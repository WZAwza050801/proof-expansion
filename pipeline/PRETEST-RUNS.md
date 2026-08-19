# 预测试/运行产物落盘协议（后台运行约定）

- 日期：2026-08-18
- 目的：**测试与中间记录不进 DeepSeek 会话对话框**——探针输出、Terra 蒸馏草稿、临时评分等一律落盘；会话里只保留状态行与结论。
- 适用：所有预演探针、正式预测试、Terra 出题、judge 复核、chunked 流水线的块输出等非对话产物。

## 规则

1. **落盘位置**：`runs/pretest/`（已被 `.gitignore` 排除，本地归档、不进版本控制）。
   - 单条探针：`runs/pretest/<题包>_<模型>_<探针类型>.md`（例：`S10_deepseek-v4-flash_bare.md`）；
   - Terra 蒸馏草稿：`runs/pretest/terra_<日期>_<slug>.md`；
   - 临时评分/拼接产物：`runs/pretest/…` 或 `runs/<run-id>/`（正式 run 走原布局）。
2. **agent 输出即写文件**：派发探针/Terra/judge 时，在提示词里要求"把完整输出写入指定文件，最后只回复一行：`saved=<路径> status=<ok|fail> summary=<一句话>`"。
3. **后台执行**：批量探针用后台 job / workflow；等待结果用 `job_output`（只看尾部状态行），不整段回显。
4. **只把"结论"落进 git**：定档结论、窄缝判定、失败模式等汇总进 `problems/stage1-samples/SELFTEST.md`（git 跟踪）；原始输出永远留在 `runs/`。
5. **会话消息格式**：状态行（谁跑了、几个、存到哪、结论一句话）；不粘贴长文本。

## 触发示例

```text
派发 6 份裸题探针 → 每份要求写入 runs/pretest/S10_*.md 并只回状态行
→ 后台并行 → 汇总 SELFTEST.md 结论 → commit
```
