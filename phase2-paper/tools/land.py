#!/usr/bin/env python3
"""agent 产物落盘守卫（幂等落盘，评估建议③：让"重复派发"从要小心变成无害）

背景事故：L9 卡顿后重派靠人核对防重复落盘；写手只回文本、operator 代落盘，
这一步没有机器保护。本工具把落盘变成受账本监护的原子操作：

  - 目标不存在        -> tmp + os.replace 原子写入（action=created）
  - 目标存在且逐字节同 -> 不重写不换 mtime（action=unchanged，幂等重放无害）
  - 目标存在且内容异  -> 拒绝（exit 3），除非显式 --replace（action=replaced）
  - 每次尝试追加一行 JSONL 到账本（含新旧 sha256）

用法:
  python3 land.py <src> <dest> [--ledger <land-ledger.jsonl>] [--replace] [--note "..."]
"""
import argparse
import datetime
import hashlib
import json
import os
import sys


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def append_ledger(ledger, entry):
    if not ledger:
        return
    os.makedirs(os.path.dirname(os.path.abspath(ledger)), exist_ok=True)
    with open(ledger, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def main():
    ap = argparse.ArgumentParser(description='幂等落盘守卫')
    ap.add_argument('src')
    ap.add_argument('dest')
    ap.add_argument('--ledger', default=None, help='JSONL 账本路径（建议 <run_dir>/land-ledger.jsonl）')
    ap.add_argument('--replace', action='store_true', help='内容不同时允许覆盖（默认拒绝）')
    ap.add_argument('--note', default='', help='备注（如派发来源、重试轮次）')
    a = ap.parse_args()

    if not os.path.exists(a.src):
        print('FATAL: 源文件不存在 ' + a.src, file=sys.stderr); return 2
    new = open(a.src, 'rb').read()
    new_sha = sha256_bytes(new)

    def log(action, old_sha=None):
        append_ledger(a.ledger, {
            'ts': datetime.datetime.now().isoformat(timespec='seconds'),
            'action': action, 'src': a.src, 'dest': a.dest,
            'sha256': new_sha, 'sha256_old': old_sha, 'note': a.note})

    if os.path.exists(a.dest):
        old = open(a.dest, 'rb').read()
        old_sha = sha256_bytes(old)
        if old == new:
            log('unchanged', old_sha)
            print(f'unchanged {a.dest}（逐字节一致，未重写）')
            return 0
        if not a.replace:
            log('refused', old_sha)
            print(f'REFUSED {a.dest}\n  已存在且内容不同（旧 {old_sha[:12]} / 新 {new_sha[:12]}）。'
                  f'确认覆盖请加 --replace。', file=sys.stderr)
            return 3
        tmp = a.dest + '.tmp'
        with open(tmp, 'wb') as f:
            f.write(new)
        os.replace(tmp, a.dest)
        log('replaced', old_sha)
        print(f'replaced {a.dest}（旧 {old_sha[:12]} -> 新 {new_sha[:12]}）')
        return 0

    d = os.path.dirname(os.path.abspath(a.dest))
    os.makedirs(d, exist_ok=True)
    tmp = a.dest + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(new)
    os.replace(tmp, a.dest)
    log('created')
    print(f'created  {a.dest}（{len(new)} bytes, {new_sha[:12]}）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
