# 一期：A/B 对照测评

- 状态：设计与基础设施就绪；**尚未产出任何可进入统计的数据**。
- 判分口径唯一事实源：`phase1-ab-eval/experiment-design.md`（跑前冻结＝预注册）
- 执行协议：`phase1-ab-eval/contracts/EXECUTION_CONTRACT.md`（高于 RUNBOOK）

## 研究问题

不是"模型能不能写出看起来完整的证明"，而是：

> 给定去答案化的证明骨架，**精细化提示词（B）**是否比**普通提示词（A）**稳定产出更完整、更严谨、更可读的证明？

任务 = **证明补全**。不考独立证明能力（骨架已消解"数学难"），不考诚实审计（降为护栏）。

## 判分

| | 含义 | 权重 |
|---|---|---|
| **C** | 数学正确性 | **门槛**（不过则该份作废） |
| **G** | 补全度 | 40 |
| **R** | 严谨性 | 30 |
| **L** | 可读性 | 30 |

三类题分工：**窄缝题**（区分度主力，唯一进 A/B 结论）、探针题（测上限）、秒杀题（排除）。窄缝是 model-relative 的，靠预测试标定，不凭出题人感觉定档。

## 一份数据要能进统计，必须同时满足

出自 `contracts/EXECUTION_CONTRACT.md`：

1. `pair_id` = package+variant+role+provider+model+repetition，**恰好一个 A 一个 B**，且两者 token budget 一致（§5.1）；
2. `manifest.yml` 记录 condition / private_id / permutation（§5.2）；
3. 匿名化：Fisher–Yates seed 落盘，`ANON-%03d` 编号，judge 输入文本 hash 除匿名正文外全同（§5.2）；
4. `judge_blind` 零工具盲评（§4）；
5. `capability_evidence` 含两个独立工具锁探针的 session id 与原始回答（§8）；
6. `validate_package.rb` 通过（§3）；
7. `aggregate_stats.rb` bootstrap 出 `aggregate.data.json`（STATISTICS_CONTRACT）。

**七条缺一不可。** 2026-08-18 的 Seidel 冒烟 0/7 命中，所以那轮所有产物都是预演级，一个数字都不能引用。

## 目录

```
experiment-design.md   预注册设计（§1 任务定义 / §6 rubric）
skill-contract.md      条件 B 的过程干预规范
prompts/               writer-A-baseline  writer-B-skill  judge-reviewer  terra-curator  analyst
contracts/             EXECUTION  STATISTICS  CALIBRATION  RUNBOOK
tools/                 aggregate_stats.rb  validate_package.rb  calibration_kappa.rb  + 模板
problems/              12 道题池 + SELFTEST.md（窄缝定档记录）
packages/  queue.yml   题包与队列
rubric-samples/        评分样例
archive/               已作废/已完成：STAGE-1-PLAN  P001-SMOKE-BLOCKER  DESIGN-REFLECTION 等
```

## 路由（角色行是唯一执行真相）

```
terra_curator  -> micu/gpt-5.6-terra          maxTokens 32768
writer_closed  -> deepseek-official/v4-flash  maxTokens 65536  零工具
judge_blind    -> micu/gpt-5.6-sol            maxTokens 65536  零工具
analyst_stats  -> read/glob/grep 只读，无模型 pin
```

**写死的教训**：reasoning token 计入 `maxTokens`。`16384` 曾让 3/4 冒烟任务截断（`archive/P001-SMOKE-BLOCKER.md` §9）。2026-08-19 把 `judge_blind` 从 16384 提到 65536——同一个坑，之前只修了写手那行。

## 待办

1. 阶段 2 正式预测试：**必须在 proof-pipeline preset 会话**用零工具角色行跑；
2. 人工复核 S10 的"秩 d"陈述（对照 arXiv:2306.08567）；
3. Terra 再切 2–3 个方向，论文档题池扩到 5；
4. 阶段 4 小步校准：验证 B 在 G/R/L 上胜 A，通过后冻结写手提示词；
5. 阶段 5 正式矩阵（1–4 全部校准后才允许）。
