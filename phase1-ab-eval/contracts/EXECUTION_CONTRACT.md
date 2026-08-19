# Proof Expansion Execution Contract

- 版本：`v0.3`（阶段 3 同步，2026-08-18：题包 schema 改 v2（`proof_spine`/`spine_answer_key`/六态/窄缝标定）；评分维度 C/G/R/L；写手输出为纯证明正文，无 `<response>` 信封）
- 目的：把“由 agent 临场理解”的流程变成可机械审计的执行规则。
- 优先级：本文件高于 `RUNBOOK.md` 的简写说明；实验判定仍以 `phase1-ab-eval/experiment-design.md` 为准。

---

## 1. 真相源与不可变边界

| 数据 | 真相源 | 可否改写 |
|---|---|---|
| 题目与 reference proof | frozen package | `ready` 后不可改；建新版本 |
| A/B 条件映射 | `runs/<run-id>/manifest.yml` | 只在 materialize 阶段写；之后不可改 |
| 原始 writer/judge 输出 | `writers/`、`reviews/` | 永不改写 |
| 匿名评审输入 | `anonymous/` | materialize 后不可改 |
| 确定性统计 | `aggregate.data.json` | 由脚本新建；重算开新 run |
| 人工/agent 解释 | `aggregate.md` | 仅由父 Harness 写入 analyst 返回的原文 |

任何错误都以**新 package version 或新 run id**处理；不得修补旧 artefact。

---

## 2. 路由优先级

执行 route 的优先级（高→低）：

1. **preset role row 的 pinned `agentOptions`**：唯一实际执行真相；
2. package `run_policy`：必须与 role row 完全一致；
3. queue `writer_models`：必须与 package 完全一致；
4. 用户自然语言请求：只可选择已经存在的 role，不得覆盖 route。

任一冲突 → queue item `blocked`，记录三方值，不得降级或猜测。

当前映射：

```text
terra_curator  -> micu/gpt-5.6-terra
writer_closed  -> deepseek-official/deepseek-v4-flash (P001 smoke only)
judge_blind    -> micu/gpt-5.6-sol
analyst_stats  -> read-only, no model pin
```

正式 M1/M2/M3 前，必须新增 `writer_m1_closed`、`writer_m2_closed`、`writer_m3_closed`：每一行零工具、`maxDepth:0`、pinned provider/model/maxTokens、独立 tool name，并 mount-validate。

---

## 3. Package validation

在 claim 前必须运行：

```bash
ruby phase1-ab-eval/tools/validate_package.rb --package <package.yml> --queue phase1-ab-eval/queue.yml \
  --writer-role <locked-role> --writer-provider <provider> --writer-model <model>
```

非零退出即 hard fail。一个 package 只有满足以下条件才能由 `candidate` 变 `ready`：

1. `package_id` 非空且全局唯一；
2. `writer_bundle` 与 `judge_bundle` 都存在；writer bundle 不得包含 reference proof、failure annotations、judge rubric 或 variant expected outcome；
3. `allowed_dependencies` 的每个 `id` 非空且唯一；
4. 每个 selected variant 有非空 `variant_id`、`expected_outcome`、`writer_bundle_patch`；
5. `source_record` 符合项目 Evidence Rule；正式 dev/eval 不能用 `unverified-source`；
6. 人工批准字段对应 split 为 true；
7. package `run_policy` 与 queue、preset 路由无冲突。

内部 `smoke_only: true` package 可豁免文献原文要求，但其 `evidence_status` 必须写 `not-applicable-smoke`，且不得进入任何文献、数学或有效性结论。

---

## 4. Variant materialization（确定性）

对每个 selected variant，执行器从未改动的 `writer_bundle` 创建内存副本，依次执行：

1. `remove_dependency_ids`：逐个删除同 ID dependency；若目标不存在、重复指定或删除后 dependency ID 不唯一 → hard fail；
2. `replace_statement`：`null` 表示不变；非 null 必须为非空字符串，完整替换 `writer_bundle.statement`；
3. `replace_proof_spine`：`null` 表示不变；非 null 必须为非空字符串，完整替换 `writer_bundle.proof_spine`（v1 的 `replace_proof_skeleton` 已废弃，v2 schema 下 validator 视为非法字段，见 validate_package.rb）；
4. `append_allowed_dependencies`：追加后所有 ID 必须非空且全局唯一；
5. 写出 materialized bundle 的 canonical text 和 SHA-256 hash 到 job/manifest；
6. 不允许任何隐式文本删除、手工改写或“按意图理解”。

Judge 输入必须含：

```text
- materialized writer bundle（与 A/B 完全相同）
- selected variant 的完整 record：variant_id、modification、expected_outcome
- package judge_bundle
- anonymous writer output
```

当 `expected_outcome` 与 `judge_bundle.reference_proof` 看似冲突时：selected variant 的 `expected_outcome` 控制该变体是否应报告缺口；reference proof 仅作为完整原题的数学锚点。冲突本身是 package validation failure。

---

## 5. Pair、匿名与审计链

### 5.1 Pair identity

每个 A/B 对必须共享且只共享：

```text
pair_id = package_id + variant_id + writer_role + provider + model + repetition
```

每个 `pair_id` 恰有两个 submissions：一个 `condition:A`、一个 `condition:B`。缺失、重复、模型不一致、variant 不一致、patch hash 不一致、token budget 不一致 → entire pair invalid，禁止统计。

### 5.2 私有 manifest 与匿名文件

- `manifest.yml` 是唯一含 `condition` 和 `private_id` 的 artefact；
- materialize 前按 private_id 字典序建立列表，用记录的 Fisher–Yates seed 生成 permutation；
- anonymous id 固定为 `ANON-%03d`，按 permutation position 编号；
- manifest 必须记录 `permutation` 中的 `position/private_id/anonymous_id` 三元组；
- `anonymous/ANON-###.md`、review prompt、review filename 中禁止出现：`condition`、`private_id`、`-A`、`-B`、prompt 文件名、原始路径；
- 对同 pair 的 A/B，除 anonymous writer output 与 anonymous id 外，所有 judge 输入文本 hash 必须一致；不一致 → anonymity failure。

### 5.3 必需审计字段

每个 submission 必须记录：pair_id、private_id、anonymous_id、package/variant/repetition、writer role/provider/model/maxTokens、prompt version/hash、materialized bundle hash、input hash、output hash/path、时间戳、child session id、tool-lock probe reference、review path/status、route check。

---

## 6. Queue claim、幂等与恢复

队列项状态：`candidate → ready → claimed → running → reviewed → aggregated`，异常进入 `blocked`。

- `claimed` 必须写 `claim.run_id`、`owner_session_id`、`claimed_at`、`lease_expires_at`；
- 已有非过期 claim 的 item 不得被第二个 session 启动；
- session 恢复时：按 manifest 的 `writer_status/review_status` 继续，只派发 `pending`；不得重派 `completed`；
- lease 过期只允许 owner 或人工确认后转 `blocked`/重新 claim；
- retry 一律新 run id，旧 run 保留；
- queue 更新前后均检查当前状态是否符合允许转换，否则 hard fail。

---

## 7. Operator contamination boundary

- `terra_curator` 是唯一可为 package 搜索资料的角色；
- package `ready` 后，operator 不得搜索、补充、删减或改写任何 writer/judge 内容；
- writer/judge prompt 只能由 frozen package + versioned prompt + deterministic patch materialize；
- 每个 job 的完整输入 hash 必须保存，因此任何后注入都可被检测；
- writer/judge 一律经 role-locked tools，通用 delegation/workflow 不可使用。

---

## 8. 角色工具锁证据

每个 run 的 `manifest.yml.capability_evidence` 必须含：

- preset id/package validation reference；
- writer/judge role name、configured allow list、maxDepth、pinned route；
- 两个独立 preflight child probe（writer 与 judge）的 session id、原始回答、预期 `visible_tools=[]`；
- 若任一 probe 声称可用工具，或 child route 与 pinned route 不一致，整个 run `blocked`。

该记录证明配置与探针结果；它不把模型自述误当作唯一安全证据，role filter 的硬依据仍是 mount-validated preset 配置。
