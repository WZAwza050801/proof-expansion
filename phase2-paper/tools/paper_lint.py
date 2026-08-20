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


def main():
    ap = argparse.ArgumentParser(description='论文级刚性自洽检查器（G3a）')
    ap.add_argument('tex')
    ap.add_argument('--log', default=None, help='编译日志（用于 overfull 量化）')
    ap.add_argument('--report', default=None)
    a = ap.parse_args()
    rep = lint(a.tex, a.log)
    print(f"== paper_lint: {a.tex} ==")
    print(f"结论: {'PASS' if rep['ok'] else 'FAIL'} | errors {len(rep['errors'])} | warnings {len(rep['warnings'])}")
    for e in rep['errors']:
        print('  ERROR  ' + e)
    for w in rep['warnings']:
        print('  WARN   ' + w)
    for k, v in rep['stats'].items():
        print(f'  stat   {k} = {v}')
    if a.report:
        json.dump(rep, open(a.report, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('report ->', a.report)
    return 0 if rep['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
