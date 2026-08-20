# 交接文档：论文全文 E2E 收官 ＋ agent 派发层修复记录

> 写于 2026-08-20 收。上承 `HANDOFF-2026-08-20-REBUILD-BACKEND.md`（后半段重构方案）。
> 本会话把该方案走完：S1–S4 全文 E2E **首次全绿**；同时沉淀了派发层（subagent 基础设施）
> 的三起事故与修法。本文档 = 下一个会话的唯一入口。

---

## 1. 一句话状态

38/38 块 → S1 38/38 fragments → S2 组装（DAG 校验修正一处真实拓扑违规）→ S4 编译门
**0 errors / 70 页**；S3 格式审查未走（QUESTIONS.md 五族问题待 operator 裁决）。
headline N37 有效状态 BLOCKED（诚实传播，D6 缺稿为 charter 级外部缺料，非管线问题）。

## 2. 论文侧：交付状态对照 S4 清单（DESIGN §4.4）

| 清单项 | 状态 | 落点 |
|---|---|---|
| `paper.tex` ＋ `paper.pdf`（70 页，amsart 英文） | ✅ | `runs/pretest/seidel/` |
| coverage 报告·全文模式（长度比 3.09，计数零丢失） | ✅ | `coverage-full-paper.json` |
| coverage 报告·块级（38 份） | ⚠️ 当轮全 PASS 但未逐份落盘 | **补齐项** |
| 装配指令 JSON | ✅ | `instructions-full.json`（题、8 节、6 环境去重、10 xref） |
| 编辑与问题两本账 | ◐ 问题账=`QUESTIONS.md`；编辑账=S3 报告未成文 | **补齐项**（`S3-FORMAT-REVIEW.md` 模板在库） |
| 六态账本快照（`status` 输出落盘） | ❌ 只在日志里 | **补齐项**（一条命令） |
| 编译日志 | ✅ | `paper.compile.log`、`pass1.log` |

## 3. Agent 修复记录（派发层三起事故＋断言器一起，全部已闭环）

按"诚实账本适用于写手本身"原则，来源全部如实入账：

1. **S1 三块连败代写**：N33/N36/N37 子代理基础设施连败（重试制下 35/38 成功），
   由主 agent 以**同一 v0.3 契约**代写，产物过同样的 coverage＋探针门，来源记录在 RUN-LOG。
2. **S2 coordinator 子代理无产物**：主 agent 顶调度编辑角色出 `instructions-full.json`
   （仍守规则④：只出指令不出正文）；**assemble.py 的 DAG 校验当场抓到指令里的真实
   拓扑违规**（N14 是 N09 前置却排反）——闸门对"主 agent 代班"同样不 trust，按 dep-tree
   order 修正后组装 ok。这是"机械闸门＞角色自律"的一次实证。
3. **L9 后台任务丢失**（早于上两起）：会话卡顿后 job_list 空、零落盘；因块写手是
   零工具角色、无副作用，原样重派安全。协议沉淀：**卡顿后先 `job_list`＋`status`
   核对再重派，防重复落盘**。
4. **断言器计数盲区**（N27 报备触发）：`coverage_check.py` 原只计 `$...$`，漏 `\(...\)`；
   修复为双定界符等价计数后**立即抓出 N01"假回归"**（纯数字 `\(5\)` 是中文编号习惯），
   遂加纯数字豁免＋公式集合级 diff。教训同 splice 时代：**闸门脚本自己的 bug 只能靠
   负测试与报备发现，这是当前体系最薄的一环**（见 §6 建议②）。

## 4. 本次数据整理（归档）

以下三类移入 `runs/archive/seidel-superseded-20260820/`，原路径留符号链接（冻结文档
证据路径不断，`run-e2e-P0.sh` 经符号链接仍可重跑）：

- `paper-v2.*`（v1 学术编辑轮 7 页降质稿）；
- paper-P0 相关（P0 微组装验证轮全套＋`segments/` 段级试跑，已被全文 E2E 取代）；
- splice-v1 产物（`splice-spec.json`/`spec.json`/`paper.md`/`check-report.json`，
  机拼稿可由 blocks＋splice.py 再生）。

同步更新：`runs/pretest/seidel/README.md`（新建，目录导览）、`runs/archive/INDEX.md`、
`phase2-paper/README.md` 与 `WORKFLOW-DIAGRAM.md`（后半段 S1–S4 口径）。

## 5. 待办（按优先级）

1. **S3 五族裁决**（QUESTIONS.md 已按族归并，多数有初判建议）：①headline N37 环境
   proposition vs theorem；②rem:NXX-deps 依赖节去处（正文/后置/账本）；③结论呈现形态
   （编号环境 vs 段落式，两分支并存）；④术语定名族（约 8 个新术语）；⑤equation 升格
   与编号风格。裁决后：机械项直接改，涉内容项路由回 S1 对应块。
2. **补齐 S4 交付包**（§2 三个补齐项）。
3. **学术编辑轮**（v1 轮的合法职责，现在有 coverage＋编译门双闸保护，可安全重做）：
   跨块重复句（check-report 记 1 处）、overfull hbox、文风统一。
4. **G2 终验**（operator 人确认全文连贯、结论链闭合）→ G3 全局审读定稿。
5. 想法池（不阻塞）：放行做成 GUI 按钮（operator 提议）；run manifest（模型/契约/输入
   哈希逐块机器可读，补齐可复现性）——✅ 已落地见 §8；一期正式预测试仍待跑。
6. **I5 漂移处置（工程加固轮发现，随 S3 路由）**：修完 status 空目录 bug 后复跑，
   I5 报 N20 未引用 N15、N37 未引用 N35/N36——引用只落在【依赖与未决】记账段，
   正文未实际调用前置结论（两块都在 5 块 C 重写轮内；此前"I5 全过"是重写前读数）。
   选项：(a) v3 微改在正文补显式引用句；(b) 接受并记档。属内容级改动，归 operator。
7. **xref 断链（工程缺口，2026-08-21 归因分析发现→同日已修复）**：coordinator 按契约产出
   10 条 xrefs，但 assemble.py 不消费 xrefs 字段——指令产出即被丢弃。**修复落地**：两协议
   消费（find/replace 恰好一次定位拒盲换；legacy 自动短语定位）；草稿实测 9/10 命中、
   \ref 1→10、0 errors（见 §8 第二批）；结构性补全＝splicer v0.4 `\Nref` 机制＋coordinator
   v0.2 labels 全表（正文 676 处 NXX 的全量转换路径见 S3-RULING-SHEET）。

## 6. 给下一个会话的工程建议（本次实证支撑）

1. 派发层是当前最薄弱环节（三起事故都在这层）：重试已有协议，下一步是**幂等落盘**
   （内容寻址/临时名+原子改名），让"重复派发"从"需要小心"变成"无害"。（✅ 已落地：`tools/land.py`，见 §8）
2. 闸门脚本（schedule/assemble/coverage_check/splice）目前**无自动化测试**， correctness
   靠手工负测试维持；coverage 盲区事故已实证风险。建议：金样快照＋最小 pytest，
   与"管线不信任模型"的不信任度对齐——**对闸门代码也要不信任**。（✅ 已落地：25→30 例，见 §8）
3. 状态进文档靠手工同步（本次 README/DIAGRAM 更新即例证）；建议 `status` 输出直接
   生成 STATUS 段，文档只引用不抄写。（✅ 已落地：STATUS.md）
4. **重写/回块落盘后必须复跑 `status`（I3/I5）**——一行命令拦住 N20/N37 式引用漂移
   （本 run 实证：C 重写轮引入漂移、末轮"I5 全过"是重写前读数，直到加固轮复跑才浮出）。

## 7. 重启步骤（照抄）

```
工作目录：/Users/yongganniuniu/Desktop/数学科研实践/proof-expansion

1. 读本文件 + runs/pretest/seidel/README.md（目录导览）+ RUN-LOG.md 末三节
2. 核对账本：python3 phase2-paper/scheduler/schedule.py status \
     runs/pretest/seidel/dep-tree.v3.json --blocks runs/pretest/seidel/blocks
   应见 38/38、I5 全过、headline N37 BLOCKED
3. 从 §5 待办 1 起：陪 operator 过 QUESTIONS.md 五族 → S3 报告成文 → 机械项执行
4. 学术编辑轮 → G2 终验 → 交付
```

## 8. 工程加固落地（2026-08-21 凌晨补，§6 建议 → 已执行）

| §6 建议 | 落地 | 证据 |
|---|---|---|
| ② 闸门测试 | ✅ `phase2-paper/tests/test_gates.py`：25 例 CLI 级集成（负测试必红） | 首跑抓出 `status` 空 blocks 目录 NameError（已修＋回归锁定）；复跑真实数据发现 I5 漂移（§5.6） |
| ③ 幂等落盘 | ✅ `tools/land.py`：created/unchanged/refused/replace 四态＋JSONL 账本 | 冒烟四路径全过（refused=exit 3） |
| ②′ 可复现性 | ✅ `tools/run_manifest.py`：gen/verify（产物＋scheduler/tools/prompts 逐文件 sha256） | 本 run `manifest.json` 214 产物条目；verify 干净 |
| ③′ 状态进文档 | ✅ `runs/pretest/seidel/STATUS.md`：status 机器生成快照（头部带再生命令） | 文档改引用不抄写 |
| ⑤ 人门账本 | ✅ `tools/gate_log.py`＋`gate-ledger.jsonl`：add/list，追加式 JSONL | RUN-LOG 回溯补录 15 条（source 标原始出处；ts 为补录时间） |
| 卫生 | ✅ `__pycache__` 退出 git 跟踪；assemble/coverage_check 补模块 docstring | `.gitignore` 增 Python 条目 |

未做（留后续）：GUI 放行按钮（operator 想法池）；成本论断量化（按派发记账 token）；
I5 漂移的内容级处置（§5.6，归 operator/S3——裁决单已列为项 0）。

## 9. 第二批加固（2026-08-21 同日，§6 四件编排债清偿）

| 债 | 落地 | 证据 |
|---|---|---|
| xref 断链 | ✅ assemble.py 消费 xrefs（新 find/replace 协议＝恰好一次定位、旧协议自动短语定位）；失败拒绝/跳过均记账 | 草稿 9/10 命中、\ref 1→10、编译 0 errors（`drafts/asm-xref-bib-draft-report.json`）；新增测试 3 例 |
| 引用替换的结构性方案 | ✅ `\Nref{NXX}` 语义宏：splicer v0.4 块内标注→assemble 按全表解析→wrapper fallback 保探针可编译 | labels-all 38/38 覆盖验证；测试 2 例 |
| coordinator 契约过度承诺 | ✅ v0.2：职责 3 重写（labels 全表＋协议内 xref＋"不得假装全量转换"边界）；新增 bibliography 职责 | `prompts/coordinator.md` 版本注记 |
| 参考文献无工位 | ✅ assemble 渲染 thebibliography＋S3 模板第 8 类目＋DESIGN S4 交付包清单 | 9 条 D1–D8＋Wu 草稿编译验证（D6 诚实口径） |
| I5 复跑纪律 | ✅ 成文：重写落盘后必须复跑 status | seidel README 常用命令＋本文件 §6 |
| S3 备料 | ✅ 裁决单一页纸（五族＋项 0＋全量转换路径，每项带推荐） | `runs/pretest/seidel/S3-RULING-SHEET.md` |

测试 25→30 例全绿；RUN-LOG 第 2 批已记；manifest 再生成（含 drafts/）。

—— 完 ——
