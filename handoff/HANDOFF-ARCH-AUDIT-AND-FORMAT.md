# 交接文档：agent 架构审计 ＋ 论文格式调整（新会话入口）

> ✅ **2026-08-21 深夜续会已办结**（见 RUN-LOG 末两节＋gate-ledger #19）：
> 审计三缝全部坐实（结论与收缝建议记录在案，未动架构）；格式工单 1/2/4/5 完成
> ——overfull **65→0**、文献 9 键全挂 cite、术语 4 族统一（D1 引文保留）、
> 编译 exit=0/0 errors/74 页；工单 3（author）待 operator、工单 4（abstract）
> 已呈 operator 过目。工具面新增 assemble `meta.short_title`（页眉短题根因修复）。
> 下一步待办：R2 审查轮（先重刷 lint 定快照、挂 preset 会话最小探针）、
> coordinator 下次运行前落实 xref∈deps 机械检查建议。
> **风险登记册：`handoff/RISK-REGISTER.md`**（三缝＋两元风险，含销账栏）。
> 以下为原始工单存档。

> 写于 2026-08-21。上一会话（14 commits，`8c3bb84`→`db72527`）完成了 S3 定稿、S5 审查
> 技能块、模板层与工程加固。**operator 本轮指令：先重新审计 agent 架构，然后重新调整
> 论文格式即可，不用 verify**（不跑测试/manifest/lint 复验轮，除非临时要求）。

---

## 1. 审计对象清单（agent 架构全图）

### 提示词（`phase2-paper/prompts/`）
| 文件 | 现版本 | 本会话改动 | 审计点 |
|---|---|---|---|
| `splicer.md` | v0.4 | +职责6 `\Nref` 块内标注 | 局部纪律完备；视觉职责正确地**不在**这里 |
| `coordinator.md` | v0.2.1 | +职责2b 模板定调、labels 全表、bibliography | 职责2b 刚补（`db72527`），**尚无任何一次真实运行验证过它下模板指令**——审计重点 |
| `paper-reviewer.md` | v1.1 | 全新（S5 审查轮 G3a/G3b/G3c） | G3b/G3c 契约就绪但 **R2 轮从未跑过** |
| `splitter.md` / `judge-reviewer.md`（一期） | 未动 | — | 拆题/盲审协议，与二期无冲突 |

### Preset 角色行（`~/.dsh/.agent-presets/proof-pipeline/agent.cordis.yml`）
- 本会话新增 `role-paper-reviewer`（micu / gpt-5.6-sol / 65536 / toolName `paper_review`），
  备份在同目录 `agent.cordis.yml.bak-20260821`；
- 既有：`role-block-writer`、`role-judge-blind`、`role-analyst`、各 writer 角色；
- **审计点：`role-paper-reviewer` 从未被 spawn 过**——角色行存在≠能跑通，新会话若要
  跑 R2 先用最小探针确认 toolName 生效。

### 工具与门（`phase2-paper/tools/` ＋ `scheduler/`）
| 组件 | 状态 | 审计点 |
|---|---|---|
| `assemble.py` | 模板层+xref+Nref+bib+intro/conclusion+deps附录 | `meta.template` 只在 paper-v3 手工指令里用过一次 |
| `paper_lint.py` | 五族+三级+A/B/C/D+battery（自包含可独立部署） | checkcites 对内联文献 model-mismatch 是已知正确行为 |
| `coverage_check.py`/`schedule.py`/`splice.py` | 加固完毕 | 测试锁定（50 例，`tests/test_gates.py`） |
| `templates/arxiv-base.tex` | 实测编译全绿 | 本项目用 amsart（AMS 官方类），不迁移 |

### 已知未闭合的缝（审计时优先看）
1. **R2 内容审查轮未跑**（契约+角色+输入快照全就绪：paper-v3 @ lint PASS 版）；
2. coordinator 职责 2b（模板）无运行记录——v0.1 的 xref 越权前科说明"契约写了"不等于"做对"；
3. S5 的 G3b 节级审查与学术编辑轮的边界（FINDING 清单 vs 直接改排）未实战校准。

## 2. 论文格式调整工单（内容级，按优先级）

输入：`runs/pretest/seidel/instructions-v3.json` ＋ `fragments/`；重组装一条命令：
```
python3 phase2-paper/tools/assemble.py runs/pretest/seidel/instructions-v3.json \
  runs/pretest/seidel/fragments runs/pretest/seidel/dep-tree.v3.json \
  runs/pretest/seidel/paper-v3.tex --labels runs/pretest/seidel/labels-all.json
```

| # | 工单 | 规模 | 说明 |
|---|---|---|---|
| 1 | **overfull 65 处逐处断行**（54 处>10pt，最大 239pt） | 大头 | 长公式 `align`/`multline`/手动断点；逐 fragment 改（探针纪律），非论文级改 |
| 2 | **文献挂 cite**：D1–D5/D7/D8/WU 共 8 条列而未引 | 中 | 正文叙述性提及处（GPS/JYZ/Ganatra 等）挂对应键；N02 审计段是主战场 |
| 3 | author 实名 | operator 拍板 | 目前 `OPERATOR-FILL`；operator 说不急 |
| 4 | abstract 定稿 | operator 过目 | 草稿在 `instructions-v3.json` `meta.abstract`（1223 字符） |
| 5 | 术语 4 族 7 处统一（`drafts/terminology-report.md`） | 小 | forward/positive graph 等 |
| 6 | 结论散文 3 处 NXX 语义化 | 小 | 可选 |

**operator 指令：本轮不用 verify**——格式改完不必跑 lint/manifest/测试复验；
compile 一次确认能编译即可（交付级验收留到以后）。

## 3. 快速上下文（新会话 3 分钟上手）

- 论文：`runs/pretest/seidel/paper-v3.pdf`（73 页，0 errors，lint PASS，A:ADVISORY/B:PASS/C:FAIL/D:FAIL）；
- 过程唯一事实源：`runs/pretest/seidel/RUN-LOG.md`（末 5 节＝本会话全部）；
- 上一轮交接：`handoff/HANDOFF-PAPER-AND-AGENT-REPAIR.md`（§8–§10 工程账）；
- 归档区：`runs/archive/seidel-superseded-20260820/`（符号链接保持证据路径）。

—— 完 ——
