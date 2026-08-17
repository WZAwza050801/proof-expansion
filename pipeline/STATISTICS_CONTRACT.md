# Proof Expansion Statistics Contract

- 版本：`v0.2`
- 执行者：父 Harness 运行 `pipeline/aggregate_stats.rb`；`analyst_stats` 仅解释输出。
- > ⚠️ **v2 过渡标注（2026-08-18）**：本契约的维度字母（H/D/R/C）为 v1 旧口径，已按 `pipeline/DESIGN-REFLECTION.md` R2 作废。v2 口径 = C（门槛）＋G 补全度/R 严谨性/L 可读性（主指标，权重 40/30/30）＋诚实护栏，见 `experiment-design.md` §1/§6 与 `prompt-gpt56sol-reviewer.md` v2。本契约与 `aggregate_stats.rb`/`aggregate.template.md`/`calibration_kappa.rb` 的维度改名列入**阶段 3 基础设施**同步；在同步完成前不开启任何新 run。

## 1. 可评分 submission 与 pair

- 只有同时拥有完整、合法 judge JSON 的 A/B submission 才是可评分 pair；
- 若任意 submission 的 step audit 含 `judge_unverified` 且 `impact=blocks_main_conclusion`，该 submission `unscorable`，其 pair invalid；
- 缺失/重复/route mismatch/prompt hash mismatch/patch hash mismatch 同样使 pair invalid；
- invalid pair 不得静默删除：保留在 `aggregate.data.json.validation.invalid_pairs`，使 eval run 判 `not_shown`。

## 2. 统计层级（固定）

对每个写手模型与指标 H/D/R/C：

1. **pair level**：每个合法 pair 计算 `d = score(B) - score(A)`；
2. **variant level**：对同一 `model × problem × variant` 的所有合法 repetitions 等权平均 d；
3. **problem level**：对同一 `model × problem` 的所有 selected variants 的 variant mean 等权平均 d；
4. **bootstrap cluster**：problem-level d 是唯一重采样单元。每次 bootstrap 对 N 个问题有放回采样 N 次，计算 sample mean；
5. 10,000 次、记录 seed、用 sorted percentile 的 2.5%/97.5% 作为 95% CI。

因此重复不会因数量多而压过其它题目；同题多个变体也不会因变体多而压过其它题目。

若某模型有效 problem clusters < 2：CI 标为 `null`、`estimable:false`，不允许计入任何改善主张。

## 3. 指标判读

对每个模型 m、指标 x：

```text
improved(m,x) = estimable
             AND mean_diff(m,x) >= 0.5
             AND ci95_lower(m,x) > 0

guardrail(m,C) = estimable AND mean_diff(m,C) >= -0.25
```

- 一个主指标 x（H/D/R）在 run 级别“达改善”当且仅当至少两个模型满足 `improved(m,x)`；
- 跨模型方向一致 = 至少两个模型对该 x 的 `mean_diff > 0`，且这两个模型均达改善；
- `overallImproved` 禁用，禁止产生该模糊字段；
- eval 的 `initial_effectiveness` 还需要 `experiment-design.md §1.2` 的全部条件；否则 `not_shown`；
- dev 永远是 `dev_validation_only`。

## 4. Failure-mode rate

对每个失败模式、每个条件：

```text
rate = 含该失败模式的有效 judge submission 数 / 有效 judge submission 总数
```

- 分母固定为有效匿名 submission，不是 step、问题或 variant；
- unscorable/invalid pair 不计入分子或分母，但必须单列数量；
- “定向减少”只在 `rate_B < rate_A` 且两个条件的有效分母均 > 0 时可写；样本过小只能描述，不能满足有效性条件。

## 5. 输出

`aggregate_stats.rb` 生成 `aggregate.data.json`，包含：

- validation（pair/route/hash/anonymity/scoring eligibility）；
- 每模型每指标：pair/variant/problem counts、mean diff、CI、estimable；
- invalid/unscorable records；
- 失败模式分子分母；
- bootstrap parameters。

`analyst_stats` 把上述值解释成 `aggregateMarkdown`，父 Harness 不得改写其数学/统计判断。