# Judge–Human Calibration Protocol

- 版本：`v0.2`
- 状态：D4 已具体化；必须在正式 eval 前完成。
- > ⚠️ **v2 过渡标注（2026-08-18）**：本协议维度（H/D/R/C）为 v1 旧口径。v2 口径 = C/G/R/L（G/R/L ≥0.60，C ≥0.50，主指标无 <0.40），见 `phase1-ab-eval/experiment-design.md` §7.2 与 `phase1-ab-eval/rubric-samples/`（首批可读性锚点）。协议正文与 `calibration_kappa.rb` 已于**阶段 3（2026-08-18）**同步到 C/G/R/L；L 允许 0.5 步进，`calibration_kappa.rb` 统一折半记分（0..8）后算加权 kappa。

## 1. 目标

验证 `micu/gpt-5.6-sol` 的 C/G/R/L 评分与人工评分具有足够一致性。校准不证明提示词有效；它只决定 judge 是否可以批量评分。

## 2. 校准样本

- 使用 3–5 个冻结 `dev` packages；
- 每 package 运行 A/B 各 2 次，最少 12、最多 20 个匿名 submission；
- 人工评分者与 judge 都使用同一 0–4 rubric；
- 校准样本不得用于随后 B prompt 的调优，也不得进入 eval 结论。

## 3. 数据文件

复制 `phase1-ab-eval/tools/calibration-ratings.template.csv` 到：

```text
runs/CAL-<id>/human-judge-ratings.csv
```

一行代表一个匿名 submission × 一个指标。字段：`unit_id,metric,human_score,judge_score,package_id,run_id,notes`。

## 4. 通过门（冻结）

运行：

```bash
ruby phase1-ab-eval/tools/calibration_kappa.rb \
  --input runs/CAL-<id>/human-judge-ratings.csv \
  --output runs/CAL-<id>/calibration.data.json \
  --min-units 12 --main-threshold 0.60 --c-threshold 0.50
```

使用线性权重 Cohen's kappa（评分 0–4）。通过当且仅当：

- H、D、R 各有 >=12 个完整单位且 weighted kappa >= 0.60；
- C 有 >=12 个完整单位且 weighted kappa >= 0.50；
- 任一主指标没有 kappa < 0.40；
- CSV 无重复 unit/metric、无超范围分数、无缺失对。

任何失败 → `judge_calibration=failed`，禁止启动自动化 eval；只允许修 rubric/judge prompt 或扩大独立校准样本，然后创建新的 calibration run。

## 5. 记录

将 `calibration.data.json`、CSV、人工评分说明和 judge 原始 JSON 一同保存。把通过结果写入 `phase1-ab-eval/experiment-design.md` 的 D4 行，包含 calibration run id 和 kappa 值。