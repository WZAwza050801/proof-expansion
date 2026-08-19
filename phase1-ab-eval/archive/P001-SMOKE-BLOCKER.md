# P001 冒烟 Blocker 记录

- 日期：2026-08-17
- 结论：**冒烟未开始**。§4.1 能力探针门未通过，按协议停止，未 materialize、未 claim。
- 队列状态：`P001-smoke-harmonic-v1` 保持 `status: ready`、`claim: null`（题目包本身无缺陷，不标 blocked）。
- 协议依据：`NEXT_ROUND_HANDOFF.md` §4.1（探针门）+ §7 第一行（role tool 问题 → 停止；检查 preset；修复后 mount-validate；新 run id 重跑）。

## 1. 症状

2026-08-17，本 session（preset `proof-pipeline`）对 `writer_closed` 与 `judge_blind`
分别派发零题目能力探针（前台），两者均立即返回：

```text
Error: subagent depth 1 exceeds maxDepth 0
```

未产生任何子 agent 输出。探针 prompt 只要求子 agent 报告可用工具/搜索能力/route，
不含任何题目内容。

## 2. 根因（对 DSH 源码验证，非猜测）

- `packages/subagent/subagent/src/child-agent.ts` → `resolveChildDepth(parent, maxDepth)`：
  `childDepth = delegationDepthOf(parent) + 1`，若 `childDepth > maxDepth` 抛
  `SubagentDepthError("subagent depth <attempted> exceeds maxDepth <max>")`。
- `packages/subagent/subagent/src/depth.ts`：顶层 agent 深度为 0。
- `tool-subagent/README.zh.md`：`maxDepth` = **绝对委派深度上限**，默认 3，**0 禁止委派**（即禁止这次派发本身）。
- preset `proof-pipeline`（`~/.dsh/.agent-presets/proof-pipeline/agent.cordis.yml`）四个角色行
  （terra/writer/judge/analyst）均写 `maxDepth: 0`，且注释声称
  “maxDepth: 0 forbids the child from delegating further”——该理解与 DSH 实际语义相反。
- mount 校验通过的原因：`0` 是 schema 合法的非负整数；缺陷只在**调用时**爆发。
  静态审查（handoff v0.2 §1）无法发现，正是冒烟测试要覆盖的动态缺陷。

结论：Harness（depth 0）派出的任何角色子 agent（depth 1）都必然超过上限 0，
所以四个角色行在本部署中**完全不可调用**。

## 3. 已应用的修复

文件：`~/.dsh/.agent-presets/proof-pipeline/agent.cordis.yml`

- 四个角色行 `maxDepth: 0` → `maxDepth: 1`（terra_curator / writer_closed / judge_blind / analyst_stats）。
- 更正 delegation 组注释：说明 `maxDepth` 为绝对深度上限、Harness 子 agent 深度为 1、
  `0` 会禁止调用；零工具行与只读行的再委派限制由 `toolFilter` 保证。
- 修复后语义：Harness → 角色（depth 1 ≤ 1）允许；角色 → 孙 agent（depth 2 > 1）拒绝。
  writer/judge 本就零工具（`toolFilter.allow: []`），analyst 仅 read/glob/grep，均无法再委派。
- 校验：`ruby -ryaml` 解析通过，逐行确认四个角色行 `maxDepth=1`。

## 4. 修复不立即生效的证据

- 修复文件后，同 session 重探 `writer_closed`，返回完全相同的
  `Error: subagent depth 1 exceeds maxDepth 0`。
- 原因：preset 按进程挂载一次（"mounted once per process"），角色工具配置在
  session 挂载时固化；`NEXT_ROUND_HANDOFF.md` §3.1 亦禁止中途切换 preset。
- 因此：**必须新开 DSH session（选择 preset `proof-pipeline`）重跑**，本 session 不再重试。

## 5. 本 session 明确未做的事（防止误解）

- 未 materialize P001；未创建 run id / manifest / runs/ 目录；未 claim 队列项；`queue.yml` 未改动。
- 未用通用 `subagent` / `subagent_fork` / `workflow` 派任何 writer/judge（遵守用户指令与 handoff §1）。
- 未触碰任何 prompt 文件、题目包、writer bundle、judge bundle。
- 未把本次失败标记为 P001 的 `blocked`——缺陷在 preset 配置，不在题目包。

## 6. 下一位 operator 的重跑步骤

1. 新开 DSH session，选择 preset `proof-pipeline`（先确认角色工具四个都在）。
2. 重跑 §4.1 探针：
   - `writer_closed`：应报告无任何工具、不能搜索。
   - `judge_blind`：同上，且 route 报告应为 `micu/gpt-5.6-sol`。
3. 任一探针仍失败 → 写新的 blocker 记录，**不要 materialize**。
4. 探针通过 → 按 §4.2–§4.6 完整执行 P001（新 run id；队列仍 ready/claim:null）。

## 7. 次要发现（不阻塞 P001，记录备查）

- `role-terra-curator` 无 `toolFilter`，会继承通用 `subagent` 工具，理论上可再委派一层；
  handoff v0.2 声称 Terra "cannot delegate" 并不成立。P001 冒烟不使用 Terra，待启用时补 deny 过滤。
- `NEXT_ROUND_HANDOFF.md` §5.2 原要求未来 writer 模型角色 `maxDepth: 0`，会复现本缺陷；
  已在 v0.3 中更正为 `maxDepth: 1`。

## 8. 进程重启执行记录（2026-08-17 13:55）

用户授权后，operator 安排了一次托管重启以让 preset 修复生效（preset 每进程挂载一次，
无热重载端点；服务器 = PID 29113 `node .../pnpm dsh web`，cwd=deepseek-harness checkout，
2026-08-16 14:19 启动，早于修复）。

- 脚本：`/tmp/dsh-web-restart.sh`（脱离进程树，PID 41132；90 秒延迟 → 校验 preset 修复
  `maxDepth: 1` 计数 ≥4 → 杀 3080 监听进程及其 pnpm 父进程 → 在 checkout 原样
  `nohup pnpm dsh web` 重启 → 轮询 `http://127.0.0.1:3080/` 直到返回非 000）。
- 日志：`/tmp/dsh-web-restart-<ts>.log`（主）、`/tmp/dsh-web-restart-server.log`（新服务器 stdout/stderr）。
- 重启后本 session 从存储恢复；下一步 operator 先重跑 §4.1 探针，通过后再 materialize P001（新 run id）。

## 9. 第二次动态发现：writer maxTokens 截断（RUN-20260817-001-smoke，2026-08-17 14:07 CST）

重启后探针通过、RUN-20260817-001-smoke 完成 materialize 并派发 4 份 writer job。结果：

| job | finish | inputTokens | outputTokens | reasoningTokens | 最终文本 |
|---|---|---|---|---|---|
| full-A | max-tokens | 2732 | 16384 | 16125 | 404 字符（被截断） |
| full-B | max-tokens | 3256 | 16384 | 16384 | 0（空） |
| missing_lemma-A | stop | 2607 | 13763 | 12673 | 完整 ✓ |
| missing_lemma-B | max-tokens | 3131 | 16383 | 16383 | 0（空） |

- **根因**：deepseek-v4-flash 是推理模型，**reasoning tokens 计入 maxTokens**；preset 写手行
  pinned `maxTokens: 16384`，三个 job 在隐藏推理中烧完预算、以 max-tokens 停止且没有最终答案。
  唯一完成的 job 用 12.6K reasoning + 1.1K 文本 ≈ 13.7K，擦线上限过线。子 session 的
  `request/header` 与 usage 事件为证（child session ids 见 manifest）。
- **协议处理**：冒烟通过条件"四个 writer job 均完成"不满足 → run 转 `blocked`；
  原始产物全部保留：`writers/P001-missing_lemma-r01-A.md`（完整输出）、
  `writers/P001-full-r01-A.md`（截断文本，404 字符）+ 三份 `.FAILED.md`（finish reason/usage/session id）。
  未派发任何 judge；未做匿名化；manifest 状态与 queue 状态均已记录。
- **修复**：preset `role-writer-closed` `maxTokens: 16384 → 65536`（模型/零工具/maxDepth 不变）。
  与 maxDepth 修复一样需**重启 dsh web 进程 + 新 session** 才生效（脚本同 §8）。
- **重跑**：新 session 后新 run id（`RUN-20260817-002-smoke`）；queue 从 blocked → 新 claim；
  旧 run 全部保留，不修补。
- **观察项**：judge 行 `maxTokens: 16384` 未动（无证据）。若 gpt-5.6-sol 同样把推理计入预算，
  评审阶段可能遇到同类截断；重跑中若发生，按同法修复。

## 10. 探针异常：writer 自报工具清单（幻觉，非能力泄漏）（2026-08-17 14:45 CST）

第二次重启后为 RUN-002 重跑探针，`writer_closed` 自报：

```text
可见/可用的工具：bash、edit、glob、goal、grep、job、ralph、read、web_search、workflow、write；能搜索。
```

`judge_blind` 同时段正常（"无任何工具 / 不能 / 不可见"）。调查结论：

- **子 agent system prompt 取证**：写手探针 session `57f32a24`（与 judge 探针 `2ef49c01`）
  的 system prompt 仅 5.5KB，**不含任何工具定义/函数 schema**；其中的 `web_search`/`ralph`/`workflow`
  只是部署 persona 的**散文提及**（"Use the web_search tool..."类指导语）。role persona
  （"You are a closed-book proof writer… You have no tools…"）也在其中。
- **决定性执行测试**（session `e186efd6`）：要求子 agent 实际调用 `read` 读 `/etc/hosts`。
  子 agent 在**最终文本里模仿**了 `<tool_calls>` 语法，但 session 内 `tool/call` 事件 = 0，
  没有任何工具执行、工具结果或文件内容回传。→ **无任何可执行能力**。
- **定性**：deepseek-v4-flash（弱模型，正是冒烟写手）把 persona 散文中的工具名
  幻觉成自己的工具清单，并会模仿调用语法。这不是 role filter 泄漏；`toolFilter.allow: []` 完好
  （无授权、无执行、mount-validated 配置为硬依据，EXEC §8）。
- **处理**：异常与三份探针记录全部写入 RUN-002 的 `manifest.yml.capability_evidence`；
  冒烟以硬证据（配置 + 0 工具事件 + 拒绝执行）继续。教训：探针自报不可靠，必须辅以
  "要求实际调用工具 + 检查子 session tool/call 事件"的确定性测试。
