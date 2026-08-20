#!/usr/bin/env python3
"""论文级刚性自洽检查器（S5 论文级审查轮·机械件，DESIGN §4.4 / GATES G3a）

定位：编译门查"能不能编译"，本工具查"作为一篇论文自不自洽"。零 LLM、纯机械、
每项检查对应一类已实证或 arXiv 投稿标准明确要求的自洽义务。operator 2026-08-21
定调："一篇 latex 论文应该有很多专门的刚性程序判定是否自洽"——本文件是落地。

用法:
  python3 paper_lint.py <paper.tex> [--log <compile.log>] [--report r.json]

退出码: 0=无 error（可有 warning），1=存在 error，2=用法错误。
回归测试: phase2-paper/tests/test_gates.py（负样本必红）。
"""
import argparse
import collections
import json
import os
import re
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


def main():
    ap = argparse.ArgumentParser(description='论文级刚性自洽检查器（G3a）')
    ap.add_argument('tex')
    ap.add_argument('--log', default=None, help='编译日志（用于 overfull 量化）')
    ap.add_argument('--report', default=None)
    ap.add_argument('--no-battery', action='store_true',
                    help='跳过外部开源检查器 battery（仅内部 E/W）')
    a = ap.parse_args()
    rep = lint(a.tex, a.log)
    if not a.no_battery:
        uncited = re.findall(r'W2 参考文献列而未引 \d+ 条: \[(.*?)\]', ' '.join(rep['warnings']))
        internal_uncited = {k.strip() for k in uncited[0].split(',')} if uncited else set()
        rep['battery'] = run_battery(a.tex, rep['errors'], rep['warnings'],
                                     rep['stats'], internal_uncited)
    print(f"== paper_lint: {a.tex} ==")
    print(f"结论: {'PASS' if rep['ok'] else 'FAIL'} | errors {len(rep['errors'])} | warnings {len(rep['warnings'])}")
    for e in rep['errors']:
        print('  ERROR  ' + e)
    for w in rep['warnings']:
        print('  WARN   ' + w)
    for k, v in rep['stats'].items():
        print(f'  stat   {k} = {v}')
    for name, b in rep.get('battery', {}).items():
        print(f"  batt   {name}: {b['status']}"
              + (f" | {b.get('note', '')[:80]}" if b.get('note') else ''))
    if a.report:
        json.dump(rep, open(a.report, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('report ->', a.report)
    return 0 if rep['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
