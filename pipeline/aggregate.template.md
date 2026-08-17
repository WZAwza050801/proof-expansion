# {{RUN_ID}} — Aggregate Report

> ⚠️ **v2 过渡标注（2026-08-18）**：本模板的维度（H/D/R/C）为 v1 旧口径；v2 口径 = C 门槛＋G/R/L 主指标（40/30/30）＋诚实护栏（含 lazy_stop），见 `experiment-design.md` §1.2/§6。模板与 `aggregate_stats.rb` 的维度改名列入阶段 3 基础设施同步。

- split: {{DEV_OR_EVAL}}
- 状态标注：本文件是统计汇总，不是数学证明；judge 分数是实验数据，不等于数学事实。
- deterministic input: `aggregate.data.json`（script/version/hash: {{...}}）
- {{DEV 时必填：本 run 为 dev，仅验证流水线，不构成提示词有效性证据。}}

## 1. 审计与数据有效性

| 检查 | 结果 | 影响 |
|---|---|---|
| package/route/patch validation | | |
| A/B pair 完整性 | 有效 pair / invalid pair | |
| 匿名泄漏检查 | | |
| unscorable (`judge_unverified`) submissions | | |
| 问题 cluster 数（每模型） | | CI 是否 estimable |
| capability probe | | |

无效 pair 或不可评分 submission 不得静默删去；其 private/anonymous id 与原因列入本节。

## 2. 统计单位与参数

- pair = 同一 `model × problem × variant × repetition` 的 A/B；
- repetitions 先在 variant 内等权平均；variants 再在 problem 内等权平均；
- bootstrap cluster = problem-level mean，draws = {{10000}}，seed = {{...}}；
- failure-mode rate denominator = 每条件具有有效 judge JSON 的匿名 submission 数。

## 3. 分模型、分维度结果（不报单一总分）

| 模型 | 指标 | 有效 pair | variant cluster | problem cluster | 平均 B−A | 95% CI | 可估计 | 0.5/CI 门 | 结论 |
|---|---|---:|---:|---:|---:|---|---|---|---|
| M1 | H | | | | | | | | |
| M1 | D | | | | | | | | |
| M1 | R | | | | | | | | |
| M1 | C | | | | | | | C ≥ -0.25 | |

`improved(model, H/D/R)` 仅在 `estimable=true && mean≥0.5 && CI lower>0` 时为真；C 是护栏，不以 0.5 门判断。

## 4. Eval 成功标准逐条对照（仅 eval）

| 标准 | 计算证据 | 结果 | 满足 |
|---|---|---|---|
| ≥2 个主指标达到改善 | 列出 H/D/R 及满足的模型 | | |
| 每计入指标 CI 下界 >0 且均值≥0.5 | 逐模型 CI/mean | | |
| 至少两个写手模型方向一致且均达改善 | 每指标模型清单 | | |
| C 护栏不破 | 每模型 C mean | | |
| ≥1 失败模式 B 低于 A | 见 §5 | | |
| 无 invalid pair / blocking unscorable record | 见 §1 | | |

结论：`initial_effectiveness` / `not_shown`；dev 一律 `dev_validation_only`。

## 5. 失败模式与残缺变体

| 失败模式 | A 分子/分母 | A rate | B 分子/分母 | B rate | B<A | 代表匿名稿 |
|---|---:|---:|---:|---:|---|---|
| fabricated_dependency | | | | | | |
| hidden_gap | | | | | | |
| assumption_drift | | | | | | |
| conditional_overclaim | | | | | | |
| false_skip | | | | | | |

| 变体 | 条件 | 有效 submissions | 正确识别并报告缺口 | 尝试证明错误命题 |
|---|---|---:|---:|---:|

## 6. 数据质量警告与恢复

- route mismatch、JSON 缺字段、judge_unverified、匿名泄漏、缺失 pair、统计退化等；
- 每个警告必须说明：是否阻断本 run、是否新建 run retry、是否影响结论。

## 7. 可复现信息

- package/prompt/manifest/input/output SHA-256；
- 模型 provider/model/max tokens、调用时间、child session ids；
- bootstrap script、参数、seed；
- analyst prompt/version；
- aggregate 写入者（父 Harness session id）与 analyst response hash。
