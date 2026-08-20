#!/usr/bin/env python3
"""论文级刚性自洽检查器（S5 论文级审查轮·机械件，DESIGN §4.4 / GATES G3a）

定位：编译门查"能不能编译"，本工具查"作为一篇论文自不自洽"。零 LLM、纯机械、
每项检查对应一类已实证或 arXiv 投稿标准明确要求的自洽义务。operator 2026-08-21
定调："一篇 latex 论文应该有很多专门的刚性程序判定是否自洽"——本文件是落地。

用法:
  python3 paper_lint.py <paper.tex> [--log <compile.log>] [--pdf <paper.pdf>] [--report r.json]

退出码: 0=无 ERROR（WARNING/REVIEW 可留），1=存在 ERROR，2=用法错误。
三级报告: ERROR（CI 阻断）/ WARNING / REVIEW（高风险命令等，按 operator 建议不判错）。
检查族: E（tex 图性质）L（log 指标）P（PDF 层）W（量化警告）R（高风险/模板合规）＋
        外部开源工具 battery（checkcites vendor；chktex/lacheck 探测）。
**独立部署**: 本文件仅依赖 Python stdlib ＋ 探测式外部工具（pdffonts/qpdf/PyMuPDF/
texlua，缺件自动降级）＋ vendor/checkcites.lua——整目录拷出即可脱离本仓库独立使用
（operator 定调：论文审查器可脱离区块独立存在，单独制作也有价值）。
回归测试: phase2-paper/tests/test_gates.py（负样本必红）。
"""
import argparse
import collections
import json
import os
import re
import shutil
import subprocess
import sys

DISPLAY_ENVS = 'equation|align|gather|multline|eqnarray|displaymath'
THEOREM_ENVS = ('theorem|lemma|proposition|corollary|conjecture|definition|'
                'example|remark|comparisonlemma')
STATUS_TAG = re.compile(r'\[STATUS:\s*([A-Z-]+)\]')
STATUS_PAREN = re.compile(r'(?<![A-Za-z\[])'
                          r'\((?:BLOCKED|FIXED|CONDITIONAL|CANDIDATE|PROVED(?:-IN-PROJECT)?'
                          r'|IMPORTED-VERIFIED|UNVERIFIED)\)')


def lint(tex_path, log_path):
    t = open(tex_path, encoding='utf-8').read()
    log = open(log_path, encoding='utf-8', errors='ignore').read() if log_path else ''
    errors, warnings, stats = [], [], {}

    # ── E1 label 唯一性 ─────────────────────────────────────────────
    labels = re.findall(r'\\label\{([^}]+)\}', t)
    dup = sorted(k for k, v in collections.Counter(labels).items() if v > 1)
    if dup:
        errors.append(f'E1 label 重复定义: {dup}')
    stats['labels_total'] = len(labels)

    # ── E2 引用闭合 ────────────────────────────────────────────────
    refs = re.findall(r'\\(?:ref|eqref)\{([^}]+)\}', t)
    broken = sorted(set(refs) - set(labels))
    if broken:
        errors.append(f'E2 引用指向不存在的 label: {broken}')

    # ── E3 cite↔bibitem 正向 ───────────────────────────────────────
    cites = {k for c in re.findall(r'\\cite\{([^}]+)\}', t) for k in c.split(',')}
    bibs = {m.group(1) or '' for m in re.finditer(r'\\bibitem(?:\{([^}]+)\})?', t)}
    bad_cite = sorted(cites - bibs - {''})
    if bad_cite:
        errors.append(f'E3 \\cite 键无对应 \\bibitem: {bad_cite}')

    # ── E4 环境配对 ────────────────────────────────────────────────
    for env in ('theorem', 'lemma', 'proposition', 'corollary', 'conjecture',
                'definition', 'example', 'remark', 'enumerate', 'itemize',
                'equation', 'align', 'gather', 'multline', 'thebibliography'):
        b, e = t.count(f'\\begin{{{env}}}'), t.count(f'\\end{{{env}}}')
        if b != e:
            errors.append(f'E4 环境 {env} 不配对: begin×{b} vs end×{e}')
    if t.count('\\[') != t.count('\\]'):
        errors.append(f"E4 显示数学 \\[ vs \\] 不配对: {t.count(chr(92)+'[')} vs {t.count(chr(92)+']')}")

    # ── E5 定界符平衡 ──────────────────────────────────────────────
    dollars = len(re.findall(r'(?<!\\)\$', t))
    if dollars % 2:
        errors.append(f'E5 $ 定界符奇数（{dollars}）——数学模式跨界')
    if t.count('\\(') != t.count('\\)'):
        errors.append(f"E5 \\( vs \\) 不配对: {t.count(chr(92)+'(')} vs {t.count(chr(92)+')')}")

    # ── E6 Nref 残留 / 双重包裹 ────────────────────────────────────
    nref_left = t.count('\\Nref{')
    if nref_left:
        errors.append(f'E6 未解析 \\Nref 残留 {nref_left} 处（labels 映射缺失）')
    double = re.findall(r'\\Nref\{(?:Theorem|Lemma|Proposition|Definition|Remark|Corollary|Equation)[^}]*\}', t)
    if double:
        errors.append(f'E6 \\Nref 双重包裹 {len(double)} 处（如 {double[0][:40]}…）')

    # ── E7 引言统计对账（承诺 vs 文档本身）─────────────────────────
    # 背景：2026-08-21 实锤——引言印着旧轮统计 244 项，全文实际 [STATUS:] 479 项，
    # 无任何闸门发现。本项检查把"散文里的数字"纳入机械对账。
    claimed = re.findall(r'\$(\d+)\$\s*\$\\mathrm\{([A-Z-]+)\}\$\s*(?:entries|annotations)', t)
    actual = collections.Counter(STATUS_TAG.findall(t))

    def fam(tag):  # 变体归并到引言词汇的六族（PROVED-IN-PROJECT → PROVED；IMPORTED-VERIFIED 单列）
        for base in ('IMPORTED-VERIFIED', 'PROVED', 'PROVED-IN-PROJECT', 'CONDITIONAL',
                     'CANDIDATE', 'BLOCKED', 'UNVERIFIED', 'FIXED'):
            if tag.startswith(base):
                return base
        return tag
    actual_fam = collections.Counter()
    for tag, n in actual.items():
        actual_fam[fam(tag)] += n
    for num, name in claimed:
        name2 = 'PROVED' if name == 'PROVED' else name
        if actual_fam.get(name2, 0) != int(num):
            errors.append(f'E7 引言统计对不上：声称 {name} {num}，实际 [STATUS:] 计数 '
                          f'{actual_fam.get(name2, 0)}（口径：变体归并到族）')
    stats['status_tags_total'] = sum(actual.values())
    stats['status_by_family'] = dict(sorted(actual_fam.items()))

    # ── W1 unused labels（arXiv 标准：编号以被引用为目的）──────────
    used = set(refs)
    unused = set(labels) - used
    eq_u = sorted(l for l in unused if l.startswith('eq:'))
    thm_u = sorted(l for l in unused if not l.startswith(('eq:', 'sec:')))
    sec_u = sorted(l for l in unused if l.startswith('sec:'))
    warnings.append(f'W1 未被引用的 label {len(unused)}/{len(labels)}：'
                    f'eq:* {len(eq_u)}（公式编号了没人引→应降为无编号或补引）、'
                    f'定理类 {len(thm_u)}、sec:* {len(sec_u)}')
    stats['unused_eq_labels'] = len(eq_u)

    # ── W2 bibitem 列而未引 ────────────────────────────────────────
    uncited = sorted(bibs - cites - {''})
    if uncited:
        warnings.append(f'W2 参考文献列而未引 {len(uncited)} 条: {uncited}'
                        '（正文叙述性提及处应挂 \\cite，或删条目）')

    # ── W3 overfull（排版达标量化，arXiv 视角的硬指标）─────────────
    if log:
        of = [float(x) for x in re.findall(r'Overfull \\hbox \((\d+(?:\.\d+)?)pt too wide\)', log)]
        big = [x for x in of if x > 10]
        warnings.append(f'W3 overfull hbox {len(of)} 处（>10pt 的 {len(big)} 处，'
                        f'最大 {max(of):.0f}pt）——公式/行溢出版心，学术编辑轮逐处断行或改排')
        stats['overfull_total'], stats['overfull_gt10pt'], stats['overfull_max_pt'] = \
            len(of), len(big), round(max(of), 1) if of else 0

    # ── W4 状态标注形态统一 ────────────────────────────────────────
    paren = STATUS_PAREN.findall(t)
    if paren:
        warnings.append(f'W4 状态标注圆括号残留形态 {len(paren)} 处（应统一 [STATUS: X]）')

    # ── W5 公式编号策略 ────────────────────────────────────────────
    if len(eq_u) > 0 and t.count('\\eqref{') == 0:
        warnings.append(f'W5 全文 \\eqref 使用 0 次而 eq: label {len(eq_u)} 个未被引——'
                        '编号无消费者；S5 裁决：批量降无编号，或为需要被引的公式补 \\eqref')

    ok = not errors
    return {'ok': ok, 'tex': tex_path, 'log': log_path, 'errors': errors,
            'warnings': warnings, 'stats': stats}


# ── 外部开源检查器 battery（operator 2026-08-21 定调："很多 github 开源工具
#    放入一个判定器、构成 harness 的一部分"）。架构：工具注册表 → 探测 → 运行 →
#    normalization（映射到本工具 E/W 分类）→ 模型不匹配仲裁 → 与内部检查交叉验证。
#    关键实证：checkcites 假设 BibTeX 工作流（.bib via \bibdata），对内联
#    thebibliography 文档把已定义键误报 undefined——原始输出不可直接信，
#    每个工具的文档模型假设必须由驱动层仲裁。

import shutil
import subprocess

VENDOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor')


# ── L 族：编译日志指标（operator 2026-08-21 清单：.log 提取为机器可读指标）──

def parse_log_metrics(log_text):
    """LaTeX 编译日志 → 指标 dict（纯函数，供测试与 CI 复用）。

    指标清单与 operator 提供的表逐项对应：compile_errors / undefined_references /
    undefined_citations / multiply_defined_labels / missing_files / missing_characters /
    font_substitution_warnings / overfull_hbox_count / overfull_vbox_count /
    max_overflow_pt / underfull_badness_10000_count / rerun_required_warnings。
    """
    m = {
        'compile_errors': len(re.findall(r'^!', log_text, re.M)),
        'undefined_references': len(re.findall(r"LaTeX Warning: Reference `[^']*' on page \d+ undefined", log_text)),
        'undefined_citations': len(re.findall(r"LaTeX Warning: Citation `[^']*' on page \d+ undefined", log_text)),
        'multiply_defined_labels': len(re.findall(r"Label `[^']*' multiply defined", log_text))
                                    + len(re.findall(r'There were multiply-defined labels', log_text)),
        'missing_files': len(re.findall(r'File `[^`\']*\'? not found|No file [^\s]+', log_text)),
        'missing_characters': len(re.findall(r'Missing character', log_text)),
        'font_substitution_warnings': len(re.findall(r'Font shape .* undefined|substituted|Font Warning', log_text)),
        'overfull_hbox_count': len(re.findall(r'Overfull \\hbox', log_text)),
        'overfull_vbox_count': len(re.findall(r'Overfull \\vbox', log_text)),
        'max_overflow_pt': 0,
        'underfull_badness_10000_count': len(re.findall(r'Underfull \\[hv]box \(badness 10000\)', log_text)),
        'rerun_required_warnings': len(re.findall(r'Rerun to get|Label\(s\) may have changed', log_text)),
    }
    pts = [float(x) for x in re.findall(r'Overfull \\[hv]box \((\d+(?:\.\d+)?)pt too wide', log_text)]
    m['max_overflow_pt'] = round(max(pts), 1) if pts else 0
    return m


def apply_log_metrics(metrics, errors, warnings, stats):
    """日志指标 → 三级判定（operator 表的 CI 阻断口径：ERROR 项全零）。"""
    for k in ('compile_errors', 'undefined_references', 'undefined_citations',
              'multiply_defined_labels', 'missing_files'):
        if metrics.get(k):
            errors.append(f'L-{k} = {metrics[k]}（CI 阻断项，须为 0）')
    for k in ('missing_characters', 'font_substitution_warnings',
              'underfull_badness_10000_count', 'rerun_required_warnings'):
        if metrics.get(k):
            warnings.append(f'L-{k} = {metrics[k]}')
    stats['log_metrics'] = metrics


# ── P 族：PDF 层检查（字体嵌入/结构/页面几何/图片分辨率）────────────

def parse_pdffonts(output):
    """pdffonts 输出 → {unembedded: [...], type3: [...], total}（纯函数）。
    列解析用 emb/sub/uni 三连 yes/no 锚定（类型名可含空格，如 'Type 1'/'CID Type 0C'，
    固定下标会被打穿——实证于本测试）。"""
    rows, started = [], False
    for ln in output.splitlines():
        if re.match(r'-{5,}', ln.strip()):
            started = True
            continue
        if started and ln.strip():
            f = ln.split()
            # 从右找 emb/sub/uni 三连（各为 yes/no），其前为 encoding
            idx = None
            for i in range(len(f) - 3, 0, -1):
                if all(f[i + k] in ('yes', 'no') for k in range(3)):
                    idx = i
                    break
            if idx is None:
                continue
            rows.append({'name': f[0], 'type': ' '.join(f[1:idx - 1]), 'emb': f[idx]})
    unembedded = [r['name'] for r in rows if r['emb'] == 'no']
    type3 = [r['name'] for r in rows if 'Type 3' in r['type']]
    return {'unembedded': unembedded, 'type3': type3, 'total': len(rows)}


def parse_pdfimages(output):
    """pdfimages -list 输出 → 低分辨率图片清单（<300 DPI 经验阈值）。"""
    low, started = [], False
    for ln in output.splitlines():
        if ln.strip().startswith('page') and 'x-ppi' in ln:
            started = True
            continue
        if started and ln.strip():
            f = ln.split()
            if len(f) >= 14:
                try:
                    xppi, yppi = float(f[12]), float(f[13])
                    if xppi < 300 or yppi < 300:
                        low.append({'page': f[0], 'xppi': xppi, 'yppi': yppi})
                except ValueError:
                    continue
    return low


def check_pdf(pdf_path, errors, warnings, review, stats):
    """PDF 层：pdffonts/qpdf/pdfimages 子进程 ＋ PyMuPDF 页面几何。缺件降级。"""
    battery = {'pdf': pdf_path}
    sh = lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=120)  # noqa: E731

    # P1 字体：嵌入与 Type 3
    p1 = {'status': 'skipped', 'note': ''}
    if shutil.which('pdffonts'):
        try:
            out = sh(['pdffonts', pdf_path]).stdout
            fonts = parse_pdffonts(out)
            p1.update(status='ok', **fonts)
            if fonts['unembedded']:
                errors.append(f"P1 字体未嵌入 {fonts['unembedded']}（arXiv/打印不达标）")
            if fonts['type3']:
                warnings.append(f"P1 Type 3 字体 {fonts['type3']}（位图字形，常见于 matplotlib 默认）")
            stats['pdf_fonts_total'] = fonts['total']
        except Exception as e:  # noqa: BLE001
            p1.update(status='error', note=str(e))
    else:
        p1['note'] = 'pdffonts 不可用'
    battery['fonts'] = p1

    # P2 结构：qpdf --check
    p2 = {'status': 'skipped', 'note': ''}
    if shutil.which('qpdf'):
        try:
            r = sh(['qpdf', '--check', pdf_path])
            ok = r.returncode == 0
            boilerplate = ('No syntax or stream encoding errors found', 'qpdf cannot detect')
            warns = [ln for ln in r.stdout.splitlines()
                     if ('warning' in ln.lower() or 'error' in ln.lower())
                     and not any(b in ln for b in boilerplate)]
            p2.update(status='ok', returncode=r.returncode, findings=warns[:20])
            if not ok:
                errors.append(f'P2 qpdf --check 退出码 {r.returncode}（PDF 结构损坏嫌疑）')
            elif warns:
                review.append(f'P2 qpdf 警告 {len(warns)} 条（详见报告）')
        except Exception as e:  # noqa: BLE001
            p2.update(status='error', note=str(e))
    else:
        p2['note'] = 'qpdf 不可用'
    battery['structure'] = p2

    # P3 页面几何与空白页（PyMuPDF）
    p3 = {'status': 'skipped', 'note': ''}
    try:
        import pymupdf  # type: ignore
        doc = pymupdf.open(pdf_path)
        sizes, outside, blank = set(), [], []
        for pno, page in enumerate(doc, 1):
            r = page.rect
            sizes.add((round(r.width, 1), round(r.height, 1)))
            has_content = False
            for b in page.get_text('blocks'):
                has_content = True
                x0, y0, x1, y1 = b[:4]
                if x0 < -1 or y0 < -1 or x1 > r.width + 1 or y1 > r.height + 1:
                    outside.append(f'p{pno}:text')
            for im in page.get_image_info():
                has_content = True
                bb = im['bbox']
                if bb[0] < -1 or bb[1] < -1 or bb[2] > r.width + 1 or bb[3] > r.height + 1:
                    outside.append(f'p{pno}:image')
            if not has_content:
                blank.append(pno)
        p3.update(status='ok', page_sizes=sorted(map(list, sizes)),
                  outside_page=len(outside), outside_sample=outside[:10], blank_pages=blank)
        if len(sizes) > 1:
            errors.append(f'P3 页面尺寸不一致 {sorted(map(list, sizes))}')
        if outside:
            review.append(f'P3 内容块越出页面框 {len(outside)} 处（样本 {outside[:5]}）'
                          '——overfull 的下游表现，学术编辑轮处置')
        if blank:
            warnings.append(f'P3 疑似空白页 {blank}')
        stats['pdf_pages'] = len(doc)
    except ImportError:
        p3['note'] = 'PyMuPDF 未装（pip install pymupdf 后自动启用）'
    except Exception as e:  # noqa: BLE001
        p3.update(status='error', note=str(e))
    battery['geometry'] = p3

    # P4 图片分辨率（300 DPI 经验阈值；线稿 600 属 REVIEW 提示）
    p4 = {'status': 'skipped', 'note': ''}
    if shutil.which('pdfimages'):
        try:
            out = sh(['pdfimages', '-list', pdf_path]).stdout
            low = parse_pdfimages(out)
            p4.update(status='ok', low_res=low)
            if low:
                warnings.append(f'P4 低分辨率图片（<300DPI）{len(low)} 处：{low[:5]}')
        except Exception as e:  # noqa: BLE001
            p4.update(status='error', note=str(e))
    battery['images'] = p4
    return battery


# ── R 族：高风险排版命令与版面干预（REVIEW 层，按 operator 建议不判错）──

HIGH_RISK_COMMANDS = (r'\vspace{-', r'\hspace{-', r'\newpage', r'\clearpage',
                      r'\enlargethispage', r'\resizebox', r'\scalebox', r'\tiny',
                      r'\scriptsize', r'\sloppy', r'\allowdisplaybreaks')


def high_risk_scan(tex_text):
    """统计高风险排版命令与版面干预（纯函数）。只报告，不判错。"""
    cmd_counts = {c.replace('\\', ''): len(re.findall(re.escape(c), tex_text))
                  for c in HIGH_RISK_COMMANDS}
    geo = []
    for pat in (r'\\geometry(?:\[[^\]]*\])?(?:\{[^}]*\})?',
                r'\\setlength\{\\(?:textwidth|textheight|oddsidemargin|evensidemargin|topmargin)[^}]*\}\{[^}]*\}',
                r'\\addtolength\{\\(?:oddsidemargin|topmargin|textheight)[^}]*\}',
                r'\\enlargethispage'):
        geo += re.findall(pat, tex_text)
    return {'commands': {k: v for k, v in cmd_counts.items() if v},
            'geometry_tamper': geo[:20]}


def template_compliance_scan(tex_text):
    """R3 模板合规（operator 定调"字体和排版直接准备好模板"的配套检查）。"""
    issues = []
    if 'OPERATOR-FILL' in tex_text:
        issues.append('作者字段仍为 OPERATOR-FILL 占位（交付前须实名/匿名规范填充）')
    if not re.search(r'\\title\{', tex_text):
        issues.append('缺 \\title')
    if not re.search(r'\\author\{', tex_text):
        issues.append('缺 \\author')
    if '\\maketitle' not in tex_text:
        issues.append('缺 \\maketitle')
    if '\\begin{abstract}' not in tex_text:
        issues.append('缺 abstract 环境（amsart 常规要求；特殊体例除外）')
    return issues


VENDOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor')


def parse_checkcites(output):
    """checkcites v2.x 输出 → {unused: [...], undefined: [...]}（纯函数，供测试）。"""
    def section(name):
        m = re.search(name + r' references in your TeX document:\s*(\d+)\s*(.*?)(?:\n\n|\Z)',
                      output, re.S)
        if not m or m.group(1).strip() == '0':
            return []
        return re.findall(r'=>\s*(\S+)', m.group(2))
    return {'unused': section('Unused'), 'undefined': section('Undefined')}


def run_battery(tex_path, errors, warnings, stats, internal_uncited):
    """运行可用的外部检查器；缺件优雅降级；结果并入报告 battery 节。
    internal_uncited：内部 W2 的未引用键集合（交叉验证用）。"""
    battery = {}
    t = open(tex_path, encoding='utf-8').read()
    aux = tex_path[:-4] + '.aux'
    has_inline_bib = '\\begin{thebibliography}' in t

    # ── checkcites（LPPL, Island of TeX；vendor 单文件，texlua 运行）──
    cc = {'tool': 'checkcites (vendored, LPPL)', 'status': 'skipped', 'findings': [], 'note': ''}
    texlua = shutil.which('texlua')
    script = os.path.join(VENDOR_DIR, 'checkcites.lua')
    if texlua and os.path.exists(script) and os.path.exists(aux):
        try:
            out = subprocess.run([texlua, script, os.path.basename(aux)],
                                 capture_output=True, text=True, timeout=60,
                                 cwd=os.path.dirname(os.path.abspath(tex_path))).stdout
            parsed = parse_checkcites(out)
            # 模型仲裁：checkcites 只认 .bib（\bibdata）；内联 thebibliography 且无 \bibdata
            # 时，其 "undefined" = 文档模型不匹配的假阳性（键实际有 \bibitem），降级为备注，
            # 内部 E3 为权威判定。
            aux_text = open(aux, encoding='utf-8', errors='ignore').read()
            bibtex_mode = '\\bibdata' in aux_text
            if parsed['undefined'] and not bibtex_mode and has_inline_bib:
                cc['status'] = 'model-mismatch'
                cc['note'] = (f"checkcites 报 undefined {parsed['undefined']}，但其文档模型为 "
                              "BibTeX（.bib via \\bibdata）；本文档为内联 thebibliography——"
                              "该判定降级为备注，内部 E3（\\cite↔\\bibitem 正则对账）为权威")
                stats['battery_checkcites'] = 'model-mismatch (inline bib)'
            else:
                cc['status'] = 'ok'
                if parsed['undefined']:
                    errors.append(f"E3-cc checkcites: 引用了无 bibliography 来源的键 {parsed['undefined']}")
                if parsed['unused']:
                    warnings.append(f"W2-cc checkcites: 列而未引 {parsed['unused']}")
                # 交叉验证：两套独立实现（内部正则 vs checkcites aux 解析）对同一不变量对账
                if set(parsed['unused']) != set(internal_uncited) and bibtex_mode:
                    warnings.append(f"XCHK 内部 W2 与 checkcites unused 不一致："
                                    f"内部 {sorted(internal_uncited)} vs 工具 {sorted(parsed['unused'])}"
                                    "（检查器自身 bug 嫌疑，人工复核）")
                cc['findings'] = parsed
                stats['battery_checkcites'] = f"unused={len(parsed['unused'])} undefined={len(parsed['undefined'])}"
        except Exception as e:  # noqa: BLE001
            cc['status'] = 'error'
            cc['note'] = f'运行失败: {type(e).__name__}: {e}'
    else:
        cc['note'] = '需要 texlua＋同目录 .aux＋tools/vendor/checkcites.lua'
    battery['checkcites'] = cc

    # ── chktex / lacheck（TeX Live 工具；本机 basic 集未装 → 占位并写明启用路径）──
    for name, code, what in (('chktex', 'W6', '排版/印刷惯例（间距、括号、标点类）'),
                             ('lacheck', 'W7', 'LaTeX 风格类（悬空引用修饰语等）')):
        entry = {'tool': name, 'status': 'skipped', 'findings': [], 'note': ''}
        path = shutil.which(name)
        if path:
            try:
                out = subprocess.run([path, '-q', tex_path] if name == 'chktex'
                                     else [path, tex_path],
                                     capture_output=True, text=True, timeout=120).stdout
                lines = [ln for ln in out.splitlines() if ln.strip()]
                entry['status'] = 'ok'
                entry['findings'] = lines[:50]
                entry['count'] = len(lines)
                if lines:
                    warnings.append(f'{code} {name}: {len(lines)} 条（详见 battery 报告；'
                                    'G3b 节级审查时按节消化）')
                stats[f'battery_{name}'] = len(lines)
            except Exception as e:  # noqa: BLE001
                entry['status'] = 'error'
                entry['note'] = f'运行失败: {e}'
        else:
            entry['note'] = ('未安装：TeX Live basic 集不含；启用 = sudo tlmgr install '
                             f'{name}（或装 TeX Live full / MacTeX）后重跑本工具')
        battery[name] = entry
    return battery


def arxiv_readiness(rep):
    """operator 2026-08-21 判据框架：A 可编译 / B PDF 技术质量 / C 版式 / D 引用。
    A、B 高度自动化；C、D 机械代理指标＋残余人工抽查（如实标注，不冒充全检）。"""
    lm = rep['stats'].get('log_metrics') or {}
    pdf = rep['battery_pdf'] if 'battery_pdf' in rep else {}
    fonts = pdf.get('fonts', {})
    geo = pdf.get('geometry', {})
    imgs = pdf.get('images', {})
    tex_errs = len(rep['errors'])

    def sec(items):
        fails = [i for i, ok in items if not ok]
        skipped = [i for i, ok in items if ok is None]
        st = 'PASS' if not fails else ('ADVISORY' if all(ok is not False for _, ok in items) else 'FAIL')
        return {'status': st, 'failed': fails, 'unverified': skipped,
                'items': {i: ('PASS' if ok else ('SKIP' if ok is None else 'FAIL')) for i, ok in items}}

    A = sec([
        ('compile_errors=0', lm.get('compile_errors') == 0 if lm else None),
        ('undefined_references=0', lm.get('undefined_references') == 0 if lm else None),
        ('undefined_citations=0', lm.get('undefined_citations') == 0 if lm else None),
        ('missing_files=0', lm.get('missing_files') == 0 if lm else None),
        ('tex_static_errors=0', tex_errs == 0),
        ('干净环境编译', None),   # 需 latexmk 于干净目录跑（CI 项，本轮不自动）
        ('源文件齐备（无绝对路径/交互依赖）', None),  # arxiv-collector 层
    ])
    B = sec([
        ('pdf_structure_ok', pdf.get('structure', {}).get('status') == 'ok' or None),
        ('fonts_all_embedded', (not fonts.get('unembedded')) if fonts else None),
        ('type3_fonts=0', (not fonts.get('type3')) if fonts else None),
        ('page_sizes_consistent', (len(geo.get('page_sizes', [])) <= 1) if geo else None),
        ('no_blank_pages', (not geo.get('blank_pages')) if geo else None),
        ('images_ge_300dpi', (not imgs.get('low_res')) if imgs else None),
    ])
    C = sec([
        ('overfull_hbox=0（优先处置项）', (lm.get('overfull_hbox_count') == 0) if lm else None),
        ('overfull_vbox=0', (lm.get('overfull_vbox_count') == 0) if lm else None),
        ('高风险排版命令=0', not rep['stats'].get('high_risk', {}).get('commands', {'x': 0})),
        ('版面干预=0', not rep['stats'].get('high_risk', {}).get('geometry_tamper')),
        ('模板件齐备（title/author/maketitle/abstract）',
         all('R3' not in r for r in rep.get('review', []))),
        ('孤寡行/浮动体/视觉版式', None),  # 残余人工逐页抽查（operator 判据原文：C/D 语义部分仍需人工）
    ])
    D = sec([
        ('cite↔bibitem 全对账', all('E3' not in e for e in rep['errors'])),
        ('multiply_defined=0', lm.get('multiply_defined_labels') == 0 if lm else None),
        ('文献无"列而未引"', all('W2' not in w for w in rep['warnings'])),
        ('引用角标不与标点/脚注重叠', None),  # 视觉项，人工抽查
    ])
    return {'A_arxiv_compilable': A, 'B_pdf_technical': B,
            'C_typography': C, 'D_citations': D}


def main():
    ap = argparse.ArgumentParser(description='论文级刚性自洽检查器（G3a）：'
                                            'tex 静态检查＋log 指标＋PDF 层＋开源工具 battery')
    ap.add_argument('tex')
    ap.add_argument('--log', default=None, help='编译日志（L 族指标＋overfull 量化）')
    ap.add_argument('--pdf', default=None, help='PDF 路径（默认取 <tex>.pdf，存在即查）')
    ap.add_argument('--report', default=None)
    ap.add_argument('--no-battery', action='store_true', help='跳过外部检查器 battery')
    ap.add_argument('--no-pdf', action='store_true', help='跳过 PDF 层检查')
    a = ap.parse_args()
    rep = lint(a.tex, a.log)

    # L 族：日志指标（lint 内部若已读 log，这里复用同一路径解析）
    rep['review'] = []
    if a.log:
        apply_log_metrics(parse_log_metrics(open(a.log, encoding='utf-8', errors='ignore').read()),
                          rep['errors'], rep['warnings'], rep['stats'])

    # R 族：高风险排版命令（REVIEW 层，不判错）
    hr = high_risk_scan(open(a.tex, encoding='utf-8').read())
    if hr['commands']:
        rep['review'].append(f"R1 高风险排版命令：{hr['commands']}（只统计不判错；"
                             '负间距/缩放/tiny 类逐处人工复核）')
    if hr['geometry_tamper']:
        rep['review'].append(f"R2 版面干预命令 {len(hr['geometry_tamper'])} 处：{hr['geometry_tamper'][:5]}"
                             '（geometry/长度改写——若模板为官方文档类，私自改版心需说明）')
    tc = template_compliance_scan(open(a.tex, encoding='utf-8').read())
    if tc:
        rep['review'].append('R3 模板合规：' + '；'.join(tc))
    rep['stats']['high_risk'] = hr

    # P 族：PDF 层
    pdf = a.pdf or (a.tex[:-4] + '.pdf' if a.tex.endswith('.tex') else None)
    if not a.no_pdf and pdf and os.path.exists(pdf):
        rep['battery_pdf'] = check_pdf(pdf, rep['errors'], rep['warnings'],
                                       rep['review'], rep['stats'])

    if not a.no_battery:
        uncited = re.findall(r'W2 参考文献列而未引 \d+ 条: \[(.*?)\]', ' '.join(rep['warnings']))
        internal_uncited = {k.strip() for k in uncited[0].split(',')} if uncited else set()
        rep['battery'] = run_battery(a.tex, rep['errors'], rep['warnings'],
                                     rep['stats'], internal_uncited)

    rep['ok'] = not rep['errors']
    rep['arxiv_readiness'] = arxiv_readiness(rep)
    print(f"== paper_lint: {a.tex} ==")
    print(f"结论: {'PASS' if rep['ok'] else 'FAIL'} | "
          f"ERROR {len(rep['errors'])} | WARN {len(rep['warnings'])} | REVIEW {len(rep['review'])}")
    print('  arXiv readiness: '
          + ' | '.join(f"{k.split('_')[0]}:{v['status']}"
                       for k, v in rep['arxiv_readiness'].items()))
    for e in rep['errors']:
        print('  ERROR  ' + e)
    for w in rep['warnings']:
        print('  WARN   ' + w)
    for r in rep['review']:
        print('  REVIEW ' + r)
    for k, v in rep['stats'].items():
        print(f'  stat   {k} = {v}')
    for name, b in rep.get('battery', {}).items():
        print(f"  batt   {name}: {b['status']}"
              + (f" | {b.get('note', '')[:80]}" if b.get('note') else ''))
    for name, b in rep.get('battery_pdf', {}).items():
        if isinstance(b, dict):
            print(f"  pdf    {name}: {b.get('status', '?')}"
                  + (f" | {b.get('note', '')[:60]}" if b.get('note') else ''))
    if a.report:
        json.dump(rep, open(a.report, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('report ->', a.report)
    return 0 if rep['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
