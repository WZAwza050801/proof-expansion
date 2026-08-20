# 人门状态机与确认模式（Gates）

- 日期：2026-08-18
- 用途：论文写作流水线（拆题 → 逐块扩写 → 拼接）里"人工确认"如何落地。信任不交给 AI，交给结构与可配置的确认模式。
- 与 `CHUNKED-PAPER-WRITING-DESIGN.md` §2 配合；本文件是 gates 的唯一事实源。

## 1. 四个门

| 门 | 位置 | 人确认什么 | 未通过时 |
|---|---|---|---|
| G0 拆题 | 依赖树生成后 | 树粒度、依赖最简、约定卡无歧义、根=头号定理 | 返回拆题，改树，不扩写 |
| G1 逐块 | 每个引理扩写后 | 该块证明正确且严谨，可进全局账本 | 重扩该块（或其前置） |
| G2 拼接 | 整体处理拼接后 | 全文连贯、无重复、结论链闭合；机械前置＝G2a 每块 `coverage_check.py` 断言＋编译探针通过，G2b 装配指令合法＋组装编译全绿（DESIGN §4.5） | 回改对应块或拼接器 |
| G3 结论 | 论文定稿前 | 全局审读；（实验语境）盲评分只当证据 | 修订或降级结论 |

## 2. 确认模式（confirm_policy，可自由选，像 manual / yolo）

| 模式 | 行为 | 适用 |
|---|---|---|
| `manual` | 每个门都停，逐块（G1 每引理）人确认后才继续 | 老师不信任 AI、或承重论文 |
| `per-batch` | G1 按"一批互不依赖的引理"打包确认，其余门照停 | 想省事又不全放手 |
| `yolo` | 全自动推进，所有产物＋哈希＋谁生成什么全程记账；仅在末尾保留可选 G3 | 快速草稿、探路、跑 A/B 数据 |

- `manual` 是默认；`yolo` 的每一件产物仍完整落盘（`runs/pretest/` 或 run 目录），事后可逐件复查——区别只在"确认发生在推进前还是推进后"。
- 三种模式共用同一套**审计账本**（六态 claim 账本 + 门状态），只是推进规则不同。
- **提问方式**：门里或流程中任何"停下来问人"都按 `common/ASK-HUMAN-CONVENTION.md` 用大白话问，问完的回答进账本。

### 2.1 与调度器 I4 的合成规则（2026-08-19 补）

`confirm_policy` 与调度器按污染半径算出的档位是**两套机制**，必须明确合成方式，否则同一批会出现"文件说 yolo、调度器说 manual"的矛盾。规则：

> **`confirm_policy` 是人类愿意接受的最松档位，不是覆盖开关。生效档位 = 取严(confirm_policy, 污染半径建议)。**

- 声明 `yolo` **不能**让污染 36/37 的节点免检——上一轮全程 yolo，恰好把最该看人的地方（N00–N03，污染 34–36）放过了；
- 声明 `manual` 可以把算法认为安全的节点也拉回人门（承重论文、不信任 AI 时用）；
- 调度器的 `plan` / `next` 会同时打印两者与取严结果，不允许静默矛盾。

污染半径 → 建议档位（`gate_of()`，n = 节点总数）：

| 污染半径 | 建议 |
|---|---|
| ≥ 0.5 n | `manual` |
| ≥ 0.1 n | `per-batch` |
| 其余 | `yolo` |

## 3. 节点/门状态机

```
拆题:  tree: candidate → (G0) approved
节点:  node: pending → expanded → (G1) human_approved → 可供后继引用
拼接:  spliced → (G2) human_approved
结论:  final → (G3) accepted
```

- `manual`：节点必须 `human_approved` 才能被后继节点引用。
- `yolo`：`expanded` 自动视为 `human_approved`（账本里记 `auto`，标注"未经人确认"）。
- 任何 `human_approved` 之前的改动只影响本节点；之后的改动要级联重跑受影响的子节点（DAG 反向闭包）。

## 4. 配置落点

- `dep-tree.template.json` 顶层加 `confirm_policy: manual | per-batch | yolo`；
- 每节点加 `status: pending | expanded | human_approved`（由流水线推进，非拆题 agent 填写）；
- 队列状态机（`queue.yml`）的 `candidate → ready → …` 保持不变；论文写作流水线的门状态单独记在 dep-tree 侧车账本，不与实验题包队列混用。
