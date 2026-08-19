# 二期：分块论文写作流水线

- 状态：**调度器已重构（2026-08-19）**。上一轮"operator 凭感觉派块"已替换为确定性程序。
- 设计依据：`phase2-paper/DESIGN.md`；人门状态机：`phase2-paper/GATES.md`
- 与一期的关系：本期测**拼接级/工程级**质量，**不产生 A/B 分数**，不与 `phase1-ab-eval/` 的统计混用。

## 总流程

```
精简证明(charter)
   │ ① 拆题   prompts/splitter.md              → dep-tree.json（命题依赖 DAG）
   │ ② 审图   独立模型审 漏边/假边/粒度/判据空转  → dep-tree.v2.json  ★ 扩写前必做
   │ ③ 调度   scheduler/schedule.py            → 分层 + 人门档位 + 任务书
   │ ④ 扩写   零工具块写手角色（一节点一 agent） → blocks/N*.md（三段式）
   │ ⑤ 拼接   prompts/splicer.md + tools/splice.py → paper.tex + check-report.json
   ▼
完整论文
```

② 是这轮新增的一步。理由见下。

## 为什么要有调度器（上一轮的教训）

上一轮 6 块只成 1 块，而唯一成功的 N19 **也不算数**——它在第 6 层，9 个祖先一个都没写，于是它自己在文末写"引用 N08、N09、N14……均按本次流水线规则视为已声明义务 (FIXED)"，**假设前置成立**把证明写完了。

调度器把这类事故变成机械上不可能。四条不变量：

| | 不变量 | 强制方式 |
|---|---|---|
| **I1** | 依赖未落盘 ⇒ 拒发 | `taskbook` 退出码 3；`next` 只吐 frontier |
| **I2** | 有效状态 = worst(自己声明, 所有前置) | 沿拓扑序单调传播；`status` 显示降级 |
| **I3** | 【前置结论】只能是上游块已落盘的原文 | 任务书由程序拼装；纪律禁止"按约定视为已声明" |
| **I4** | 人门档位由污染半径决定，不由心情决定 | `gate_of()`：污染 ≥ 50% 节点数 → manual |

实测：对旧产物跑 `status`，N19 被自动判为 `PROVED-IN-PROJECT → CANDIDATE` 降级并报 I3 违规；`taskbook --node N19` 直接拒发。

## 依赖结构不是树，是 DAG

Seidel charter 拆出的 38 节点，**81 条边**（v2 补边后 98 条），而树只需 37 条。**25 个节点被两个以上下游引用**（N28 被 5 个，N07/N10/N18/N29 各被 4 个）——引理复用，数学证明的依赖结构必然如此。

后果：**不能递归下降分治**；同一条引理被多处引用时必须保证各处看到**同一份**结论。这是全局约定卡 + `splice.py` 符号一致性检查存在的理由。

实测形状（`plan`，v2）：

```
串行深度 24 层 | 最宽 3 | 理论最优加速比 1.58x
L0(2) L1(1) L2(1) L3(2) L4(3) L5(2) L6(2) L7(3) L8(3) L9(2) L10(2)
L11–L19 各 1 个   ← 9 层单链，无并行余量
L20(3) L21(1) L22(1) L23(1)
```

**并行收益上限只有 1.58x，所以优先级是正确性而不是吞吐。**

污染半径（该块出错则下游作废数）：`N01/N00` 36、`N02` 35、`N03` 34、`N07` 30、`N10` 27、`N14/N09` 22。
**前 7 层全部 manual** —— 投入产出比最高的人工介入点就在这里。

## 用法

```bash
S=phase2-paper/scheduler/schedule.py
T=runs/pretest/seidel/dep-tree.v2.json
B=runs/pretest/seidel/blocks

python3 $S validate $T                     # 环 / 悬空引用 / 孤儿 / order 自洽 / 判据空转
python3 $S plan     $T --json plan.json    # 分层、关键路径、污染半径、人门档位
python3 $S next     $T --blocks $B         # 本批可派发节点（只吐前置全落盘的）
python3 $S taskbook $T --blocks $B --node N00 --out runs/pretest/seidel/taskbooks/
python3 $S status   $T --blocks $B         # 六态账本 + I3 违规检测
python3 $S spec     $T --out spec.json     # 导出 splice.py 兼容 spec
python3 phase2-paper/tools/splice.py spec.json $B paper.md check-report.json
```

标准循环：`next` → 为该批每个节点 `taskbook` → 派发 → 落盘 `blocks/N*.md` → `status` 查降级 → 过人门 → 回到 `next`。

## 派发纪律（上一轮两个坏点的修法）

1. **必须走 preset 角色行**，不用通用 `workflow`/`subagent` 派发。角色行是 route / 预算 / 工具锁的唯一执行真相；而 `workflow` 的 `agent()` 连 `maxTokens` 这个选项都不存在——P001 那条"reasoning 计入 maxTokens，须给 65536"的教训在那条路径上**表达不出来**。这也是 `phase1-ab-eval/contracts/EXECUTION_CONTRACT.md` §7 明文禁止的事。
2. **agent 只回文本，operator 落盘**。块写手是零工具角色，物理上不可能自己写文件——这是闭卷设计的必然结果，不是缺陷。

## 输出契约（块写手，三段缺一不合格）

```
【正文】        只写本块；不复述背景与全局约定（拼接后不许有重复段）
【结论】        一整句话，能被下游块直接引用；句末必须带状态标注
【依赖与未决】  引用的节点/依赖编号；新引入的局部符号；最小 blocker
```

状态标注，严重度从好到坏：
`PROVED-IN-PROJECT` → `IMPORTED-VERIFIED` → `CONDITIONAL` → `FIXED` → `CANDIDATE` → `BLOCKED`

Seidel 是 open problem，**预期大量 BLOCKED 而非完整证明**。报 BLOCKED + 最小 blocker + 能证到的最强结论比编造有价值——`status` 会把它诚实传播到 headline，最终定理会被写成"在 A1–A7 假设下成立"。
