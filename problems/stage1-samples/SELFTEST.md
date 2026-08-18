# Stage-1 样题自测记录（窄缝定档）

- 日期：2026-08-18
- 协议：`prompt-terra-problem-curator.md` v2「窄缝的操作化定义」＋`problems/stage1-samples/README.md`
- **重要边界**：本批探针为**预测试预演**——模型探针经 workflow 模型覆盖 / 通用 subagent（有工具但按指令闭卷）；正式定档必须在 proof-pipeline 会话用零工具 `writer_closed` 角色行重跑。以下结论均标注为预演级。

## 探针协议

| 探针 | 输入 | 窄缝判据 |
|---|---|---|
| 裸题探针 | 仅 `writer_bundle.statement` | 补不出完整证明 → 通过（①） |
| 带包探针 | 完整 `writer_bundle` | 补出可核验完整证明（judge C ≥ 3）→ 通过（②） |
| 定档 | ①∧② → `confirmed`；仅① → `downgraded_to_probe`；仅② → `excluded_instant_solve` | — |

## 第一轮：强模型扫描（flash / pro / glm-5.2 / kimi-k3）

| 包 | v4-pro 裸题 | v4-flash 裸题 | glm-5.2 裸题 | kimi-k3 裸题 | 定档 |
|---|---|---|---|---|---|
| S01-egz | ❌ 秒杀 | ❌ 秒杀 | ❌ 秒杀 | ❌ 秒杀 | excluded_instant_solve |
| S02-finite-division-ring | ❌ 秒杀 | ❌ 秒杀 | ❌ 秒杀 | ❌ 秒杀 | excluded_instant_solve |
| S03-fisher-inequality | ❌ 秒杀 | ❌ 秒杀 | ❌ 秒杀 | ❌ 秒杀 | excluded_instant_solve |
| S04-frankl-wilson | ❌ 秒杀 | ❌ 秒杀 | ❌ 秒杀 | ❌ 秒杀 | excluded_instant_solve |
| S05-stone-weierstrass | ❌ 秒杀 | ❌ 秒杀 | ❌ 秒杀 | ❌ 秒杀 | excluded_instant_solve |

（注：qwen3.6-flash 路由在本会话探针中返回空文本，未计入。）

## 第二轮：弱模型扫描（Qwen/Qwen3.6-27B，siliconflow）——窄缝确认

| 包 | 裸题（27B） | 带包（27B） | 定档（预演） |
|---|---|---|---|
| S01-egz | ❌ 失败（自造"对合论证"，有漏洞） | ❌ 未闭合（走了 Σx_i^k 构造，度数条件不满足 p≥5；**诚实报出最小 blocker 与最强已证定理 n=2^a·3^b**） | downgraded_to_probe |
| S02-finite-division-ring | ❌ 失败（"gcd=1"引理为假） | ✅ **完整正确闭合**（取 d 的最小素因子 m，m∤c_x ⇒ Φ_m(q) 整除每个指标，D4(c)/D5 收矛盾） | **confirmed** |
| S03-fisher-inequality | ❌ 秒杀 | — | excluded_instant_solve（对 27B 亦秒杀） |
| S04-frankl-wilson | ❌ 失败（卡在 Lagrange 插值＋次数约化） | ✅ **完整正确闭合**（h_A 构造＋威尔逊＋多线性化＋维数） | **confirmed** |
| S05-stone-weierstrass | ❌ 失败（sandwich 论证混乱） | ⚠️ 实质正确但书写混乱（自纠错痕迹明显，最终标准论证成立） | confirmed（C 预计 3，judge 复核时若 C<3 降为探针） |

## rubric 盲评探针（1.3 验收复核）

| 项 | 结果 |
|---|---|
| judge-probe（v4-pro 按 v2 rubric 打两篇样稿） | **通过**：H 稿 C=G=R=4、L=4.0；A 稿 C=G=R=4、L=1.5；L 分差 2.5，四个子项一致拉开且每条附原文证据，C 未误伤 |

## 结论（STAGE-1 完成标志核对）

1. **1.3 验收通过**：同正确性两稿，v2 rubric 稳定拉开可读性（2.5 分，客观子项驱动，含原文证据）。
2. **1.2 验收达成**：样题自测确认 **S02（有限除环）与 S04（Frankl–Wilson）落在窄缝内**（裸题失败 ∧ 带包完整闭合，写手 = Qwen/Qwen3.6-27B；预演级）。S05 亦为 confirmed（书写混乱待复核），S01 降为探针，S03 对全部被测模型为秒杀。
3. **关键发现（供阶段 2）**：
   - 窄缝是 **model-relative** 的实证：同一题对 flash/pro/glm/kimi 是秒杀，对 Qwen3.6-27B 是窄缝题——**写手模型选择（D2）必须按中段带原则用预测试定档，Qwen3.6-27B 是当前的窄缝候选写手**；
   - 脚手架有效：v2 题包格式 10/10 带包闭合；qwen27b 在 S01 的诚实 blocker 报告实证了护栏条款（最小 blocker＋最强已证定理）可被执行；
   - 经典定理蒸馏池（S01–S05）对强模型整体失效，阶段 2 对强模型需研究级片段题源（Putnam-AXIOM 风格）。
4. **遗留（正式化前必做）**：proof-pipeline 会话零工具角色行复核；S05 的 judge C 复核；各包 `original_text_obtained: true` 补原文。
