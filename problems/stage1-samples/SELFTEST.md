# Stage-1 样题自测记录（窄缝定档）

- 日期：2026-08-18
- 协议：`prompt-terra-problem-curator.md` v2「窄缝的操作化定义」＋`problems/stage1-samples/README.md`
- **重要边界**：本批探针为**预测试预演**——v4-pro 探针运行于通用 subagent、v4-flash 探针经 workflow 模型覆盖（两者均有工具但按指令闭卷）；正式定档必须在 proof-pipeline 会话用零工具 `writer_closed` 角色行重跑。

## 探针协议

| 探针 | 输入 | 窄缝判据 |
|---|---|---|
| 裸题探针 | 仅 `writer_bundle.statement` | 补不出完整证明 → 通过（①） |
| 带包探针 | 完整 `writer_bundle` | 补出可核验完整证明（judge C ≥ 3）→ 通过（②） |
| 定档 | ①∧② → `confirmed`；仅① → `downgraded_to_probe`；仅② → `excluded_instant_solve` | — |

## 结果（v4-pro 与 v4-flash，共 20 份探针）

| 包 | 裸题（pro） | 裸题（flash） | 带包（pro） | 带包（flash） | 定档（预演） |
|---|---|---|---|---|---|
| S01-egz | ❌ 秒杀（点名 Chevalley–Warning，含合成情形） | ❌ 秒杀（连 Chevalley–Warning 本身都从零证出） | ✅ | ✅ | **excluded_instant_solve** |
| S02-finite-division-ring | ❌ 秒杀（类方程＋分圆三件套） | ❌ 秒杀 | ✅ | ✅ | **excluded_instant_solve** |
| S03-fisher-inequality | ❌ 秒杀（关联矩阵特征值法） | ❌ 秒杀（A^T A 正定法） | ✅ | ✅ | **excluded_instant_solve** |
| S04-frankl-wilson | ❌ 秒杀（h_A 构造＋多线性化完整默写） | ❌ 秒杀（同左，含威尔逊） | ✅ | ✅ | **excluded_instant_solve** |
| S05-stone-weierstrass | ❌ 秒杀（|f| 逼近＋插值＋双覆盖完整默写） | ❌ 秒杀（二项级数证 √ 的自足版本） | ✅ | ✅ | **excluded_instant_solve** |

## rubric 盲评探针（1.3 验收复核）

| 项 | 结果 |
|---|---|
| judge-probe（v4-pro 按 v2 rubric 打两篇样稿） | **通过**：H 稿 C=G=R=4、L=4.0；A 稿 C=G=R=4、L=1.5；L 分差 2.5，四个子项一致拉开且每条附原文证据，C 未误伤 |

## 结论（归档）

1. **1.3 验收通过**：同正确性两稿，v2 rubric 稳定拉开可读性（2.5 分，客观子项驱动，含原文证据）。
2. **1.2 样题验收未达成**：5/5 题对 v4-pro 与 v4-flash 都是秒杀题（含两道"证明路线冷门"的升级题 FW 与 S–W）。两模型的数学证明记忆/重构能力远超"弱写手"假设——**经典定理蒸馏池整体落在当前两模型的秒杀区**。
3. **脚手架本身有效**：10/10 带包探针全部完整闭合；v2 题包格式（脊柱＋completion test＋依赖）无故障。协议（裸题/带包/定档）也被验证可靠。
4. **窄缝比预想高得多**，下一步选项（暂停后继续时选）：
   - (a) 阶段 2 正式能力预测试：在 proof-pipeline 会话对更多候选模型（含更弱模型）做裸题扫描，先摸出每个模型的秒杀边界；
   - (b) 题源升级：主池 B 研究级片段（Putnam-AXIOM 风格：近期论文关键引理切片，原文证明作 judge 锚点），记忆污染最低；
   - (c) 出题工艺升级：去答案化只能改"思路"，改不了"模型背过整条证明"——需要题干本身更冷门（论文片段）或结论改写为等价非标准形式；
   - (d) 骨架细度作为调节旋钮（TECH-ROADMAP 原则）：若要保留经典定理题，可把骨架细到"只给依赖不给路线"，或接受对强模型用更细骨架重开有效区间——这是阶段 2 的标定工作。
5. 五题保留为**秒杀题对照样题**（冒烟/校准/对比用），不进 A/B 区分度池。
