# Stage-1 样题包（1.2 产物）

- 日期：2026-08-18
- 状态：`candidate`（未入队；自测已跑——**S02/S04/S05 对 Qwen3.6-27B 定档 `confirmed`（窄缝），S01 降为探针，S03 全模型秒杀**；详见 `SELFTEST.md`）
- schema：`prompt-terra-problem-curator.md` v2（`proof_spine + completion_test + allowed_dependencies + 六态 claim + 写作纪律`）

## 五题一览

| 包 | 定理 | 领域 | 证明结构 | 先验独立可解度 | 实测（预演，pro/flash） |
|---|---|---|---|---|---|
| `S01-egz.yml` | Erdős–Ginzburg–Ziv | 组合数论 | key_lemma | low | 秒杀 / 秒杀 |
| `S02-finite-division-ring.yml` | 有限除环必是域 | 抽象代数 | contradiction | low | 秒杀 / 秒杀 |
| `S03-fisher-inequality.yml` | 2-设计中 b ≥ v | 组合设计 | construction | medium | 秒杀 / 秒杀 |
| `S04-frankl-wilson.yml` | Frankl–Wilson 多项式方法（求和界形式） | 极值组合 | construction | low | 秒杀 / 秒杀 |
| `S05-stone-weierstrass.yml` | Stone–Weierstrass（实值格版本） | 泛函分析 | construction | medium | 秒杀 / 秒杀 |
| `S06-putnam2019b6-lattice.yml` | Putnam 2019 B6 格点完美支配集 | 数论/组合 | construction | low | 秒杀（flash/pro/27B） |
| `S07-putnam2022a5-tiling.yml` | Putnam 2022 A5 铺砖博弈 | 组合博弈 | induction | low | **窄缝确认（flash）**；pro 秒杀 |
| `S08-putnam2023b6-determinant.yml` | Putnam 2023 B6 行列式 | 数论/线代 | construction | low | 秒杀（flash/pro）；27B 待复核 |
| `S09-seidel-stage1-audit.yml` | Seidel 猜想 Stage-I 审计（**前沿探针题**） | 辛拓扑/范畴 | key_lemma | — | probe_only：charter 模板演示，测上限不进区分度 |
| `S10-bohr-multidilate.yml` | Kościuszko 多系数 Bohr 膨胀密度增量二分引理 | 加法组合 | direct | medium | **论文蒸馏**：EJC 2025 Lemma 10；窄缝确认（flash/pro/27B）；"秩 d"陈述待人工对照原文 |
| `S11-pcap-monotonicity.yml` | p-容度势水平集单调性公式 | 几何分析 | direct | low | **论文蒸馏**：arXiv:2205.11642 Thm 1.1；窄缝确认（flash/pro 完整闭合六步） |

- 定档（预演级，2026-08-18）：S02/S04/S05 = `confirmed`（写手 Qwen/Qwen3.6-27B）；**S07 = `confirmed`（写手 deepseek-v4-flash，benchmark 难题档）**；S01 = `downgraded_to_probe`；S03/S06/S08 = `excluded_instant_solve`。窄缝是 model-relative 的。
- 带包探针全部闭合——v2 题包格式验证通过。

## 窄缝验收协议（STAGE-1 完成标志的一部分）

对每题依次做两个探针（阶段 2 能力预测试的预演）：

1. **裸题探针**：只给 `writer_bundle.statement`，问模型"证明它" → 预期：补不出完整证明（错/跳/放弃）；
2. **带包探针**：给完整 `writer_bundle` → 预期：能补出可核验的完整证明（judge C ≥ 3）。

两条都满足 → `narrow_slot_calibration.measured = confirmed`；只满足 ① → 降级为探针；只满足 ②（裸题也会）→ 淘汰为秒杀题。

- 探针必须在 **proof-pipeline preset 会话**中用零工具 `writer_closed` 角色行执行才算正式；本仓库不把通用 subagent 的输出当作正式预测试数据（本批为预演，结果已标注）。
- 2026-08-18 实测结论：S02/S04 对 Qwen3.6-27B 窄缝确认（裸题失败 ∧ 带包完整闭合）→ **1.2 的"样题落窄缝"验收达成（预演级）**；强模型侧需研究级片段题源，是阶段 2 的工作。

## 诚实标注

- 经典定理五题（S01–S05）`original_text_obtained: false`：参考证明为按标准教材重建（重建内容已在本包内全文给出）；
  Putnam 三题（S06–S08）与论文蒸馏两题（S10–S11）`original_text_obtained: true`（S06–S08 来自 Putnam-AXIOM 数据集官方解答，S10–S11 由 Terra 预演核对 arXiv 原文）。
  **入正式池前必须获取原文并人工复核数学内容**（EXECUTION_CONTRACT §3.2 的硬门；S10–S11 的数学内容尚未经人工复核，属 Terra 预演产出）。
- 旧 schema（`pipeline/problem-package.template.yml`）与 `validate_package.rb` 尚未覆盖 v2 字段；
  本目录样题不进入队列，待阶段 3 基础设施同步后再接 validator。
