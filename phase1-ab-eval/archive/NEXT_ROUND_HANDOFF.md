# Proof Expansion：下一轮标准化执行交接

- 版本：`v0.3`
- 交接状态：**执行契约、统计与校准 gate 已静态审查；2026-08-17 首次动态冒烟在 §4.1 探针处被阻（角色行 `maxDepth: 0` 与 DSH 语义冲突），已修复 preset 并记录证据，见 §9 与 `phase1-ab-eval/archive/P001-SMOKE-BLOCKER.md`。**
- 本文件面向下一位 Harness operator。它规定冒烟、dev 先导、eval 前置门和失败处理；不得凭聊天记忆改写流程。
- > ⚠️ **v2 过渡标注（2026-08-18）**：本交接的评分维度（H/D/R/C）、题目包 schema 与写手信封为 v1 旧口径。v2 口径见 `phase1-ab-eval/experiment-design.md` v2（§1 任务=证明补全、§5.1 v2 题包、§6 C/G/R/L 权重）、`phase1-ab-eval/prompts/terra-curator.md` v2、`phase1-ab-eval/prompts/judge-reviewer.md` v2、`phase1-ab-eval/archive/writer-v04-direction.md`。执行链（validator/stats/信封）的同步列入阶段 3；同步完成前，本文件 §4–§6 的冒烟/先导/eval 流程**不得**用于新 run。

---

## 0. 一句话目标

把一个经人工批准、已冻结的题目包，稳定地变成：

```text
闭卷 A/B 配对写手输出
→ 私有标签、公开匿名稿
→ micu/gpt-5.6-sol 严格盲审 JSON
→ 仅统计角色恢复 A/B 标签
→ append-only aggregate.md
```

这套流水线测的是**缺口诚实性、假设/依赖管理、可审阅性**，不是把模型输出认证为数学证明。

---

## 1. 审查结论（本轮已核对）

| 项目 | 状态 | 结论 |
|---|---|---|
| 用户自有 preset `proof-pipeline` | 已 mount-validate | `valid`；未修改 shipped preset |
| Terra | 硬角色行 | `micu/gpt-5.6-terra`，可搜索/读写，`maxDepth:1` |
| 写手 | 硬角色行 | `writer_closed`，**零工具**、`maxDepth:1`，当前 smoke 锁 `deepseek-official/deepseek-v4-flash` |
| Judge | 硬角色行 | `judge_blind`，**零工具**、`maxDepth:1`，锁 `micu/gpt-5.6-sol` |
| 统计 | 硬读角色 + 确定性脚本 | `aggregate_stats.rb` 算统计；`analyst_stats` 只读解释，父 Harness 逐字写 aggregate |
| A/B 公平性 | 已修复 | A/B 共用外层输出信封；B 的内部 ledger/步骤结构不再被当作 A 的格式失败 |
| 变体执行 | 已修复 | `writer_bundle_patch` 有固定顺序、冲突规则与 judge ground-truth 绑定 |
| 私有标签 | 已补齐 | manifest 记录 pair_id、hash、匿名 permutation、review order；是唯一 A/B 映射来源 |
| 校准 gate | 已补齐 | CSV + `calibration_kappa.rb` + weighted-kappa 阈值，未过门禁止 eval |
| 冒烟包 | 已入队 | `P001-smoke-harmonic-v1`，只验机制，不是 benchmark |
| 动态验收 | **未完成** | 必须先跑 §4 冒烟，才可称流水线“已验证” |

### 关键限制：硬与软的边界

- `writer_closed` 和 `judge_blind` 的无工具状态是 **DSH 创建期硬限制**：工具不出现在子 agent prompt 中且拒绝执行。
- `analyst_stats` 与 `terra_curator` 的“只改指定目录”是**操作协议**，不是 OS 级路径沙箱；operator 每次要审核写入路径与 git diff。
- 不要使用通用 `subagent`、`subagent_fork` 或 `workflow` 派闭卷写手/judge：它们不能施加 role tool filter。`phase1-ab-eval/archive/workflow-template.js` 已明确弃用。

---

## 2. 权威文件地图（读哪个，不要猜）

| 用途 | 文件 |
|---|---|
| 实验口径、成功条件、统计阈值 | `phase1-ab-eval/experiment-design.md` |
| Skill 行为边界 | `phase1-ab-eval/skill-contract.md` |
| 条件 A | `phase1-ab-eval/prompts/writer-A-baseline.md` |
| 条件 B | `phase1-ab-eval/prompts/writer-B-skill.md` |
| 盲审 JSON 契约 | `phase1-ab-eval/prompts/judge-reviewer.md` |
| 善后统计契约 | `phase1-ab-eval/prompts/analyst.md` |
| 题目包唯一 schema | `phase1-ab-eval/tools/problem-package.template.yml` |
| 执行、匿名、patch、route、queue 契约 | `phase1-ab-eval/contracts/EXECUTION_CONTRACT.md` |
| 统计单位、CI、failure-rate 契约 | `phase1-ab-eval/contracts/STATISTICS_CONTRACT.md` |
| 校准 gate | `phase1-ab-eval/contracts/CALIBRATION_PROTOCOL.md` |
| 私有 run 映射 schema | `phase1-ab-eval/tools/run-manifest.template.yml` |
| Package/route validator | `phase1-ab-eval/tools/validate_package.rb` |
| 确定性统计脚本 | `phase1-ab-eval/tools/aggregate_stats.rb` |
| Cohen's kappa 脚本 | `phase1-ab-eval/tools/calibration_kappa.rb` |
| 队列 | `phase1-ab-eval/queue.yml` |
| 状态机和文件布局 | `phase1-ab-eval/contracts/RUNBOOK.md` |
| 本交接 | `phase1-ab-eval/archive/NEXT_ROUND_HANDOFF.md` |

---

## 3. 开始前：硬门（任一失败即 `blocked`）

### 3.1 Session 门

1. 新开 DSH session；
2. 在 preset picker 选择 **Proof Expansion Evaluation Harness**（id: `proof-pipeline`）；
3. 不得在已有对话中途切换 preset；
4. 先让 Harness 列出可用角色工具：`terra_curator`、`writer_closed`、`judge_blind`、`analyst_stats`。缺任一个就停止。

### 3.2 题目包门

只有同时满足以下条件的 package 才能由 `candidate` 变 `ready`：

- `writer_bundle` 与 `judge_bundle` 完整且互相隔离；
- 来源记录完整；正式 benchmark 必须 `original_text_obtained: true`，且不能是 `unverified-source`；
- 人工批准记录存在；
- 每个被执行的 variant 有明确 `expected_outcome` 和 `writer_bundle_patch`；
- `run_policy` 写明 writer 路由、变体、重复、judge 路由；
- package 一旦 `ready`，只能新建版本，不能修改原文件。

### 3.3 模型门

当前固定路由：

```text
Terra:  micu / gpt-5.6-terra
Judge:  micu / gpt-5.6-sol
Smoke writer: deepseek-official / deepseek-v4-flash
```

任何固定 route 启动失败 → 队列项 `blocked`，记录错误；**不得静默降级模型**。

---

## 4. 第一件事：P001 冒烟测试（唯一允许先跑的 item）

目标不是测提示词有效，而是验证系统真实执行。队列中已有：

```text
P001-smoke-harmonic-v1
split=dev
variants=[full, missing_lemma]
writer=deepseek-v4-flash
repetitions=1
judge=micu/gpt-5.6-sol
```

### 4.1 前置能力探针（不记入 run）

先分别用 `writer_closed` 与 `judge_blind` 派两个独立探针，要求子 agent只报告它可用的工具/是否能搜索，不给任何题目。预期：两者均报告没有工具、不能搜索；judge probe 还要记录实际 route 为 `micu/gpt-5.6-sol`。任一能使用任何工具或 route 不符，停止冒烟并记录 capability leak。

### 4.2 Materialize（必须先写 manifest）

1. 在 queue 仍为 `ready` 且 `claim=null` 时，先运行 `validate_package.rb`；非零退出即停止；
2. 以 `EXECUTION_CONTRACT.md §6` claim queue item：写 run_id、owner session、lease，并检查无旧 claim；
3. 创建唯一 `run_id`，例如 `RUN-20260817-001-smoke`；
4. 创建 `runs/<run-id>/jobs/`、`writers/`、`anonymous/`、`reviews/`；`manifest.yml` 先写，`aggregate.data.json`/`aggregate.md` 最后写；
5. 从 `phase1-ab-eval/tools/run-manifest.template.yml` 建立 `manifest.yml`，填 package/prompt/model/input hashes、pair_id 与完整 permutation；
6. 对每个 variant，复制 `writer_bundle` 到内存，严格按 `EXECUTION_CONTRACT.md §4` 应用其 `writer_bundle_patch`：
   - `full`：无 patch；
   - `missing_lemma`：删除 `D3` 并替换为中性 skeleton；
7. 每个 `variant × condition` 建立私有 writer job；本烟测共 4 份：

```text
full × A, full × B, missing_lemma × A, missing_lemma × B
```

8. `manifest.yml` 内保存 A/B 映射；写手 job、匿名稿、judge prompt **不得出现 `condition: A/B`**。

### 4.3 写手阶段（必须 role-locked）

对每一份 job：

- 调 `writer_closed`，不得用通用 delegation；
- A 的用户 prompt = `phase1-ab-eval/prompts/writer-A-baseline.md` 全文 + **patched** `writer_bundle`；
- B 的用户 prompt = `phase1-ab-eval/prompts/writer-B-skill.md` 全文 + **同一份 patched** `writer_bundle`；
- 记录模型路由、max token、variant、重复、提示词版本、输入和原始输出；
- A/B 必须同一模型、同一变体、同一重复、同一闭卷条件；
- 可后台并行，但任何 writer 不得看到其它 writer 输出。

### 4.4 匿名与审稿

1. 为四份 writer output 分配随机 `ANON-###`，Fisher–Yates 顺序和 seed 写进 manifest；
2. `anonymous/ANON-###.md` 只能含：匿名 ID、patched writer bundle、variant 标识/ground truth、匿名 writer output；不得含 A/B、私有 id、prompt 文件名；
3. 每份匿名稿调用 `judge_blind`，用户 prompt = `phase1-ab-eval/prompts/judge-reviewer.md` + 匿名稿 + `judge_bundle`；
4. 每次返回必须是**纯合法 JSON**，至少含：

```text
scores.gap_honesty_H
scores.assumption_dependency_D
scores.reviewability_R
scores.mathematical_correctness_C
step_audit
honesty_assessment
```

5. JSON 不合法、路由不对、含 condition 泄漏 → 不作手工修分，标 `blocked` 或 `review_failed`，保留原始输出。

### 4.5 善后统计

- 四份 JSON 与 pair/anonymity/hash 检查都有效后，父 Harness 运行 `ruby phase1-ab-eval/tools/aggregate_stats.rb --run runs/<run-id> --output runs/<run-id>/aggregate.data.json --bootstrap 10000 --seed <manifest seed>`；
- 只读 `analyst_stats` 才读取 manifest、恢复标签并返回 `aggregateMarkdown`；父 Harness 将该字段逐字写入 `runs/<run-id>/aggregate.md`；
- 若脚本 exit 非零、pair invalid、blocking `judge_unverified` 或匿名泄漏，run 不能继续统计结论；
- 冒烟的汇总结论必须为 `dev_validation_only`，禁止输出初步有效性结论。

### 4.6 冒烟通过条件

全部满足才通过：

- [ ] `writer_closed` 与 `judge_blind` 探针均确认零工具，且 judge probe route=micu/gpt-5.6-sol；
- [ ] 四个 writer job 均使用 flash 且完成；
- [ ] 四个 judge JSON 均来自 micu/gpt-5.6-sol；
- [ ] judge 输入没有 A/B/private id，且 pair 内非 submission judge-input hash 完全一致；
- [ ] manifest 有 pair_id、完整 permutation、route/prompt/bundle/input/output hash；
- [ ] 目录布局完整，manifest 与匿名映射一一对应；
- [ ] `aggregate.data.json` 与 `aggregate.md` 均存在，前者 validation.ok=true，后者只做 dev 方法验证；
- [ ] P001 原始 package、原始 writer output、review JSON 均未被改写；
- [ ] queue 状态更新为 `aggregated`（或出现具体 `blocked` 原因）。

---

## 5. 冒烟后：dev 先导的标准执行

只有 §4 全过，才能开始：

```text
1 个写手模型 × 2 条件 × 5 个高区分度题 × 3 重复 = 30 writer outputs
```

### 5.1 题目来源与筛选

只从以下主池选：

- IMO/IMO Shortlist、USAMO、CMO 等国家级奥赛 P3+、Putnam、Schweitzer/IMC；
- 已发表论文里可自洽的**关键中间引理片段**（原文证明必须获取，作为 judge 锚点）。

禁用 MATH 基础层、AMC、AIME。每题先 baseline 预检：目标写手必须能产出部分有效步骤、但在关键引理处失手；全对或全崩都淘汰。

### 5.2 写手模型 D2（未冻结，真实 pilot 前的必要工作）

当前 `writer_closed` 只为 P001 冒烟锁定 flash。正式 pilot 前：

1. 用 dev 候选题预检 3–5 个候选模型；
2. 依据“中段带”选择 M1/M2/M3；
3. 为每个冻结模型在 preset 中新增独立零工具 writer role row，例如 `writer_m1_closed`；每行必须：
   - `toolFilter.allow: []`；
   - `maxDepth: 1`（DSH 的 `maxDepth` 是绝对深度上限：Harness 派出的子 agent 深度为 1，`0` 会使角色行无法被调用；见 §9）；
   - 显式 `agentOptions.provider/model/maxTokens`；
4. mount-validate preset；新开 session；
5. 把 D2 的模型、理由、route、token budget 写回 `phase1-ab-eval/experiment-design.md` 和 run manifest。

### 5.3 D4（已冻结，真实 eval 前阻塞项）

执行 `phase1-ab-eval/contracts/CALIBRATION_PROTOCOL.md`：3–5 个冻结 dev package × A/B × 2 repetitions，最少 12 个匿名 submission；H/D/R weighted kappa ≥0.60，C ≥0.50，且主指标无 <0.40。运行 `calibration_kappa.rb` 生成 `calibration.data.json`；不通过则禁止自动化 eval。

---

## 6. 正式 eval 的不可违反规则

- 只使用冻结的 `split: eval` packages；不能把 eval 输出拿去修改 B prompt；
- 正式小规模矩阵：`3 writers × 2 conditions × 5 questions × 3 repetitions = 90 outputs`；
- 题目与 package 版本不可变；重跑生成新 run id；
- 分析按**题目聚类** bootstrap 10,000 次；
- 有效性判定严格按 `phase1-ab-eval/experiment-design.md` §1.2：至少两个 H/D/R 改善、单指标平均配对差 ≥0.5/4 且 95% CI 下界 >0、C 护栏不破、至少两个写手方向一致、至少一种目标失败模式下降；
- 任何模型输出都不得标为 `proved`；judge 分数只是实验数据。

---

## 7. 失败处理

| 失败 | 处理 |
|---|---|
| role tool 缺失/工具泄漏 | 停止；检查 preset；修复后 mount-validate；新 run id 重跑 |
| 模型 route 失败 | queue=`blocked`；记录 provider/model 原文错误；不降级 |
| package writer/judge 信息混杂 | package 不可修补；建新版本并重新批准 |
| judge 非 JSON | 原文写 `reviews/`；`review_failed`；不得让 operator 手工转写为分数 |
| 匿名稿泄漏 A/B | 整个 run 无效；新 run id、重新随机化 |
| analyst 修改原始产物 | 停止；保留 git/文件证据；从原始 artefact 重新建立新 run |
| 统计样本不足/CI 无结论 | 报 `not_shown`，不延伸成有效性结论 |

---

## 8. 下一位 operator 的第一句话

在新 preset session 中先说：

> 检查 `phase1-ab-eval/archive/NEXT_ROUND_HANDOFF.md` 与队列；只执行 P001 冒烟测试。先做 writer_closed 零工具探针，探针通过后再 materialize P001；不要调用通用 subagent 或 workflow 处理 writer/judge。

这条交接完成后，下一位 operator 不需要再问“流程怎么跑”，只需按 §4 执行并报告 run id 或具体 blocker。

---

## 9. 2026-08-17 首次动态冒烟：探针发现与修复（v0.3 增补）

首次真实执行时，`writer_closed` 与 `judge_blind` 两个 §4.1 探针都返回
`Error: subagent depth 1 exceeds maxDepth 0`。冒烟按门禁停止，**未 materialize P001**。

- **根因（已对源码验证）**：DSH 的 `maxDepth` 是**绝对深度上限**——子 agent 深度 = 父深度 + 1，必须 ≤ maxDepth（checkout `packages/subagent/subagent/src/child-agent.ts` 的 `resolveChildDepth`；`depth.ts` 视顶层为 0）。Harness 是顶层，因此 `maxDepth: 0` 使角色行**完全无法被调用**；它并不表示“禁止孙级委派”。旧 preset 注释与 v0.2 交接对此语义的解读是错误的；schema 允许 0，所以 mount 校验通过、调用才炸——这正是冒烟存在的意义。
- **修复**：用户 preset `proof-pipeline`（`~/.dsh/.agent-presets/proof-pipeline/agent.cordis.yml`）四个角色行 `maxDepth: 0 → 1` 并更正注释；writer/judge 的零工具与 analyst 的只读 `toolFilter` 本就保证不能再委派。YAML 已校验。
- **关键限制**：角色配置在 session 挂载时固化。修复后同 session 重探仍返回同一错误（已记录），必须**新开 DSH session** 才能生效（§3.1 禁止中途换 preset）。
- **重跑路径**：新 session 中从 §4.1 探针重新开始；P001 保持 `ready`、`claim: null`，无需新建 package，重跑用新 run id。
- **次要发现（不阻塞 P001）**：`role-terra-curator` 未设 `toolFilter`，会继承通用 `subagent` 工具、理论上可再委派一层；P001 冒烟不使用 Terra，待 Terra 真正启用时按需补 deny 过滤。
- **完整证据**：`phase1-ab-eval/archive/P001-SMOKE-BLOCKER.md`（含时间线、错误原文、源码行号、未执行事项清单）。

## 9.1 第二次动态发现（v0.3 增补，同日）

maxDepth 修复并重启后，`RUN-20260817-001-smoke` 在**写手阶段**被阻：

- 4 份 `writer_closed` job 中 3 份以 `max-tokens` 失败：deepseek-v4-flash 的 **reasoning tokens 计入 maxTokens**，pinned `maxTokens: 16384` 在隐藏推理中被烧尽（3 份最终文本为空或被截断，唯一完成的一份 reasoning≈12.6K、总≈13.7K 擦线过线）。
- 处理：run/queue 均转 `blocked` 并记录原因；原始产物（完整/截断文本 + `.FAILED.md` 证据）保留在 `runs/RUN-20260817-001-smoke/writers/`；未进入匿名与评审。
- 修复：preset `role-writer-closed` `maxTokens: 16384 → 65536`，需重启 dsh web + 新 session（同 §9 的挂载限制）。
- 重跑：新 run id（`RUN-20260817-002-smoke`），queue blocked → 新 claim；旧 run 不修补。
- 教训写入 §4.3 补充：**写手（及未来 D2 模型）角色行 maxTokens 必须覆盖 reasoning 消耗**，正式冻结时需先用 dev 候选预检单份 job 的 usage 再定预算。judge 行 16384 暂为观察项（重跑评审阶段若同类截断，按同法修复）。
- 证据：`phase1-ab-eval/archive/P001-SMOKE-BLOCKER.md` §9。
