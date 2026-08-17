# Stage-1 样题包（1.2 产物）

- 日期：2026-08-18
- 状态：`candidate`（未入队、未经阶段 2 预测试定档；只用于验证 v2 出题模板）
- schema：`prompt-terra-problem-curator.md` v2（`proof_spine + completion_test + allowed_dependencies + 六态 claim + 写作纪律`）

## 三题一览

| 包 | 定理 | 领域 | 证明结构 | 先验独立可解度 | 备注 |
|---|---|---|---|---|---|
| `S01-egz.yml` | Erdős–Ginzburg–Ziv（2n−1 个整数中有 n 个和为 n 的倍数） | 组合数论 | key_lemma | low | 素数情形编码构造 + 合成情形提取计数 |
| `S02-finite-division-ring.yml` | 有限除环必是域 | 抽象代数 | contradiction | low | 类方程 + 分圆多项式整除链 |
| `S03-fisher-inequality.yml` | 2-设计中 b ≥ v | 组合设计 | construction | medium | 关联矩阵秩论证；记忆风险最高，预测试不过即淘汰 |

## 窄缝验收协议（STAGE-1 完成标志的一部分）

对每题依次做两个探针（阶段 2 能力预测试的预演）：

1. **裸题探针**：只给 `writer_bundle.statement`，问模型"证明它" → 预期：补不出完整证明（错/跳/放弃）；
2. **带包探针**：给完整 `writer_bundle` → 预期：能补出可核验的完整证明（judge C ≥ 3）。

两条都满足 → `narrow_slot_calibration.measured = confirmed`；只满足 ① → 降级为探针；只满足 ②（裸题也会）→ 淘汰为秒杀题。

- 探针必须在 **proof-pipeline preset 会话**中用零工具 `writer_closed` 角色行执行才算正式；本仓库不把通用 subagent 的输出当作正式预测试数据。
- 截止 2026-08-18：三题 `measured` 均为 `null`，待预测试。

## 诚实标注

- 三道题 `original_text_obtained: false`：参考证明为按标准教材重建（重建内容已在本包内全文给出）。
  **入正式池前必须获取原文并改为 `true`**（EXECUTION_CONTRACT §3.2 的硬门）。
- 旧 schema（`pipeline/problem-package.template.yml`）与 `validate_package.rb` 尚未覆盖 v2 字段；
  本目录样题不进入队列，待阶段 3 基础设施同步后再接 validator。
