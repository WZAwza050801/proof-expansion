#!/usr/bin/env python3
"""run manifest 生成与校验（可复现性缺口落地，评估建议②）

背景：模型/路由/写手来源等只记在 RUN-LOG 散文里，无机器可读账。本工具把
一个运行目录的全部产物（sha256）＋管线代码/提示词版本（sha256）＋ meta
固化成 manifest.json；verify 重算并报漂移（改动/新增/丢失）。

用法:
  python3 run_manifest.py gen    <run_dir> [--out manifest.json] [--meta k=v ...]
  python3 run_manifest.py verify <run_dir> [--manifest manifest.json]

规则:
  - 收录：run_dir 顶层的 *.json/*.md/*.tex/*.pdf/*.log ＋ 子目录 blocks/
    fragments/ frag-inputs/ taskbooks/ reviews/ sources/ 内全部常规文件；
    排除 manifest 自身与 .DS_Store（符号链接跟随目标哈希——归档件同样入账）。
  - code 段：phase2-paper 的 scheduler/tools/prompts 逐文件 sha256——
    闸门脚本或提示词一改，verify 即报 CODE-DRIFT。
  - 退出码：gen 0；verify 干净 0，有漂移 1。
"""
import argparse
import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PHASE2 = os.path.dirname(HERE)          # phase2-paper/
ROOT = os.path.dirname(PHASE2)          # 仓库根

TOP_GLOBS = ('*.json', '*.md', '*.tex', '*.pdf', '*.log')
SUBDIRS = ('blocks', 'fragments', 'frag-inputs', 'taskbooks', 'reviews', 'sources')
CODE_DIRS = (os.path.join(PHASE2, 'scheduler'), HERE,
             os.path.join(PHASE2, 'prompts'))
SKIP_NAMES = {'.DS_Store', 'manifest.json'}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def collect_files(run_dir):
    out = []
    for name in sorted(os.listdir(run_dir)):
        p = os.path.join(run_dir, name)
        if name in SKIP_NAMES:
            continue
        if os.path.isfile(p):
            out.append(p)
        elif name in SUBDIRS and os.path.isdir(p):
            for base, _dirs, files in os.walk(p):
                for fn in sorted(files):
                    if fn not in SKIP_NAMES:
                        out.append(os.path.join(base, fn))
    return out


def code_versions():
    out = {}
    for d in CODE_DIRS:
        for base, _dirs, files in os.walk(d):
            if '__pycache__' in base:
                continue
            for fn in sorted(files):
                if fn.endswith(('.py', '.md')):
                    p = os.path.join(base, fn)
                    out[os.path.relpath(p, ROOT)] = sha256(p)
    return out


def snapshot(run_dir):
    files = {}
    for p in collect_files(run_dir):
        rel = os.path.relpath(p, run_dir)
        files[rel] = {'sha256': sha256(p), 'bytes': os.path.getsize(p)}
    return files


def cmd_gen(run_dir, out_path, metas):
    manifest = {
        'generated_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'run_dir': os.path.basename(os.path.abspath(run_dir)),
        'meta': dict(metas),
        'code': code_versions(),
        'files': snapshot(run_dir),
    }
    tmp = out_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, out_path)
    print(f'manifest -> {out_path}（{len(manifest["files"])} 产物，'
          f'{len(manifest["code"])} 代码/提示词条目）')
    return 0


def cmd_verify(run_dir, manifest_path):
    with open(manifest_path, encoding='utf-8') as f:
        old = json.load(f)
    cur_files, old_files = snapshot(run_dir), old['files']
    drift = []
    for rel in sorted(set(cur_files) | set(old_files)):
        if rel not in cur_files:
            drift.append(f'MISSING  {rel}')
        elif rel not in old_files:
            drift.append(f'ADDED    {rel}')
        elif cur_files[rel]['sha256'] != old_files[rel]['sha256']:
            drift.append(f'CHANGED  {rel}')
    code_drift = [k for k in sorted(set(old.get('code', {})) | set(code_versions()))
                  if old.get('code', {}).get(k) != code_versions().get(k)]

    print(f'verify {manifest_path}（基线 {old.get("generated_at")}，meta={old.get("meta")}）')
    if drift:
        print(f'!! 产物漂移 {len(drift)} 处:')
        for d in drift:
            print('   ' + d)
    if code_drift:
        print(f'!! 代码/提示词漂移 {len(code_drift)} 处（复现条件已变）:')
        for k in code_drift:
            print('   ' + k)
    if not drift and not code_drift:
        print('干净：产物与代码/提示词均与 manifest 一致。')
        return 0
    return 1


def main():
    ap = argparse.ArgumentParser(description='run manifest 生成/校验')
    ap.add_argument('cmd', choices=['gen', 'verify'])
    ap.add_argument('run_dir')
    ap.add_argument('--out', default=None, help='manifest 输出路径（默认 <run_dir>/manifest.json）')
    ap.add_argument('--manifest', default=None, help='verify 用的 manifest 路径')
    ap.add_argument('--meta', action='append', default=[], metavar='k=v',
                    help='任意键值对（如 --meta model=micu/gpt-5.6-sol），可重复')
    a = ap.parse_args()
    run_dir = a.run_dir
    if not os.path.isdir(run_dir):
        print('FATAL: 不是目录 ' + run_dir, file=sys.stderr); return 2
    if a.cmd == 'gen':
        metas = {}
        for kv in a.meta:
            if '=' not in kv:
                print('FATAL: --meta 需要 k=v 形式: ' + kv, file=sys.stderr); return 2
            k, v = kv.split('=', 1)
            metas[k] = v
        return cmd_gen(run_dir, a.out or os.path.join(run_dir, 'manifest.json'), metas)
    return cmd_verify(run_dir, a.manifest or os.path.join(run_dir, 'manifest.json'))


if __name__ == '__main__':
    sys.exit(main())
