#!/usr/bin/env python3
"""人门决策账本（gate ledger，评估建议⑤：放行不再只是聊天记录里的引语）

GATES.md 定义了门状态机，但历史放行证据只存在于 RUN-LOG 的引语里。本工具
把每个放行/驳回决策写成追加式 JSONL（谁、哪个门、范围、依据、原话出处），
与六态账本同级别可审计。

用法:
  python3 gate_log.py add  <ledger.jsonl> --gate L5 --decision approve \
         --by operator --scope "N06,N14" [--note "..."] [--source "RUN-LOG §..."]
  python3 gate_log.py list <ledger.jsonl> [--gate L5] [--last 10]

decision ∈ approve | reject | defer；add 原子追加（逐行 JSON，损坏行报错不静默）。
"""
import argparse
import datetime
import json
import os
import sys

DECISIONS = ('approve', 'reject', 'defer')


def read_entries(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding='utf-8') as f:
        for k, ln in enumerate(f, 1):
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                print(f'FATAL: {path}:{k} 行损坏（不静默跳过）', file=sys.stderr)
                sys.exit(2)
    return out


def main():
    ap = argparse.ArgumentParser(description='人门决策账本')
    ap.add_argument('cmd', choices=['add', 'list'])
    ap.add_argument('ledger')
    ap.add_argument('--gate', default=None)
    ap.add_argument('--decision', default=None, choices=DECISIONS)
    ap.add_argument('--by', default=None, help='决策者：operator / machine / operator-policy')
    ap.add_argument('--scope', default='', help='门覆盖的节点或批次，如 "L5: N06,N14"')
    ap.add_argument('--note', default='', help='决策要点')
    ap.add_argument('--source', default='', help='证据出处（RUN-LOG 小节 / 会话引语）')
    ap.add_argument('--last', type=int, default=None)
    a = ap.parse_args()

    if a.cmd == 'add':
        for k, v in (('gate', a.gate), ('decision', a.decision), ('by', a.by)):
            if not v:
                print(f'FATAL: add 需要 --{k}', file=sys.stderr); return 2
        entries = read_entries(a.ledger)
        entry = {
            'seq': (entries[-1]['seq'] + 1) if entries else 1,
            'ts': datetime.datetime.now().isoformat(timespec='seconds'),
            'gate': a.gate, 'decision': a.decision, 'by': a.by,
            'scope': a.scope, 'note': a.note, 'source': a.source,
        }
        os.makedirs(os.path.dirname(os.path.abspath(a.ledger)), exist_ok=True)
        with open(a.ledger, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        print(f'#{entry["seq"]} {entry["ts"]} {entry["gate"]} {entry["decision"]} by {entry["by"]}')
        return 0

    entries = read_entries(a.ledger)
    if a.gate:
        entries = [e for e in entries if e['gate'] == a.gate]
    if a.last:
        entries = entries[-a.last:]
    if not entries:
        print('（账本为空或无匹配条目）')
        return 0
    print(f'{"#":>3}  {"ts":19}  {"gate":<10}{"decision":<9}{"by":<16}scope')
    for e in entries:
        print(f'{e["seq"]:>3}  {e["ts"]:19}  {e["gate"]:<10}{e["decision"]:<9}'
              f'{e.get("by", ""):<16}{e.get("scope", "")}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
