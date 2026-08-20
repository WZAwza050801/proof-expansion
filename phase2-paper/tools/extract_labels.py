#!/usr/bin/env python3
# label 清单提取器：从 fragments 机械提取 \label/\begin{env} 清单 → labels.json
# 用途：coordinator（调度编辑）的输入元数据之一——它被规则④禁止读块正文，
#       但 label 映射需要真实 label；本脚本把 label 变成无损元数据（不携正文）。
# 用法: python3 extract_labels.py <fragments_dir> <out.json>
import json, re, sys, os

def main():
    frag_dir, out_path = sys.argv[1], sys.argv[2]
    inv = {}
    for f in sorted(os.listdir(frag_dir)):
        m = re.fullmatch(r'(N\d+)\.md', f)
        if not m: continue
        nid = m.group(1)
        t = open(os.path.join(frag_dir, f), encoding='utf-8').read()
        sec = re.search(r'【块正文】\s*\n(.*?)(?=【|\Z)', t, re.S)
        body = sec.group(1) if sec else ''
        labels = re.findall(r'\\label\{([^}]+)\}', body)
        envs = re.findall(r'\\begin\{(theorem|lemma|proposition|corollary|conjecture|definition|example|remark|comparisonlemma)\}', body)
        inv[nid] = {'labels': labels, 'theorem_envs': envs, 'file': f}
    json.dump(inv, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'{len(inv)} nodes ->', out_path)
    for nid, d in inv.items():
        print(f"  {nid}: {len(d['labels'])} labels, envs={d['theorem_envs']}")

if __name__ == '__main__':
    main()
