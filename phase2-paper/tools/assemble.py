#!/usr/bin/env python3
"""S2 机械组装器（DESIGN.md §4.2/§4.4）：装配指令 JSON ＋ fragments → paper.tex。

用法:
  python3 assemble.py <instructions.json> <fragments_dir> <dep_tree.json> <out.tex> \
         [--report r.json] [--labels labels-all.json]

退出码：0=组装成功（报告 ok），1=指令违规（拓扑序/缺块/角标未闭合/xref 拒换），2=用法错误。
职责与检查项见下方注释；回归测试：phase2-paper/tests/test_gates.py。
"""
# 职责（纯机械，零 LLM）：
#   1. 指令合法性：sections 节点必须与落盘 fragments 恰好对齐（缺/多都报错）；
#   2. 命题图逻辑：节序必须是 dep-tree DAG 的拓扑线性扩展（ restricted 到本次节点）；
#   3. 角标闭合：全文每个 \ref/\eqref 目标必须存在对应 \label（含节 label）；未闭合=错误；
#   4. preamble 单源：\newtheorem 只在 preamble 出现一次（fragments 内的 stray 声明剥除并告警）；
#   5. xrefs 消费（2026-08-21 补——此前该字段被静默丢弃）：新协议 {"at","find","replace"}
#      要求 find 恰好出现一次（否则报错拒换）；旧协议 {"at","ref","macro"} 自动短语定位
#      'conclusion of NXX' → 'of NXX' → 'NXX'，替换首次出现，occurrences 记账；
#   6. \Nref{NXX} 解析（splicer v0.4 语义宏）：按 labels 映射渲染 Theorem~\ref{...}；
#      无映射降级 \texttt{NXX} 并告警（fail-open，S3 补映射）；
#   7. bibliography 渲染：指令 bibliography 字段（条目文本来自 DOSSIERS 小派发/S3）；
#   8. 引言/结论只放注释占位（大纲来自指令；正文由小派发/人工产生——规则④）。
import json, re, sys, os

def fail(msg):
    print('FATAL:', msg, file=sys.stderr); sys.exit(2)

def fragment_body(path):
    """取 fragments/NXX.md 的【块正文】节。"""
    t = open(path, encoding='utf-8').read()
    m = re.search(r'【块正文】\s*\n(.*?)(?=【|\Z)', t, re.S)
    if not m: fail(f'{path}: 缺【块正文】节')
    body = m.group(1).strip()
    # 剥除 fragment 内 stray preamble 行（\newtheorem/\documentclass/\usepackage/\begin{document}）
    dropped = []
    keep = []
    for ln in body.splitlines():
        if re.match(r'\s*\\(newtheorem|documentclass|usepackage|begin\{document\}|end\{document\})', ln):
            dropped.append(ln.strip()); continue
        keep.append(ln)
    return '\n'.join(keep).strip(), dropped

def labels_of(text):
    return set(re.findall(r'\\label\{([^}]+)\}', text))

def refs_of(text):
    return re.findall(r'\\(?:ref|eqref)\{([^}]+)\}', text)


# ── xref / Nref / bibliography（2026-08-21 补）───────────────────────

ENV_OF_PREFIX = {'thm': 'Theorem', 'lem': 'Lemma', 'prop': 'Proposition',
                 'cor': 'Corollary', 'def': 'Definition', 'defn': 'Definition',
                 'rem': 'Remark', 'ex': 'Example', 'conj': 'Conjecture'}


def label_in_macro(macro):
    m = re.search(r'\\(?:ref|eqref)\{([^}]+)\}', macro or '')
    return m.group(1) if m else None


def render_ref(label):
    """label → 'Theorem~\\ref{...}' / '\\eqref{...}'；前缀未映射返回 None。"""
    pref = label.split(':', 1)[0]
    if pref == 'eq':
        return '\\eqref{' + label + '}'
    env = ENV_OF_PREFIX.get(pref)
    return f'{env}~\\ref{{{label}}}' if env else None


def apply_xrefs(bodies, instr, err, warn, rep):
    """消费装配指令 xrefs（修复：此前字段被组装器静默丢弃）。"""
    applied, skipped = [], []
    for x in instr.get('xrefs', []):
        at = str(x.get('at', ''))
        if at not in bodies:
            skipped.append({'xref': x, 'reason': f'at 块 {at} 不在装配范围'})
            warn.append(f'xref(at {at}) 跳过：块不在装配范围')
            continue
        body = bodies[at]
        if x.get('find') is not None and x.get('replace') is not None:
            n = body.count(x['find'])
            if n != 1:
                err.append(f'xref(at {at}) find 短语出现 {n} 次（须恰好 1 次），拒绝盲换: {x["find"]!r}')
                skipped.append({'xref': x, 'reason': f'find 出现 {n} 次'})
                continue
            bodies[at] = body.replace(x['find'], x['replace'])
            applied.append({'at': at, 'protocol': 'find/replace', 'find': x['find']})
            continue
        ref, macro = str(x.get('ref', '')), str(x.get('macro', ''))
        label = label_in_macro(macro)
        rendered = render_ref(label) if label else None
        if rendered is None:
            skipped.append({'xref': x, 'reason': f'macro 无法渲染（label={label}，前缀未映射）'})
            warn.append(f'xref(at {at}, ref {ref}) 跳过：label 前缀无法映射环境名')
            continue
        # 候选短语探测。裸 NXX 候选必须带守卫（不得匹配 \Nref{NXX} 内部、
        # label/ref 参数内（前置冒号）、或 R_{29} 之类子串）——v3 组装事故回归：
        # 守卫缺失时子串替换产出 \Nref{Theorem~\ref{...}} 双重包裹，编译 Undefined control sequence。
        guarded = re.compile(r'(?<!\\Nref\{)(?<![A-Za-z0-9:])' + re.escape(ref) + r'(?![0-9])')
        for cand in (f'conclusion of {ref}', f'of {ref}', ref):
            if cand == ref:
                m = guarded.search(body)
                if not m:
                    continue
                bodies[at] = body[:m.start()] + rendered + body[m.end():]
                n = 1
            else:
                n = body.count(cand)
                if n < 1:
                    continue
                bodies[at] = body.replace(cand, cand.replace(ref, rendered), 1)
            applied.append({'at': at, 'protocol': 'legacy-auto', 'ref': ref,
                            'label': label, 'phrase': cand, 'occurrences': n})
            break
        else:
            skipped.append({'xref': x, 'reason': '正文未找到可定位短语'})
            warn.append(f'xref(at {at}, ref {ref}) 跳过：正文无可定位短语')
    rep['xrefs'] = {'applied': applied, 'skipped': skipped}


def primary_labels_from_inventory(inv):
    """extract_labels.py 输出 → {node: 主陈述 label}（首个定理类前缀 label，无则首个）。"""
    out = {}
    for nid, d in (inv or {}).items():
        labs = d.get('labels', [])
        cand = next((l for l in labs if re.match(r'(thm|lem|prop|cor|def|conj|rem|ex):', l)), None)
        if cand or labs:
            out[nid] = cand or labs[0]
    return out


def resolve_nrefs(bodies, labels_map, warn, rep):
    """\\Nref{NXX} → Theorem~\\ref{主label}（splicer v0.4 语义宏，闭合成文引用环）。
    bodies 与 rep['_extra_resolve']（附录等附加文本）各解析一次。"""
    resolved = unresolved = 0

    def sub(m):
        nonlocal resolved, unresolved
        nid = m.group(1)
        label = labels_map.get(nid)
        r = render_ref(label) if label else None
        if r is None:
            unresolved += 1
            warn.append(f'\\Nref{{{nid}}} 无 labels 映射，保留文本形式（S3 裁决后补映射）')
            return '\\texttt{' + nid + '}'
        resolved += 1
        return r

    for nid in bodies:
        bodies[nid] = re.sub(r'\\Nref\{(N\d+)\}', sub, bodies[nid])
    rep['_extra_resolve'] = [re.sub(r'\\Nref\{(N\d+)\}', sub, t) for t in rep.get('_extra_resolve', [])]
    rep['nrefs'] = {'resolved': resolved, 'unresolved': unresolved}


def wrap_raw_mentions(bodies, warn, rep):
    """nref_wrap：把存量 v0.3 fragment 中残余的裸 NXX 提及包成 \\Nref{NXX}（机械，v0.4 回溯适用）。
    排除：已在 \\Nref{} 内、label/ref 参数内（前置冒号）、自身块注释。"""
    pat = re.compile(r'(?<!\\Nref\{)(?<![A-Za-z0-9:])N\d\d(?![0-9])')
    total = 0
    per = {}
    for nid in bodies:
        n = len(pat.findall(bodies[nid]))
        if n:
            bodies[nid] = pat.sub(lambda m: '\\Nref{' + m.group(0) + '}', bodies[nid])
            per[nid] = n
            total += n
    rep['nref_wrap'] = {'wrapped': total, 'per_node': per}
    if total:
        print(f'  nref_wrap: {total} 处裸提及已包裹（{len(per)} 块）')


# ── blocker 框化 pass（2026-08-21 格式轮，operator 拍板：学 Gao–Lou–Wu–Zhang 的克制）──
# 只框正文级"minimal blocker 主语句"（deps 记账 remark 内的不框——它们整体住附录）。
# fragment 源形态不变（保持可 grep 的 [STATUS: ...]）；框化只发生在组装输出。

# 小状态行内特殊字符渲染（正文轻量标注；框内不适用——框自身即视觉信号）
STATUS_GLYPH = {
    'BLOCKED': '\\textcolor{blockerred}{$\\blacksquare$}',
    'CONDITIONAL': '$\\circ$',
    'CANDIDATE': '$\\vartriangle$',
    'FIXED': '$\\bullet$',
    'PROVED': '$\\bullet$',
    'PROVED-IN-PROJECT': '$\\bullet$',
    'IMPORTED-VERIFIED': '$\\diamond$',
    'UNVERIFIED': '$\\star$',
}

def glyph_status(text):
    """[STATUS: X] → 特殊字符＋缩写脚注式渲染（可 grep 源形态只在 fragment；输出层美化）。"""
    def sub(m):
        st = m.group(1).strip()
        g = STATUS_GLYPH.get(st)
        if g is None:
            return m.group(0)  # 未知状态保守保留原样（词表单源原则）
        return f'{g}\\,{{\\scriptsize[{st}]}}'
    return re.sub(r'\[STATUS:\s*([A-Za-z\-]+)\]', sub, text)

def box_blockers(bodies, warn, rep, deps_labels):
    """正文 minimal blocker 主语句 → blockerbox 红框（标题 = BLOCKER G#：<块内主题词>）。
    匹配单位＝句子（到句号止，含跨行）；deps remark 已先行移出，不在此范围。
    追随句（[STATUS: BLOCKED] 及同句号后的限定语）一并入框。"""
    sent_pat = re.compile(
        r'(?:The minimal blocker (?:is|for)|Minimal blocker:)[^.]*\.(?:\s*\\linebreak\[4\]\s*)?\s*\[STATUS:\s*BLOCKED\]?'
        r'|(?:The minimal blocker (?:is|for)|Minimal blocker:)[^.]*\.',
        re.S)
    total = 0
    per = {}
    gid_counter = 0  # 全局 G 编号（跨块递增，学 Gao–Lou–Wu–Zhang 的 G1–G9 连续序）
    for nid in bodies:
        text = bodies[nid]
        matches = list(sent_pat.finditer(text))
        if not matches:
            continue
        out, last, n = [], 0, 0
        for m in matches:
            seg = m.group(0)
            # 句内已有 [STATUS: BLOCKED] 则剥离（框标题承载状态）
            inner = re.sub(r'\s*\[STATUS:\s*BLOCKED\]\s*$', '', seg).strip()
            n += 1
            gid_counter += 1
            gid = f'G{gid_counter}'
            # 标题：取主语句前 6 个实义词（去掉 The minimal blocker is/for）
            topic = re.sub(r'^(?:The minimal blocker (?:is|for)|Minimal blocker:)\s*', '', inner)
            # 标题只用纯文字词：数学与引用整体剔除（\ref 解析后的 "Proposition~X.Y"
            # / 裸 label / 任何 \命令 / $...$ / \(...\)），只留普通英文词
            topic = re.sub(r'\$[^$]*\$', ' ', topic)
            topic = re.sub(r'\\\([^\\]*\\\)', ' ', topic)
            topic = re.sub(r'(?:Theorem|Lemma|Proposition|Corollary|Definition|Remark|Section)~?[0-9.]*', ' ', topic)
            topic = re.sub(r'[A-Za-z]+:[A-Za-z0-9\-]+', ' ', topic)  # label 残骸（thm:xxx）
            topic = re.sub(r'\\[a-zA-Z]+', ' ', topic)
            topic = re.sub(r'[{}^_~]', ' ', topic)
            # 引导残句剥离（"the following:", "to supply, for each of ..." 等）＋停用词过滤
            topic = re.sub(r'^(?:the following\s*:|to\s+|that\s+|the\s+)', '', topic.strip(), flags=re.I)
            STOP = {'the','and','for','each','of','is','to','that','with','together','one','least',
                    'following','supply','provide','actual','all','its','this','are','been','from'}
            seen = set()
            words = [w for w in topic.split()
                     if len(w) > 2 and w.isalpha() and w.lower() not in STOP
                     and not (w.lower() in seen or seen.add(w.lower()))][:6]
            title = f'UNPROVED INPUT {gid}: {" ".join(words)}'
            out.append(text[last:m.start()])
            out.append(f'\\begin{{blockerbox}}{{{title}}}\n{inner}\n\\end{{blockerbox}}')
            last = m.end()
        out.append(text[last:])
        bodies[nid] = ''.join(out)
        per[nid] = n
        total += n
    rep['blocker_boxes'] = {'boxed': total, 'per_node': per}
    if total:
        print(f'  blocker_box: {total} 处最小 blocker 已框化（{len(per)} 块）')


def extract_deps_appendix(bodies, warn, rep):
    """deps_appendix：把 rem:NXX-deps / rem:NXX-deps-open 记账 remark 整体移入文末附录（S3 裁决族②）。"""
    pat = re.compile(r'\\begin\{remark\}(?:\[[^\]]*\])?\s*\\label\{rem:(N\d+)-deps[^}]*\}.*?\\end\{remark\}', re.S)
    moved = []
    for nid in list(bodies):
        m = pat.search(bodies[nid])
        if not m:
            continue
        moved.append({'node': nid, 'label': re.search(r'\\label\{([^}]+)\}', m.group(0)).group(1),
                      'text': m.group(0)})
        bodies[nid] = pat.sub('', bodies[nid]).strip()
    moved.sort(key=lambda e: e['node'])
    rep['deps_appendix'] = {'moved': [e['node'] for e in moved]}
    rep['_extra_resolve'] = [e['text'] for e in moved]
    rep['_deps_entries'] = moved
    return moved


def render_bibliography(instr):
    """指令 bibliography 字段 → thebibliography 环境（条目文本由 S3 小派发/人工提供）。"""
    bib = instr.get('bibliography') or []
    if not bib:
        return '', 0
    lines = ['\\begin{thebibliography}{99}']
    for e in bib:
        key, text = (e.get('key', ''), e.get('text', '')) if isinstance(e, dict) else ('', str(e))
        lines.append(f'\\bibitem{{{key}}} {text}'.rstrip() if key else f'\\bibitem {text}')
    lines.append('\\end{thebibliography}')
    return '\n'.join(lines) + '\n', len(bib)

def main():
    args = sys.argv[1:]
    if len(args) < 4: print(__doc__); sys.exit(2)
    instr_path, frag_dir, tree_path, out_path = args[:4]
    report_path = labels_path = None
    rest = args[4:]
    while rest:
        a = rest.pop(0)
        if a == '--report': report_path = rest.pop(0)
        elif a == '--labels': labels_path = rest.pop(0)
        else: fail('未知参数 ' + a)

    instr = json.load(open(instr_path, encoding='utf-8'))
    tree = json.load(open(tree_path, encoding='utf-8'))
    nodes = {n['id']: n for n in tree['nodes']}
    rep = {'ok': True, 'errors': [], 'warnings': [], 'sections': [], 'labels': [], 'unresolved_refs': [], 'dropped_preamble': {}}
    err, warn = rep['errors'], rep['warnings']

    # 1. 节点-fragments 对齐
    order = []
    for sec in instr['sections']:
        for nid in sec['nodes']:
            order.append((sec, nid))
    listed = [nid for _, nid in order]
    if len(set(listed)) != len(listed): err.append(f'指令中节点重复: {listed}')
    on_disk = sorted(f for f in os.listdir(frag_dir) if re.fullmatch(r'N\d+\.md', f))
    on_disk_ids = {f[:-3] for f in on_disk}
    missing = [nid for nid in listed if nid not in on_disk_ids]
    extra = sorted(on_disk_ids - set(listed))
    if missing: err.append(f'指令列出但无 fragment: {missing}')
    if extra: err.append(f'fragment 落盘但指令未列: {extra}（组装范围以指令为准，需更新指令或移走文件）')

    # 2. 拓扑线性扩展校验（restricted）
    pos = {nid: i for i, nid in enumerate(listed)}
    for nid in listed:
        if nid in nodes:
            for d in nodes[nid].get('deps', []):
                if d in pos and pos[d] >= pos[nid]:
                    err.append(f'节序违反命题图: {d} 是 {nid} 的前置，却排在其后')

    # 3. 组装
    num = instr.get('numbering', {})
    meta = instr.get('meta', {})
    docclass = meta.get('docclass', 'amsart')
    lang_note = meta.get('language', 'English')
    pre = [f'\\documentclass{{{docclass}}}', '\\usepackage{amsmath,amssymb,amsthm,amscd}']
    if lang_note == 'Chinese': pre.insert(1, '\\usepackage{ctex}')  # 中文回退才引 ctex
    # 模板层（2026-08-21 补——回溯证实：视觉/排版职责在 v0.3 拆分后无工位，preamble
    # 曾是六行裸奔版）。meta.template 预置配方 + meta.preamble_extra 自由追加。
    TEMPLATES = {
        # xelatex/pdflatex 通用：LM 已是 xelatex 默认；microtype 在 xelatex 下自动降级
        # 为 protrusion（expansion 不可用，打印 warning 但合法）；
        'amsart-arxiv': ['\\usepackage{lmodern}', '\\usepackage{microtype}',
                         '\\usepackage[hidelinks]{hyperref}'],
        'article-arxiv': ['\\usepackage[T1]{fontenc}', '\\usepackage{lmodern}',
                          '\\usepackage{microtype}', '\\usepackage{mathtools}',
                          '\\usepackage{booktabs}', '\\usepackage{url}',
                          '\\usepackage[hidelinks]{hyperref}'],
        # 复刻 Gao–Lou–Wu–Zhang (2026-08-19) 版式（operator 2026-08-21 拍板：迁 article 11pt）：
        # 11pt 正文、margin=1in 宽版心、蓝色可点链接、tcolorbox 红框、按节定理编号。
        # geometry 属"operator 批准的配方"，非 lint 意义上的版面干预（R3 白名单语义）。
        'sibling-wu': [
            '\\usepackage[letterpaper,margin=1in]{geometry}',
            '\\usepackage{lmodern}', '\\usepackage{microtype}',
            '\\usepackage{mathtools}', '\\usepackage{booktabs}',
            # 注：不加载 array——本机 ~/texmf 有 v2.7b array.sty 与 TeX Live 2026 basic
            # 内核不兼容（vcenter@text 未定义，最小复现 26 errors）；LaTeX 内置 array
            # 环境已够本文使用（全文 1 处 \begin{array}，无 array 包特性）。
            '\\usepackage{xcolor}',
            '\\usepackage[most]{tcolorbox}',
            '\\definecolor{blockerred}{RGB}{155,35,35}',
            '\\definecolor{blockerback}{RGB}{255,247,247}',
            '\\newtcolorbox{blockerbox}[1]{enhanced, breakable, colback=blockerback,'
            ' colframe=blockerred, boxrule=0.7pt, arc=0pt, left=7pt, right=7pt,'
            ' top=6pt, bottom=6pt, before skip=10pt, after skip=10pt,'
            ' title={#1}, coltitle=blockerred, fonttitle=\\bfseries}',
            '\\usepackage[colorlinks=true, linkcolor=blue!60!black,'
            ' citecolor=blue!60!black, urlcolor=blue!60!black]{hyperref}'],
    }
    # docclass 传参（如 article 11pt）：meta.docclass_options
    dco = meta.get('docclass_options')
    if dco:
        pre[0] = f'\\documentclass[{dco}]{{{docclass}}}'
    tpl = meta.get('template')
    if tpl:
        if tpl not in TEMPLATES:
            err.append(f'meta.template 未知配方: {tpl}（可用: {sorted(TEMPLATES)}）')
        else:
            pre = [pre[0]] + TEMPLATES[tpl] + pre[1:]
    for line in meta.get('preamble_extra', []):
        pre.append(line)
    declared = []
    # 定理编号策略：numbering.style == 'per-section' → 按节编号（Theorem 3.1 式），
    # 与共享计数器（首个环境为基准）；默认保持连续编号（现行行为）。
    per_section = str(num.get('style', '')).lower() in ('per-section', 'persection', 'by-section')
    for i, env in enumerate(num.get('newtheorems', ['theorem','lemma','proposition','corollary','conjecture','definition','example','remark'])):
        # 共享计数器：非首环境挂 [基准]；基准自身挂 [section]（per-section 时）
        if i == 0:
            decl = f'\\newtheorem{{{env}}}{{{env.capitalize()}}}' + ('[section]' if per_section else '')
        else:
            base = num["newtheorems"][0]
            decl = f'\\newtheorem{{{env}}}[{base}]{{{env.capitalize()}}}'
        if env in ('definition', 'example'):
            decl = '\\theoremstyle{definition}\n' + decl
        elif env == 'remark':
            decl = '\\theoremstyle{remark}\n' + decl
        pre.append(decl)
        declared.append(env)
    # 3.5 预载全部正文（xref/Nref 需要块内定位；stray preamble 此处剥除记账）
    bodies, dropped_map = {}, {}
    for _sec, nid in order:
        fp = os.path.join(frag_dir, nid + '.md')
        if not os.path.exists(fp):
            continue  # 对齐错误已记录，跳过缺失文件
        b, dr = fragment_body(fp)
        bodies[nid] = b
        if dr:
            dropped_map[nid] = dr
            warn.append(f'{nid}: 剥除 fragment 内 preamble 行 {len(dr)} 处（preamble 单源于指令）')
    rep['dropped_preamble'] = dropped_map

    labels_map = dict(instr.get('labels') or {})
    if labels_path:
        inv = json.load(open(labels_path, encoding='utf-8'))
        for k, v in primary_labels_from_inventory(inv).items():
            labels_map.setdefault(k, v)
    apply_xrefs(bodies, instr, err, warn, rep)
    if instr.get('nref_wrap'):
        wrap_raw_mentions(bodies, warn, rep)
    deps_entries = extract_deps_appendix(bodies, warn, rep) if instr.get('deps_appendix') else []
    resolve_nrefs(bodies, labels_map, warn, rep)

    # 视觉 pass（仅 sibling-wu 配方启用；其他配方零行为变化——渐进发布原则）
    visual = str(meta.get('template', '')).strip() == 'sibling-wu'
    if visual:
        box_blockers(bodies, warn, rep, {e['node'] for e in deps_entries})
        boxed_nodes = set(rep.get('blocker_boxes', {}).get('per_node', {}))
        for nid in bodies:
            # 状态字形化：整块做（框内已被 box_blockers 剥离 STATUS 尾注；框外轻量标注）
            bodies[nid] = glyph_status(bodies[nid])

    body_parts = []
    all_text = []
    for sec, nid in order:
        first = sec['nodes'][0] == nid
        if first:
            body_parts.append(f"\\section{{{sec['title']}}}\\label{{sec:{sec['id']}}}")
            tr = next((t for t in instr.get('transitions', []) if t.get('between') and t['between'][-1] == sec['id']), None)
            if tr: body_parts.append(tr['text'])
        if nid not in bodies:
            continue
        body = bodies[nid]
        body_parts.append(f'% ---- node {nid} ({sec["id"]}) ----')
        body_parts.append(body)
        all_text.append(body)
        # over-escape 启发式：\_{ 几乎必为数学模式内被错误转义的下标
        n_over = len(re.findall(r'\\\_\{', body))
        if n_over:
            warn.append(f'{nid}: 疑似数学模式 over-escape 下标 \\_{{ 共 {n_over} 处（能编译但排版语义错误，回 S1 修）')

    intro = instr.get('intro_outline', []); concl = instr.get('conclusion_outline', [])
    intro_text = str(instr.get('intro_text') or '').strip()
    concl_text = str(instr.get('conclusion_text') or '').strip()
    if intro_text:
        head_comment = '% 引言：小派发产物（输入=大纲＋账本统计，未接触证明正文——规则④）。\n' + intro_text + '\n'
    else:
        head_comment = '% 引言/结论正文不由组装器产生（DESIGN §4.0 规则④）：此处仅注释占位大纲。\n'
        for o in intro: head_comment += f'% INTRO-TODO: {o}\n'
    if concl_text:
        tail_comment = concl_text + '\n'
    else:
        tail_comment = ''
        for o in concl: tail_comment += f'% CONCL-TODO: {o}\n'

    # deps 附录（S3 裁决族②）：记账 remark 集中移至文末（文本原样，仅位置移动）
    appendix_tex = ''
    if deps_entries:
        parts = ['\\section*{Dependency and Open-Item Ledger}\\label{sec:deps-ledger}',
                 'The following remarks record, for each block, the predecessor blocks actually '
                 'invoked, the newly introduced local notation, the minimal blockers, and the '
                 'strongest unaffected conclusions. They are reproduced verbatim from the '
                 'block-level writing stage.']
        for e in rep.get('_extra_resolve', []):
            parts.append(e)
        appendix_tex = '\n\n'.join(parts) + '\n'

    # meta.short_title：amsart 官方 \title[短题]{全题} 机制（\shorttitle 供页眉用）。
    # 回溯实证（2026-08-21 格式轮）：全题进页眉 = 112.5pt 逐页超宽 ×36 处；
    # 缺省回落现行为（无 optional 参数）。
    title_cmd = (f"\\title[{meta['short_title']}]" + "{" + meta.get('title', 'Untitled') + "}"
                 if meta.get('short_title') and docclass == 'amsart'
                 else f"\\title{{{meta.get('title', 'Untitled')}}}")
    # article 类页眉：markboth（作者 / 短题）——学 Gao–Lou–Wu–Zhang 的偶奇分布
    abstract = str(meta.get('abstract') or '').strip()
    front = []
    if abstract and docclass != 'amsart':
        # article 顺序：maketitle → abstract → toc（amsart 是 abstract→maketitle）
        front = [title_cmd,
                 f"\\author{{{meta.get('author', 'OPERATOR-FILL')}}}"]
        if meta.get('date') is not None:
            front.append(f"\\date{{{meta['date']}}}")
        front.append('\\begin{document}')
        front.append('\\maketitle')
        front.append('\\begin{abstract}\n' + abstract + '\n\\end{abstract}')
        rep['abstract'] = {'rendered': True, 'chars': len(abstract)}
        if visual:
            front.append(f'\\markboth{{{meta.get("short_title", meta.get("title", ""))}}}{{{meta.get("running_author", meta.get("author", "OPERATOR-FILL"))}}}')
            front.append('\\tableofcontents')
            front.append('\\newpage')
    else:
        front = [title_cmd,
                 f"\\author{{{meta.get('author', 'OPERATOR-FILL')}}}"]
        if meta.get('date') is not None:
            front.append(f"\\date{{{meta['date']}}}")
        if abstract:
            front.append('\\begin{document}')
            front.append('\\begin{abstract}\n' + abstract + '\n\\end{abstract}')
            front.append('\\maketitle')
            rep['abstract'] = {'rendered': True, 'chars': len(abstract)}
        else:
            front.append('\\begin{document}\\maketitle')
    bib_tex, bib_n = render_bibliography(instr)
    if visual and bib_tex:
        # References 进目录（article 类 thebibliography 默认不进）
        bib_tex = '\\addcontentsline{toc}{section}{References}\n' + bib_tex
    # deps 附录进目录（编号 section 自进，无需处理；此处 \section* 需手动加）
    if visual and appendix_tex:
        appendix_tex = appendix_tex.replace(
            '\\section*{Dependency and Open-Item Ledger}',
            '\\section*{Dependency and Open-Item Ledger}\n\\addcontentsline{toc}{section}{Dependency and Open-Item Ledger}', 1)
    rep['bibliography'] = {'entries': bib_n}
    tex = ('\n'.join(pre) + '\n' + '\n'.join(front) + '\n' + head_comment + '\n'
           + '\n\n'.join(body_parts) + '\n' + tail_comment + '\n'
           + appendix_tex + bib_tex + '\\end{document}\n')

    # 4. 角标闭合（fragments 互相引用 + 节 label）
    full = '\n'.join(all_text) + '\n' + '\n'.join(f'\\label{{sec:{s["id"]}}}' for s in instr['sections'])
    labs = labels_of(full)
    rep['labels'] = sorted(labs)
    for r in refs_of(full):
        if r not in labs:
            rep['unresolved_refs'].append(r)
    if rep['unresolved_refs']:
        err.append(f'角标未闭合: {sorted(set(rep["unresolved_refs"]))}')

    rep['sections'] = [{'id': s['id'], 'title': s['title'], 'nodes': s['nodes']} for s in instr['sections']]
    rep['ok'] = len(err) == 0
    if rep['ok']:
        open(out_path, 'w', encoding='utf-8').write(tex)
        print('assembled ->', out_path, f'({len(tex)} bytes)')
    for k in ('_extra_resolve', '_deps_entries'):
        rep.pop(k, None)
    if report_path:
        json.dump(rep, open(report_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('report ->', report_path)
    print('ok =', rep['ok'], '| errors =', len(err), '| warnings =', len(warn))
    for e in err: print('  ERROR:', e)
    for w in warn[:10]: print('  WARN :', w)
    sys.exit(0 if rep['ok'] else 1)

if __name__ == '__main__':
    main()
