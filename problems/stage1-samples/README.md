# Stage-1 样题包（1.2 产物）

- 日期：2026-08-18
- 状态：`candidate`（未入队；自测已跑——**五题全部定档 `excluded_instant_solve`（秒杀），不进区分度池**；详见 `SELFTEST.md`）
- schema：`prompt-terra-problem-curator.md` v2（`proof_spine + completion_test + allowed_dependencies + 六态 claim + 写作纪律`）

## 五题一览

| 包 | 定理 | 领域 | 证明结构 | 先验独立可解度 | 实测（预演，pro/flash） |
|---|---|---|---|---|---|
| `S01-egz.yml` | Erdős–Ginzburg–Ziv | 组合数论 | key_lemma | low | 秒杀 / 秒杀 |
| `S02-finite-division-ring.yml` | 有限除环必是域 | 抽象代数 | contradiction | low | 秒杀 / 秒杀 |
| `S03-fisher-inequality.yml` | 2-设计中 b ≥ v | 组合设计 | construction | medium | 秒杀 / 秒杀 |
| `S04-frankl-wilson.yml` | Frankl–Wilson 多项式方法（求和界形式） | 极值组合 | construction | low | 秒杀 / 秒杀 |
| `S05-stone-weierstrass.yml` | Stone–Weierstrass（实值格版本） | 泛函分析 | construction | medium | 秒杀 / 秒杀 |

- 五题均作**秒杀题对照样题**保留（冒烟/校准/对比用），`measured: excluded_instant_solve` 已写入各包。
- 带包探针 10/10 完整闭合——v2 题包格式本身验证通过；未验证的是"窄缝题源"。

## 窄缝验收协议（STAGE-1 完成标志的一部分）

对每题依次做两个探针（阶段 2 能力预测试的预演）：

1. **裸题探针**：只给 `writer_bundle.statement`，问模型"证明它" → 预期：补不出完整证明（错/跳/放弃）；
2. **带包探针**：给完整 `writer_bundle` → 预期：能补出可核验的完整证明（judge C ≥ 3）。

两条都满足 → `narrow_slot_calibration.measured = confirmed`；只满足 ① → 降级为探针；只满足 ②（裸题也会）→ 淘汰为秒杀题。

- 探针必须在 **proof-pipeline preset 会话**中用零工具 `writer_closed` 角色行执行才算正式；本仓库不把通用 subagent 的输出当作正式预测试数据（本批为预演，结果已标注）。
- 2026-08-18 实测结论：五题对 v4-pro 与 v4-flash 全部秒杀 → 1.2 的"样题落窄缝"验收未达成；下一步见 `SELFTEST.md` 结论第 4 条（研究级片段题源 / 阶段 2 正式预测试 / 骨架细度旋钮）。

## 诚实标注

- 五道题 `original_text_obtained: false`：参考证明为按标准教材重建（重建内容已在本包内全文给出）。
  **入正式池前必须获取原文并改为 `true`**（EXECUTION_CONTRACT §3.2 的硬门）。
- 旧 schema（`pipeline/problem-package.template.yml`）与 `validate_package.rb` 尚未覆盖 v2 字段；
  本目录样题不进入队列，待阶段 3 基础设施同步后再接 validator。
