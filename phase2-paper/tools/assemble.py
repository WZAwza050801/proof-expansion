#!/usr/bin/env python3
"""S2 机械组装器（DESIGN.md §4.2/§4.4）：装配指令 JSON ＋ fragments → paper.tex。

用法:
  python3 assemble.py <instructions.json> <fragments_dir> <dep_tree.json> <out.tex> [--report r.json]

退出码：0=组装成功（报告 ok），1=指令违规（拓扑序/缺块/角标未闭合），2=用法错误。
职责与检查项见下方注释；回归测试：phase2-paper/tests/test_gates.py。
"""
# 职责（纯机械，零 LLM）：
#   1. 指令合法性：sections 节点必须与落盘 fragments 恰好对齐（缺/多都报错）；
#   2. 命题图逻辑：节序必须是 dep-tree DAG 的拓扑线性扩展（ restricted 到本次节点）；
#   3. 角标闭合：全文每个 \ref/\eqref 目标必须存在对应 \label（含节 label）；未闭合=错误；
#   4. preamble 单源：\newtheorem 只在 preamble 出现一次（fragments 内的 stray 声明剥除并告警）；
#   5. 引言/结论只放注释占位（大纲来自指令；正文由小派发/人工产生——规则④）。
# 用法:
#   python3 assemble.py <instructions.json> <fragments_dir> <dep_tree.json> <out.tex> [--report r.json]
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

def main():
    args = sys.argv[1:]
    if len(args) < 4: print(__doc__); sys.exit(2)
    instr_path, frag_dir, tree_path, out_path = args[:4]
    report_path = None
    rest = args[4:]
    while rest:
        a = rest.pop(0)
        if a == '--report': report_path = rest.pop(0)
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
    docclass = instr.get('meta', {}).get('docclass', 'amsart')
    lang_note = instr.get('meta', {}).get('language', 'English')
    pre = [f'\\documentclass{{{docclass}}}', '\\usepackage{amsmath,amssymb,amsthm,amscd}']
    if lang_note == 'Chinese': pre.insert(1, '\\usepackage{ctex}')  # 中文回退才引 ctex
    declared = []
    for env in num.get('newtheorems', ['theorem','lemma','proposition','corollary','conjecture','definition','example','remark']):
        pre.append(f'\\newtheorem{{{env}}}{{{env.capitalize()}}}' if env not in ('definition','example') else f'\\theoremstyle{{definition}}\n\\newtheorem{{{env}}}{{{env.capitalize()}}}')
        declared.append(env)
    body_parts = []
    all_text = []
    for sec, nid in order:
        first = sec['nodes'][0] == nid
        if first:
            body_parts.append(f"\\section{{{sec['title']}}}\\label{{sec:{sec['id']}}}")
            tr = next((t for t in instr.get('transitions', []) if t.get('between') and t['between'][-1] == sec['id']), None)
            if tr: body_parts.append(tr['text'])
        frag_path = os.path.join(frag_dir, nid + '.md')
        if not os.path.exists(frag_path):
            continue  # 对齐错误已记录，跳过缺失文件
        body, dropped = fragment_body(frag_path)
        if dropped:
            warn.append(f'{nid}: 剥除 fragment 内 preamble 行 {len(dropped)} 处（preamble 单源于指令）')
            rep['dropped_preamble'][nid] = dropped
        body_parts.append(f'% ---- node {nid} ({sec["id"]}) ----')
        body_parts.append(body)
        all_text.append(body)
        # over-escape 启发式：\_{ 几乎必为数学模式内被错误转义的下标
        n_over = len(re.findall(r'\\\_\{', body))
        if n_over:
            warn.append(f'{nid}: 疑似数学模式 over-escape 下标 \\_{{ 共 {n_over} 处（能编译但排版语义错误，回 S1 修）')

    intro = instr.get('intro_outline', []); concl = instr.get('conclusion_outline', [])
    head_comment = '% 引言/结论正文不由组装器产生（DESIGN §4.0 规则④）：此处仅注释占位大纲。\n'
    for o in intro: head_comment += f'% INTRO-TODO: {o}\n'
    tail_comment = ''
    for o in concl: tail_comment += f'% CONCL-TODO: {o}\n'

    meta = instr.get('meta', {})
    front = [f"\\title{{{meta.get('title', 'Untitled')}}}",
             '\\author{OPERATOR-FILL}', '\\begin{document}\\maketitle']
    tex = '\n'.join(pre) + '\n' + '\n'.join(front) + '\n' + head_comment + '\n' + '\n\n'.join(body_parts) + '\n' + tail_comment + '\n\\end{document}\n'

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
    if report_path:
        json.dump(rep, open(report_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('report ->', report_path)
    print('ok =', rep['ok'], '| errors =', len(err), '| warnings =', len(warn))
    for e in err: print('  ERROR:', e)
    for w in warn[:10]: print('  WARN :', w)
    sys.exit(0 if rep['ok'] else 1)

if __name__ == '__main__':
    main()
