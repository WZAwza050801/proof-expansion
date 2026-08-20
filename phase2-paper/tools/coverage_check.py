#!/usr/bin/env python3
# 内容覆盖断言器（DESIGN.md §4.0 规则③ / §4.1 G2a 段断言 / §4.2 全文内容覆盖断言）
# 背景：Seidel 编辑轮事故——7 页降质稿被当成品，因当时无任何"内容被压缩"检查。
# 本脚本补上：长度比 + 公式/定理环境/六态标注计数，全部机械判定，不信口头保证。
#
# 用法:
#   段断言（G2a）:
#     python3 coverage_check.py segment <segment_output.md|tex> <block1.md> [block2.md ...] \
#            [--threshold 0.8] [--allow-count-drop] [--report report.json]
#   全文断言（2b 内容覆盖）:
#     python3 coverage_check.py paper <assembled.tex> <baseline.md> \
#            [--threshold 0.8] [--allow-count-drop] [--report report.json]
#
# 检查项（全部退出码判定：0=PASS，1=FAIL）:
#   1. 长度比：产出非空白字符数 >= 输入非空白字符数 × threshold（默认 0.8，operator 定）
#   2. 计数不降（除非 --allow-count-drop，此时降级为 warning 并计入报告）:
#      - 行内公式 $...$ 对数
#      - 显示公式 \[...\] 与 equation/align/gather/multline 环境
#      - 定理类环境（theorem/lemma/proposition/corollary/definition/remark/example/conjecture）
#      - 六态标注 \tag{FIXED|PROVED|CONDITIONAL|CANDIDATE|BLOCKED|UNVERIFIED}
import json, re, sys, os

DISPLAY_ENVS = r'(?:equation|align|gather|multline|eqnarray)\*?'
THEOREM_ENVS = r'(?:theorem|lemma|proposition|corollary|definition|remark|example|conjecture|comparisonlemma)'
SIX_STATES = r'(?:FIXED|PROVED|CONDITIONAL|CANDIDATE|BLOCKED|UNVERIFIED)'


def extract_section(text, name):
    """取【name】小节；不存在则返回 None。"""
    m = re.search(r'【' + name + r'】\s*\n(.*?)(?=【|\Z)', text, re.S)
    return m.group(1) if m else None


def input_text_of(path):
    """块原文（.md）：取【正文】＋【结论】；其余文件类型取全文。"""
    text = open(path, encoding='utf-8').read()
    body = extract_section(text, '正文')
    if body is None:
        return text
    concl = extract_section(text, '结论') or ''
    return body + '\n' + concl


def output_text_of(path):
    """成文产物：若含【段正文】/【块正文】标记则只取该节；否则全文。"""
    text = open(path, encoding='utf-8').read()
    for marker in ('块正文', '段正文'):
        seg = extract_section(text, marker)
        if seg is not None:
            return seg
    return text


def metrics(text):
    dollars = len(re.findall(r'(?<!\\)\$', text))
    return {
        'chars_nospace': len(re.sub(r'\s+', '', text)),
        'inline_math': dollars // 2,
        'display_math': len(re.findall(r'\\\[', text))
        + len(re.findall(r'\\begin\{' + DISPLAY_ENVS + r'\}', text)),
        'theorem_envs': len(re.findall(r'\\begin\{' + THEOREM_ENVS + r'\}', text)),
        # 状态标注计数：任何 \tag{...} 与 [STATUS: ...] 都算（词表式会漏 PROVED-IN-PROJECT 等变体）
        'six_state_tags': len(re.findall(r'\\tag\{[^}]*\}|\[STATUS:\s*[^\]]*\]', text)),
    }


def compare(inp, outp, threshold, allow_drop):
    report = {'ok': True, 'length_ratio': None, 'errors': [], 'warnings': [],
              'input': inp, 'output': outp}
    err, warn = report['errors'], report['warnings']

    ratio = outp['chars_nospace'] / inp['chars_nospace'] if inp['chars_nospace'] else 1.0
    report['length_ratio'] = round(ratio, 4)
    if ratio < threshold:
        err.append(f"长度比 {ratio:.3f} < 阈值 {threshold}"
                   f"（输入 {inp['chars_nospace']} → 产出 {outp['chars_nospace']} 非空白字符）——疑似内容被压缩/摘要")

    for key in ('inline_math', 'display_math', 'theorem_envs', 'six_state_tags'):
        i, o = inp[key], outp[key]
        if o < i:
            msg = f"{key} 计数下降：输入 {i} → 产出 {o}"
            if allow_drop:
                warn.append(msg + '（--allow-count-drop 已显式豁免，operator 自担）')
            else:
                err.append(msg + '——内容丢失，禁摘要/禁删证明（splicer v0.2 硬约束 1）')

    report['ok'] = len(err) == 0
    return report


def main():
    args = sys.argv[1:]
    if len(args) < 3:
        print(__doc__)
        sys.exit(2)
    mode, out_path = args[0], args[1]
    in_paths = [args[2]]
    rest = args[3:]
    threshold, allow_drop, report_path = 0.8, False, None
    while rest:
        a = rest.pop(0)
        if a == '--threshold':
            threshold = float(rest.pop(0))
        elif a == '--allow-count-drop':
            allow_drop = True
        elif a == '--report':
            report_path = rest.pop(0)
        elif not a.startswith('--'):
            in_paths.append(a)  # segment 模式的第 2..n 个块文件
        else:
            print('未知参数:', a, file=sys.stderr); sys.exit(2)

    if mode == 'segment':
        inp_text = '\n\n'.join(input_text_of(p) for p in in_paths)
        src = {'files': in_paths}
    elif mode == 'paper':
        inp_text = input_text_of(in_paths[0])  # baseline（paper.md）无块标记时自动取全文
        src = {'baseline': in_paths[0]}
    else:
        print('模式必须是 segment 或 paper', file=sys.stderr); sys.exit(2)

    outp_text = output_text_of(out_path)
    rep = compare(metrics(inp_text), metrics(outp_text), threshold, allow_drop)
    rep['mode'] = mode
    rep['source'] = src
    rep['target'] = out_path
    rep['threshold'] = threshold

    if report_path:
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
        print('report ->', report_path)

    print(f"[{mode}] {out_path}")
    print(f"  长度比 {rep['length_ratio']}（阈值 {threshold}）")
    for k in ('inline_math', 'display_math', 'theorem_envs', 'six_state_tags'):
        print(f"  {k}: 输入 {rep['input'][k]} → 产出 {rep['output'][k]}")
    for e in rep['errors']:
        print('  ERROR:', e)
    for w in rep['warnings']:
        print('  WARN :', w)
    print('PASS' if rep['ok'] else 'FAIL')
    sys.exit(0 if rep['ok'] else 1)


if __name__ == '__main__':
    main()
