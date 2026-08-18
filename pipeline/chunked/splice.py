#!/usr/bin/env python3
# 分块撰写流水线：拼接器 + 确定性一致性检查器（stdlib only）
# 用法: python3 splice.py <spec.json> <outputs_dir> <assembled.md> <check-report.json>
import json, re, sys, os

def fail(msg):
    print('FATAL:', msg, file=sys.stderr)
    sys.exit(2)

def load_spec(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def load_block_outputs(spec, outdir):
    outs = {}
    for b in spec['blocks']:
        p = os.path.join(outdir, b['id'] + '.md')
        if not os.path.exists(p):
            fail(f'缺少块输出 {p}')
        text = open(p, encoding='utf-8').read()
        parts = {}
        for name in ('正文', '结论', '依赖与未决'):
            m = re.search(r'【' + name + r'】\s*\n(.*?)(?=【|\Z)', text, re.S)
            parts[name] = (m.group(1).strip() if m else '')
        if not parts['正文']:
            fail(f'{b["id"]} 的【正文】为空')
        outs[b['id']] = parts
    return outs

def normalize_lines(text):
    return [re.sub(r'\s+', ' ', ln).strip() for ln in text.splitlines() if ln.strip()]

def check(spec, outs):
    report = {'paper_id': spec['paper_id'], 'ok': True, 'warnings': [], 'errors': []}
    ids = [b['id'] for b in spec['blocks']]
    by_id = {b['id']: b for b in spec['blocks']}
    err = report['errors']; warn = report['warnings']

    # 0. DAG 无环 + 拓扑序（spec 顺序即拓扑序）
    for i, b in enumerate(spec['blocks']):
        for d in b['deps']:
            if d not in by_id:
                err.append(f'{b["id"]}: 依赖 {d} 不在块列表中')
            elif ids.index(d) >= i:
                err.append(f'{b["id"]}: 依赖 {d} 排在它后面（非拓扑序/有环）')

    # 1. 引用完整性
    for b in spec['blocks']:
        body = outs[b['id']]['正文'] + '\n' + outs[b['id']]['结论']
        mentions = set(re.findall(r'(?:块|B)(\d+)|(?:D)(\d+)', body))
        # 归一化: (kind, num)
        refs = []
        for m in re.finditer(r'块([A-Za-z0-9]+)|B(\d+)|D(\d+)', body):
            if m.group(1):
                refs.append(('block', m.group(1)))
            elif m.group(2):
                refs.append(('block', m.group(2)))
            else:
                refs.append(('dep', m.group(3)))
        block_refs = set(('B' + r[1] if r[1].isdigit() else r[1]) for r in refs if r[0] == 'block')
        dep_refs = set(r[1] for r in refs if r[0] == 'dep')
        for r in block_refs:
            if r not in b['deps']:
                warn.append(f'{b["id"]}: 引用了块 {r}，但未在 spec.deps 声明')
        for r in dep_refs:
            if 'D' + r not in b['allowed']:
                warn.append(f'{b["id"]}: 引用了 D{r}，但未在 spec.allowed 声明')
        for d in b['deps']:
            if not outs[d]['结论']:
                err.append(f'{b["id"]}: 前置块 {d} 的【结论】为空')

    # 2. 结论链闭合
    hb = spec['headline_block']
    if hb not in by_id:
        err.append(f'headline_block {hb} 不存在')
    elif not outs[hb]['结论']:
        err.append(f'头号块 {hb} 的【结论】为空')

    # 3. 符号一致性
    card = spec.get('conventions', {})
    local_syms = {}
    for b in spec['blocks']:
        text = outs[b['id']]['依赖与未决']
        for line in text.splitlines():
            m = re.match(r'符号[:：]\s*(\S+)\s*[:=]\s*(.+)', line.strip())
            if not m:
                continue
            name, meaning = m.group(1), m.group(2).strip()
            if name in card:
                if card[name].strip() != meaning:
                    err.append(f'{b["id"]}: 符号 {name} 与全局约定卡冲突（{meaning} vs {card[name]}）')
            elif name in local_syms:
                if local_syms[name] != meaning:
                    err.append(f'{b["id"]}: 符号 {name} 与另一块的局部定义不一致')
            else:
                local_syms[name] = meaning
    report['symbols'] = {'card': list(card.keys()), 'local': list(local_syms.keys())}

    # 4. 重复检测（跨块相同长句）
    lines_by_block = {b['id']: [l for l in normalize_lines(outs[b['id']]['正文']) if len(l) >= 60] for b in spec['blocks']}
    seen = {}
    for bid, lines in lines_by_block.items():
        for ln in lines:
            seen.setdefault(ln, []).append(bid)
    dups = {ln: bl for ln, bl in seen.items() if len(bl) > 1}
    if dups:
        warn.append(f'跨块重复长句 {len(dups)} 处，供拼接器删除')
        report['duplicated_lines'] = {ln: bl for ln, bl in list(dups.items())[:10]}

    report['ok'] = len(err) == 0
    return report

def assemble(spec, outs):
    parts = [f'# {spec.get("title", spec["paper_id"])}\n']
    if spec.get('conventions'):
        parts.append('## 记号约定\n')
        for k, v in spec['conventions'].items():
            parts.append(f'- ${k}$：{v}')
        parts.append('')
    for b in spec['blocks']:
        parts.append(f'## {b["id"]} {b["title"]}\n')
        parts.append(outs[b['id']]['正文'].strip())
        parts.append('\n')
    return '\n'.join(parts)

def main():
    spec_path, outdir, asm_path, rep_path = sys.argv[1:5]
    spec = load_spec(spec_path)
    outs = load_block_outputs(spec, outdir)
    report = check(spec, outs)
    asm = assemble(spec, outs)
    with open(asm_path, 'w', encoding='utf-8') as f:
        f.write(asm)
    with open(rep_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print('assembled ->', asm_path)
    print('check report ->', rep_path)
    print('ok =', report['ok'], '| errors =', len(report['errors']), '| warnings =', len(report['warnings']))
    if report['errors']:
        for e in report['errors']:
            print('  ERROR:', e)
    for w in report['warnings'][:10]:
        print('  WARN :', w)
    sys.exit(0 if report['ok'] else 1)

if __name__ == '__main__':
    main()
