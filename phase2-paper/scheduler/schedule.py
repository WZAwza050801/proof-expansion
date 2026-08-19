#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""二期分块论文写作：确定性调度器（stdlib only）

把"operator 凭感觉派块"重构成可审计的算法。核心不变量：

  I1  依赖未落盘 => 拒发（上一轮 N19 从第 6 层空降的根因）
  I2  节点状态 = worst(自己声明的状态, 所有前置的有效状态)  —— 沿 DAG 单调传播
  I3  任务书的【前置结论】只能来自前置块已落盘的【结论】原文，不许由模型自行假设
  I4  人门档位由污染半径决定，不由 operator 心情决定

子命令
  validate   依赖图完整性（无环/引用存在/可达/拓扑序自洽/allowed 合法）
  plan       分层、关键路径、污染半径、风险分级、人门档位
  status     读 blocks/ 目录，解析六态，沿 DAG 传播，输出账本
  next       计算 frontier（前置全部落盘的待写节点），输出本批派发清单
  taskbook   为某节点生成四段任务书（前置结论从真实块文件取）
  spec       导出 splice.py 兼容的 spec JSON

用法
  python3 schedule.py validate  <dep-tree.json>
  python3 schedule.py plan      <dep-tree.json> [--json out.json]
  python3 schedule.py status    <dep-tree.json> --blocks <dir>
  python3 schedule.py next      <dep-tree.json> --blocks <dir> [--limit N]
  python3 schedule.py taskbook  <dep-tree.json> --blocks <dir> --node N04 [--out dir]
  python3 schedule.py spec      <dep-tree.json> --out spec.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# ── 状态：严重度从好到坏（与 dep-tree conventions.statuses 一致）──────
# PROVED-IN-PROJECT 本项目内已证 / IMPORTED-VERIFIED 外部结果已核原始来源 /
# CONDITIONAL 附加假设下成立 / FIXED 按约定视为已声明义务（未证）/
# CANDIDATE 仅候选陈述 / BLOCKED 卡住
STATES = ['PROVED-IN-PROJECT', 'IMPORTED-VERIFIED', 'CONDITIONAL',
          'FIXED', 'CANDIDATE', 'BLOCKED']
SEVERITY = {s: i for i, s in enumerate(STATES)}
NOT_LANDED = 'NOT-LANDED'

SECTIONS = ('正文', '结论', '依赖与未决')

# 人门档位严格度（GATES.md §2）
GATE_RANK = {'yolo': 0, 'per-batch': 1, 'manual': 2}


def die(msg: str, code: int = 2):
    print('FATAL: ' + msg, file=sys.stderr)
    sys.exit(code)


# ── 载入与图结构 ────────────────────────────────────────────────────

def load_tree(path: str) -> dict:
    if not os.path.exists(path):
        die('依赖图不存在: ' + path)
    with open(path, encoding='utf-8') as f:
        t = json.load(f)
    for k in ('nodes', 'headline_node'):
        if k not in t:
            die('依赖图缺少必需字段: ' + k)
    return t


class Graph:
    """依赖 DAG。边方向 = dep -> node（dep 必须先完成）。"""

    def __init__(self, tree: dict):
        self.tree = tree
        self.nodes = {n['id']: n for n in tree['nodes']}
        self.ids = [n['id'] for n in tree['nodes']]
        self.headline = tree['headline_node']
        self.conventions = tree.get('conventions', {})
        self.allowed_deps = {d['id']: d for d in tree.get('allowed_dependencies', [])}
        self.used_by: dict[str, list[str]] = {i: [] for i in self.ids}
        for i in self.ids:
            for d in self.nodes[i].get('deps', []):
                if d in self.used_by:
                    self.used_by[d].append(i)

    # --- 拓扑与分层 ---
    def toposort(self) -> list[str] | None:
        """Kahn。有环返回 None。"""
        indeg = {i: len(self.nodes[i].get('deps', [])) for i in self.ids}
        ready = sorted([i for i in self.ids if indeg[i] == 0])
        out: list[str] = []
        while ready:
            i = ready.pop(0)
            out.append(i)
            for c in sorted(self.used_by[i]):
                indeg[c] -= 1
                if indeg[c] == 0:
                    ready.append(c)
            ready.sort()
        return out if len(out) == len(self.ids) else None

    def levels(self) -> dict[str, int]:
        """层 = 最长路径深度。同层之间无依赖，可并行。"""
        order = self.toposort()
        if order is None:
            die('依赖图有环，无法分层（先跑 validate）')
        lv: dict[str, int] = {}
        for i in order:
            deps = self.nodes[i].get('deps', [])
            lv[i] = 0 if not deps else 1 + max(lv[d] for d in deps)
        return lv

    def descendants(self, i: str) -> set[str]:
        """下游闭包 = 该节点出错时的污染范围。"""
        seen: set[str] = set()
        stack = list(self.used_by[i])
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            stack.extend(self.used_by[x])
        return seen

    def ancestors(self, i: str) -> set[str]:
        seen: set[str] = set()
        stack = list(self.nodes[i].get('deps', []))
        while stack:
            x = stack.pop()
            if x in seen or x not in self.nodes:
                continue
            seen.add(x)
            stack.extend(self.nodes[x].get('deps', []))
        return seen

    def critical_path(self) -> list[str]:
        """到 headline 的最长依赖链（关键路径，无并行余量）。"""
        lv = self.levels()
        cur = self.headline
        path = [cur]
        while self.nodes[cur].get('deps'):
            cur = max(self.nodes[cur]['deps'], key=lambda d: (lv[d], d))
            path.append(cur)
        return list(reversed(path))

    # --- 风险与人门 ---
    def gate_of(self, i: str) -> tuple[str, int]:
        """人门档位由污染半径决定（I4）。返回 (档位, 污染数)。"""
        n = len(self.ids)
        c = len(self.descendants(i))
        if c >= 0.5 * n:
            return 'manual', c        # 半数以上下游作废 -> 必须人过目
        if c >= 0.1 * n:
            return 'per-batch', c     # 整层一起过目
        return 'yolo', c              # 自动推进

    def policy(self) -> str:
        """dep-tree 顶层 confirm_policy = 人类愿意接受的最松档位（GATES.md §2）。"""
        p = str(self.tree.get('confirm_policy', 'manual'))
        return p if p in GATE_RANK else 'manual'

    def effective_gate(self, i: str) -> tuple[str, str, int]:
        """取严：人类 confirm_policy 与算法建议中更严的一个胜出。

        confirm_policy 是"最松档位"而非覆盖开关：声明 yolo 不能让污染 36/37 的
        节点免检——上一轮全程 yolo 恰好把最该看人的地方放过了。
        返回 (生效档位, 算法建议, 污染数)。
        """
        suggested, c = self.gate_of(i)
        eff = suggested if GATE_RANK[suggested] >= GATE_RANK[self.policy()] else self.policy()
        return eff, suggested, c


# ── 块输出解析 ──────────────────────────────────────────────────────

def parse_block(path: str) -> dict:
    """解析三段式块输出 + 六态声明。"""
    text = open(path, encoding='utf-8').read()
    parts = {}
    for name in SECTIONS:
        m = re.search(r'【' + name + r'】\s*\n?(.*?)(?=【(?:' + '|'.join(SECTIONS) + r')】|\Z)', text, re.S)
        parts[name] = (m.group(1).strip() if m else '')
    # 状态：优先看【结论】，其次全文；取最坏的一个（诚实优先）
    found = [s for s in STATES if re.search(re.escape(s), parts['结论'])]
    if not found:
        found = [s for s in STATES if re.search(re.escape(s), text)]
    state = max(found, key=lambda s: SEVERITY[s]) if found else 'CANDIDATE'
    return {
        'path': path, 'body': parts['正文'], 'conclusion': parts['结论'],
        'open_items': parts['依赖与未决'], 'declared_state': state,
        'complete': bool(parts['正文']) and bool(parts['结论']),
    }


def load_blocks(g: Graph, blocks_dir: str) -> dict[str, dict]:
    out = {}
    if not os.path.isdir(blocks_dir):
        return out
    for i in g.ids:
        p = os.path.join(blocks_dir, i + '.md')
        if os.path.exists(p):
            out[i] = parse_block(p)
    return out


def effective_states(g: Graph, blocks: dict[str, dict]) -> dict[str, str]:
    """I2：有效状态 = worst(自己声明, 所有前置的有效状态)。沿拓扑序传播。"""
    order = g.toposort() or g.ids
    eff: dict[str, str] = {}
    for i in order:
        b = blocks.get(i)
        if b is None or not b['complete']:
            eff[i] = NOT_LANDED
            continue
        worst = b['declared_state']
        for d in g.nodes[i].get('deps', []):
            ds = eff.get(d, NOT_LANDED)
            if ds == NOT_LANDED:
                worst = 'CANDIDATE' if SEVERITY[worst] < SEVERITY['CANDIDATE'] else worst
            elif SEVERITY[ds] > SEVERITY[worst]:
                worst = ds
        eff[i] = worst
    return eff


# ── 子命令 ──────────────────────────────────────────────────────────

def cmd_validate(g: Graph) -> int:
    errs: list[str] = []
    warns: list[str] = []

    seen = set()
    for i in g.ids:
        if i in seen:
            errs.append('节点 id 重复: ' + i)
        seen.add(i)

    for i in g.ids:
        n = g.nodes[i]
        for f in ('title', 'statement', 'completion_test'):
            if not str(n.get(f, '')).strip():
                errs.append(f'{i}: 字段 {f} 为空')
        for d in n.get('deps', []):
            if d not in g.nodes:
                errs.append(f'{i}: 依赖 {d} 不存在')
            elif d == i:
                errs.append(f'{i}: 自依赖')
        for a in n.get('allowed', []):
            if g.allowed_deps and a not in g.allowed_deps:
                errs.append(f'{i}: allowed 中的 {a} 不在全局 allowed_dependencies')
        # D4: completion_test 空转 —— 与 statement 高度重合
        st, ct = str(n.get('statement', '')), str(n.get('completion_test', ''))
        if ct and st and (ct.strip() == st.strip()):
            warns.append(f'{i}: completion_test 与 statement 完全相同（空转判据）')

    order = g.toposort()
    if order is None:
        errs.append('依赖图有环（Kahn 未能覆盖全部节点）')

    if g.headline not in g.nodes:
        errs.append('headline_node 不存在: ' + str(g.headline))
    else:
        anc = g.ancestors(g.headline)
        orphan = [i for i in g.ids if i != g.headline and i not in anc]
        if orphan:
            warns.append('这些节点到不了 headline（白写）: ' + ' '.join(sorted(orphan)))

    tops = [i for i in g.ids if not g.used_by[i]]
    if len(tops) > 1:
        warns.append('有多个无人引用的顶点: ' + ' '.join(sorted(tops)))

    declared = g.tree.get('order')
    if declared:
        if sorted(declared) != sorted(g.ids):
            warns.append('order 字段与节点集合不一致')
        else:
            pos = {x: k for k, x in enumerate(declared)}
            for i in g.ids:
                for d in g.nodes[i].get('deps', []):
                    if d in pos and pos[d] >= pos[i]:
                        errs.append(f'order 非拓扑序: {i} 的依赖 {d} 排在它后面')

    print('=== validate ===')
    print(f'节点 {len(g.ids)} | 边 {sum(len(g.nodes[i].get("deps", [])) for i in g.ids)} '
          f'| 树需要的边 {len(g.ids) - 1}（多出的部分=引理复用，说明是 DAG 不是树）')
    for e in errs:
        print('  ERROR  ' + e)
    for w in warns:
        print('  WARN   ' + w)
    if not errs and not warns:
        print('  全部通过')
    print('\n结论: ' + ('FAIL' if errs else 'PASS' + ('（有 warning）' if warns else '')))
    return 1 if errs else 0


def cmd_plan(g: Graph, out_json: str | None) -> int:
    lv = g.levels()
    layers: dict[int, list[str]] = {}
    for i, k in lv.items():
        layers.setdefault(k, []).append(i)
    cp = g.critical_path()
    cpset = set(cp)

    print('=== plan ===')
    print(f'串行深度 {max(layers) + 1} 层 | 最宽 {max(len(v) for v in layers.values())} '
          f'| 理论最优加速比 {len(g.ids) / (max(layers) + 1):.2f}x（并行收益上限）')
    print(f'confirm_policy = {g.policy()}（人类允许的最松档位）；下表档位 = 取严(policy, 污染半径建议)')
    print()
    print('层  节点数  人门   节点（★=关键路径）')
    for k in sorted(layers):
        row = sorted(layers[k])
        gates = [g.effective_gate(i)[0] for i in row]
        gate = max(gates, key=lambda x: GATE_RANK[x])
        tag = ' '.join(('★' + i if i in cpset else ' ' + i) for i in row)
        print(f'L{k:<3}{len(row):^7}{gate:<10}{tag}')
    print()
    print('关键路径（%d 个节点，无并行余量，任一卡住=全局卡住）:' % len(cp))
    print('  ' + ' -> '.join(cp))
    print()
    print('高危节点（污染半径 = 该块出错时下游作废数）:')
    risk = sorted(((len(g.descendants(i)), i) for i in g.ids), reverse=True)
    for c, i in risk:
        if c < 0.1 * len(g.ids):
            break
        gate, sug, _ = g.effective_gate(i)
        mark = gate if gate == sug else '%s<-%s' % (gate, sug)
        print(f'  {i}  污染 {c:2d}/{len(g.ids) - 1}  [{mark}]  {g.nodes[i]["title"]}')

    if out_json:
        payload = {
            'n_nodes': len(g.ids),
            'serial_depth': max(layers) + 1,
            'max_width': max(len(v) for v in layers.values()),
            'layers': {str(k): sorted(v) for k, v in layers.items()},
            'critical_path': cp,
            'confirm_policy': g.policy(),
            'gates': {i: {'gate': g.effective_gate(i)[0], 'suggested': g.effective_gate(i)[1],
                          'contamination': g.effective_gate(i)[2]} for i in g.ids},
        }
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print('\n已写出 ' + out_json)
    return 0


def cmd_status(g: Graph, blocks_dir: str) -> int:
    blocks = load_blocks(g, blocks_dir)
    eff = effective_states(g, blocks)
    lv = g.levels()

    landed = [i for i in g.ids if i in blocks and blocks[i]['complete']]
    print('=== status ===')
    print(f'已落盘 {len(landed)}/{len(g.ids)} | blocks 目录: {blocks_dir}')
    print()
    if landed:
        print('节点  层   声明状态            有效状态            前置未落盘')
        for i in sorted(landed, key=lambda x: (lv[x], x)):
            missing = [d for d in g.nodes[i].get('deps', []) if eff.get(d) == NOT_LANDED]
            flag = (' '.join(missing) if missing else '—')
            degraded = '  <=降级' if eff[i] != blocks[i]['declared_state'] else ''
            print(f'{i:<6}{lv[i]:<5}{blocks[i]["declared_state"]:<20}{eff[i]:<20}{flag}{degraded}')
        print()
        # I3 违规：声称已证但前置根本没落盘
        bad = [i for i in landed
               if blocks[i]['declared_state'] in ('PROVED-IN-PROJECT', 'CONDITIONAL')
               and any(eff.get(d) == NOT_LANDED for d in g.nodes[i].get('deps', []))]
        if bad:
            print('!! I3 违规（前置未落盘却声称已证 —— 模型自行假设了前置）:')
            for i in bad:
                miss = [d for d in g.nodes[i]['deps'] if eff.get(d) == NOT_LANDED]
                print(f'   {i} 声称 {blocks[i]["declared_state"]}，但 {" ".join(miss)} 未落盘 -> 该块须重写')
            print()
    hl = eff.get(g.headline, NOT_LANDED)
    print(f'headline {g.headline} 有效状态: {hl}')
    if hl == NOT_LANDED:
        print('  => 论文尚未闭合')
    return 0


def cmd_next(g: Graph, blocks_dir: str, limit: int | None) -> int:
    """frontier = 自己未落盘、且所有前置都已落盘的节点。I1 在此强制。"""
    blocks = load_blocks(g, blocks_dir)
    eff = effective_states(g, blocks)
    lv = g.levels()

    todo = [i for i in g.ids if eff.get(i) == NOT_LANDED]
    frontier, blocked_by_deps = [], []
    for i in todo:
        miss = [d for d in g.nodes[i].get('deps', []) if eff.get(d) == NOT_LANDED]
        (blocked_by_deps if miss else frontier).append((i, miss))

    frontier.sort(key=lambda t: (lv[t[0]], t[0]))
    if not frontier:
        print('=== next ===')
        print('无可派发节点。' + ('论文已闭合。' if not todo else '全部待写节点的前置都没落盘（不该发生，先跑 validate）。'))
        return 0

    batch_level = lv[frontier[0][0]]
    batch = [i for i, _ in frontier if lv[i] == batch_level]
    if limit:
        batch = batch[:limit]
    effs = [g.effective_gate(i) for i in batch]
    gate = max((e[0] for e in effs), key=lambda x: GATE_RANK[x])
    sug = max((e[1] for e in effs), key=lambda x: GATE_RANK[x])

    print('=== next ===')
    print(f'本批 = L{batch_level}，{len(batch)} 个节点，可并行派发。人门档位: {gate.upper()}')
    print(f'  依据: confirm_policy={g.policy()}（人类最松档位） + 污染半径建议={sug} -> 取严={gate}')
    if gate == 'manual':
        print('  ！这批含高污染节点，按 I4 必须人工过目后才能进下一层')
    print()
    for i in batch:
        c = len(g.descendants(i))
        print(f'  {i}  污染 {c:2d}  前置 {" ".join(g.nodes[i].get("deps", [])) or "（无，叶子）"}')
        print(f'       {g.nodes[i]["title"]}')
    print()
    print(f'其余 {len(todo) - len(batch)} 个待写节点因前置未落盘被拒发（I1）。')
    print('生成任务书: python3 schedule.py taskbook <dep-tree.json> --blocks %s --node %s --out <dir>'
          % (blocks_dir, batch[0]))
    return 0


TASKBOOK_TMPL = """<!-- 任务书 自动生成 by schedule.py | node={node} layer=L{layer} gate={gate} 污染={contam} -->
你是分块论文撰写流水线中的「块写手」。你只负责本论文的**一个证明义务**，输入是局部上下文，
输出严格三段（缺一段即不合格）。不要复述背景，不要重写全局约定——拼接时会去重。

【全局约定卡】
{conventions}

【前置结论】
{predecessors}

【允许依赖】
{allowed}

【本块义务】
- 节点：{node}（{title}）
- 要建立：{statement}
- 完成判据（completion test）：{completion_test}

【纪律】
1. 只写本块的证明正文；引用前置块写「由 {ex_dep} 的结论：……」；引用允许依赖只写编号并核对其前提是否满足。
2. **不得假设任何未在【前置结论】中出现的结论。** 若确实需要包外事实，写进【依赖与未决】做最小 blocker，
   不要用「按约定视为已声明」把洞糊过去。
3. 六态标注（就地标在句末）：**(PROVED-IN-PROJECT)** 本项目内已证 / **(CONDITIONAL)** 仅在你写明的附加假设下成立 /
   **(FIXED)** 按约定视为已声明义务 / **(CANDIDATE)** 仅候选陈述 / **(BLOCKED)** 卡住。
   诚实优先：证不出来就报 BLOCKED + 最小 blocker + 你能证到的最强结论，这比编造更有价值。
4. 数学内容用 LaTeX（$...$ 与 \\begin{{...}}）。定理/引理用 amsthm 环境。

【输出格式 —— 严格三段，段名照抄】
【正文】
（本块证明正文）
【结论】
（一整句话的已证结论，能被下游块直接引用；句末必须带六态标注之一）
【依赖与未决】
（引用的节点编号与允许依赖编号；本块新引入的局部符号；未决卡点/最小 blocker）
"""


def cmd_taskbook(g: Graph, blocks_dir: str, node: str, out_dir: str | None) -> int:
    if node not in g.nodes:
        die('节点不存在: ' + node)
    blocks = load_blocks(g, blocks_dir)
    eff = effective_states(g, blocks)
    n = g.nodes[node]

    # I1：拒发
    missing = [d for d in n.get('deps', []) if eff.get(d) == NOT_LANDED]
    if missing:
        die('拒发（I1）：%s 的前置 %s 尚未落盘。先写完前置，或明确改图。'
            % (node, ' '.join(missing)), code=3)

    conv = '\n'.join('- %s：%s' % (k, v) for k, v in g.conventions.items()) or '（无）'
    preds = []
    for d in n.get('deps', []):
        b = blocks[d]
        preds.append('- 由 %s（%s）的结论：%s' % (d, g.nodes[d]['title'], b['conclusion'].strip()))
        if eff[d] != 'PROVED-IN-PROJECT':
            preds.append('  ↳ 注意：该前置的有效状态为 **%s**，你的结论至多同级。' % eff[d])
    pred_txt = '\n'.join(preds) or '（本块是叶子，无前置结论；只能用全局约定卡与允许依赖）'
    allow = []
    for a in n.get('allowed', []):
        d = g.allowed_deps.get(a)
        allow.append('- %s [%s]：%s' % (a, d.get('kind', ''), d['statement']) if d else '- ' + a)
    allow_txt = '\n'.join(allow) or '（本块不引用任何外部依赖）'
    gate, _sug, contam = g.effective_gate(node)

    text = TASKBOOK_TMPL.format(
        node=node, layer=g.levels()[node], gate=gate, contam=contam,
        conventions=conv, predecessors=pred_txt, allowed=allow_txt,
        title=n['title'], statement=n['statement'], completion_test=n['completion_test'],
        ex_dep=(n.get('deps') or ['N00'])[0],
    )
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        p = os.path.join(out_dir, node + '.taskbook.md')
        with open(p, 'w', encoding='utf-8') as f:
            f.write(text)
        print('已写出 ' + p)
    else:
        sys.stdout.write(text)
    return 0


def cmd_spec(g: Graph, out: str) -> int:
    """导出 splice.py 兼容 spec（nodes -> blocks，按拓扑序）。"""
    order = g.toposort()
    if order is None:
        die('有环，无法导出 spec')
    spec = {
        'paper_id': g.tree.get('paper_id', 'paper'),
        'title': g.nodes[g.headline]['title'],
        'headline_block': g.headline,
        'conventions': g.conventions,
        'allowed_dependencies': [d['id'] for d in g.tree.get('allowed_dependencies', [])],
        'blocks': [{
            'id': i, 'title': g.nodes[i]['title'],
            'objective': g.nodes[i]['statement'],
            'completion_test': g.nodes[i]['completion_test'],
            'deps': g.nodes[i].get('deps', []),
            'allowed': g.nodes[i].get('allowed', []),
        } for i in order],
    }
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    print('已写出 %s（%d 块，按拓扑序）' % (out, len(order)))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description='二期分块论文写作调度器')
    ap.add_argument('cmd', choices=['validate', 'plan', 'status', 'next', 'taskbook', 'spec'])
    ap.add_argument('tree')
    ap.add_argument('--blocks', default=None, help='块输出目录')
    ap.add_argument('--node', default=None)
    ap.add_argument('--out', default=None)
    ap.add_argument('--json', dest='json_out', default=None)
    ap.add_argument('--limit', type=int, default=None)
    a = ap.parse_args()

    g = Graph(load_tree(a.tree))
    if a.cmd == 'validate':
        return cmd_validate(g)
    if a.cmd == 'plan':
        return cmd_plan(g, a.json_out)
    if a.cmd in ('status', 'next', 'taskbook') and not a.blocks:
        die('%s 需要 --blocks <dir>' % a.cmd)
    if a.cmd == 'status':
        return cmd_status(g, a.blocks)
    if a.cmd == 'next':
        return cmd_next(g, a.blocks, a.limit)
    if a.cmd == 'taskbook':
        if not a.node:
            die('taskbook 需要 --node')
        return cmd_taskbook(g, a.blocks, a.node, a.out)
    if a.cmd == 'spec':
        if not a.out:
            die('spec 需要 --out')
        return cmd_spec(g, a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
