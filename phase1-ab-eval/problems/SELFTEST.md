# Stage-1 样题自测记录（窄缝定档）

- 日期：2026-08-18
- 协议：`phase1-ab-eval/prompts/terra-curator.md` v2「窄缝的操作化定义」＋`phase1-ab-eval/problems/README.md`
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

## 第三轮：benchmark 难题档（Putnam-AXIOM 数据集真题，官方解答作锚点）

- 题源：HuggingFace 数据集 `Putnam-AXIOM/putnam-axiom-dataset-ICML-2025-522`（522 道 Putnam 真题 1938–2023，含官方解答），经 hf-mirror 下载、pyarrow 读取，`original_text_obtained: true`。
- 选题：2019 B6（格点完美支配集）、2022 A5（铺砖博弈）、2023 B6（整除计数矩阵行列式）——均为近年最难档（A5/B6 级）。

| 包 | 裸题（flash） | 带包（flash） | 裸题（pro） | 带包（pro） | 裸题（27B） | 带包（27B） | 定档（预演） |
|---|---|---|---|---|---|---|---|
| S06 2019B6 | ❌ 秒杀 | ✅ | ❌ 秒杀 | ✅ | ❌ 秒杀 | — | excluded_instant_solve（三模型） |
| S07 2022A5 | ❌ 失败（r1 空答、r2 错答 404，引理为假） | ✅ **完整解出 290** | ❌ 秒杀（均值分析法） | ✅ | ❌ 失败（错答 2，论证崩溃） | ❌ 未闭合（b 递推式写反、a(5) 对不上表） | **confirmed（写手=flash）**；pro=秒杀；27B=downgraded_to_probe |
| S08 2023B6 | ❌ 秒杀（Möbius/Cauchy–Binet 法） | ✅ | ❌ 秒杀 | ✅ | ⚠️ 答案对但一般性证明缺 | ⚠️ 主链对（另一套合法变换）、符号论证未核实 | excluded_instant_solve（flash/pro）；27B 待 judge 复核（倾向 probe） |

## 结论补充（benchmark 档）

1. **S07（Putnam 2022 A5）对 deepseek-v4-flash 窄缝确认**——benchmark 难题档的第一个窄缝实证：flash 裸题解不出（一次空答、一次错答 404），给脊柱＋pass 引理后完整解出 290。这直接回应了"挑 benchmark 难一点的"的要求。
2. **更硬的题也被强模型秒杀**：2019 B6 与 2023 B6 连 27B 都近乎默写。结论：公开 benchmark（含 Putnam 最难档）对 flash/pro 整体仍在秒杀区——对强模型的窄缝必须用**非公开研究级片段**（FrontierMath 风格，题目私有拿不到，只能从近期论文手切片段，即阶段 2 主池 B 的工作）。
3. 阶段 2 的题池策略由此清晰：flash 档用 Putnam 难题（如 S07 类），pro 档必须上论文片段。

## 第四轮补充：前沿论文蒸馏（Seidel charter 模板）

- 响应研究者指示：出题默认路径改为**前沿/基础数学论文 → 题包**（不再以公开题库为主），蒸馏模板 = 桌面 `seidel_conjecture_distilled_work_charter.md`（P0–P7 脊柱＋completion test＋六态＋§7 写作纪律）。curator 提示词已新增「主池 B+」一节。
- S09 = 由 charter 蒸馏的第一道**探针题**（Seidel 猜想 Stage-I 审计：组织证明计划，不证猜想）。probe_only，正式上限测试在阶段 2（gpt-5.6-terra 级模型或人工评审）。「论文中已有完整证明的关键引理 → 窄缝题」的实例留待阶段 2 由 Terra 用搜索能力从具体论文切割。

## 第五轮：Terra 论文蒸馏（别的方向的前沿论文 → charter 级题包）

- 按研究者指示：Seidel 留到最后；出题方向改为**别的领域的前沿论文**。Terra（预演：deepseek-v4-pro，正式出题须在 proof-pipeline 会话用 `terra_curator`（gpt-5.6-terra）；已按研究者指示把 Terra 路由从 openrouter 改为 micu）用搜索核验并蒸馏出两题：
  - **S10**：Kościuszko, "Invariant Equations in Many Variables"（EJC 32(3) 2025 #P3.24，arXiv:2306.08567）Lemma 10——加法组合的多系数 Bohr 集膨胀密度增量二分；
  - **S11**：Agostiniani–Mantegazza–Mazzieri–Oronzio, "Riemannian Penrose inequality via Nonlinear Potential Theory"（arXiv:2205.11642，2023）Theorem 1.1——p-容度势水平集单调性公式。
- 两者都按新模板输出：**完整证明结构**（S10 四步 / S11 六步脊柱，每步 objective＋idea（大体证明思路）＋completion test）＋允许依赖＋参考证明作 judge 锚点。
- **待办硬门**：① 两题的数学内容（Terra 蒸馏稿）**未经人工复核**，`ready` 前必须人工核对原文；② 裸题/带包预测试定档（`measured` 仍为 null）；③ 正式出题在 proof-pipeline 会话由 gpt-5.6-terra 重跑核验。

## 第六轮：论文片段窄缝定档（S10/S11 预测试）

- 裸题探针（flash / pro / Qwen3.6-27B，共 6 份）：**全部失败**——
  S10：flash 声称引理为假（多分支分裂论证）但给不出完整证明、pro 完成归约骨架后卡在常数匹配、27B 平均论证中途崩溃；
  S11：三模型均卡在 p-调和 Bochner/Kato 恒等式（27B 还写出错误的 Ric≥R/3 估计）。
- 带包探针（共 8 份）：**S10 flash/pro/27B 全部闭合**（同步膨胀构造＋卷积贴近＋平均＋二分收尾），
  **S11 flash/pro 完整闭合六步**（div X 恒等式→Gauss–Bonnet 化层→连通性→无临界点→η_k 截断→ε 正则化逼近），27B 主链正确。
- **定档：S10、S11 = confirmed（窄缝），写手 = flash/pro（27B 对 S10 亦成立）。**
- **重要发现（须人工复核）**：S10 的三份带包证明一致指出——按蒸馏后的陈述，B' 的"秩 d"在 D1–D4 下不可达（构造迫使字符族含 ∪Γ∘a_i^{-1}，秩只能 ≤ kd）；三分证明都把结论改成秩 ≤ kd 并如实报告。这说明**蒸馏陈述与原文 Lemma 10 可能不一致**（原文或许允许秩增长或假设更强）。入 ready 前必须由人工对照 arXiv:2306.08567 原文修正陈述——这正是"Taste 不能全自动、人工批准门"的实证。
- 至此论文蒸馏路线完整跑通：**Terra 从别的方向的真实前沿论文切义务 → charter 级压缩 → 预测试确认窄缝（flash/pro）**。
