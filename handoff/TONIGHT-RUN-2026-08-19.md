# 今晚起跑卡（2026-08-19 夜）

> 目标：二期 Seidel，从 **L0** 按调度器逐层推。**不要**从 N19 之类的中间层空降。

## 0. 前置（已就绪，无需再做）

- ✅ 目录已分一期/二期/common，93→200 处引用已改
- ✅ 调度器 `phase2-paper/scheduler/schedule.py` 已写并自测（validate/plan/status/next/taskbook/spec 全通）
- ✅ 独立审图已跑，结论落在 `runs/pretest/seidel/DAG-AUDIT-2026-08-19.md`
- ✅ `dep-tree.v2.json` 已按审图补 15 条漏边＋补全 N01 的 P0 方差清单（无环，validate PASS）
- ✅ preset 新增 `block_writer` 零工具角色（micu/gpt-5.6-sol, maxTokens 65536），**已 mount-validate 通过**
- ✅ `judge_blind` 预算 16384 → 65536（同一个 P001 坑）

## 1. 在哪跑

**必须新开 `proof-pipeline` preset 会话**——本会话没有 `block_writer` / `writer_closed` / `judge_blind` 角色行。

```
工作目录：/Users/yongganniuniu/Desktop/数学科研实践/proof-expansion
```

## 2. 标准循环

```bash
S=phase2-paper/scheduler/schedule.py
T=runs/pretest/seidel/dep-tree.v2.json
B=runs/pretest/seidel/blocks
K=runs/pretest/seidel/taskbooks

python3 $S next $T --blocks $B            # ① 本批该写哪些（只吐前置全落盘的）
python3 $S taskbook $T --blocks $B --node N00 --out $K   # ② 生成任务书
                                          # ③ 把 $K/N00.taskbook.md 全文喂给 block_writer
                                          # ④ 把返回的文本原样存成 $B/N00.md（operator 落盘）
python3 $S status $T --blocks $B           # ⑤ 查降级 / I3 违规
                                          # ⑥ 过人门 → 回 ①
```

## 3. 今晚的第一批

`next` 会吐 **L0 = {N00, N01}**，档位 **MANUAL**。

**N01 是全树最危险的节点**（污染 36/37）。审图判定原 N01 不合格——缺 charter P0 的五项承重方差约定，直接威胁 commitment 2（目标必须是 $RHom_{A^e}(A,P_\phi)$，不是它的对偶/反范畴/$\phi^{-1}$ 版本）。v2 已把八项清单写进 statement，**但仍需你亲自过目 N01 的产出**：约定表要能直接读出目标方差。

L0 过了再推 L1(N02) → L2(N03) → L3(N04,N07)…… **前 7 层全是 manual**，别开 yolo。

## 4. 三条纪律

1. **只走 `block_writer` 角色行**，不用 `workflow` / 通用 `subagent`。上一轮 5/6 块失败就是这个原因。
2. **agent 只回文本，你落盘。** 零工具角色不可能自己写文件。
3. **BLOCKED 是合法产出。** Seidel 是 open problem，预期大量 BLOCKED。报 BLOCKED ＋ 最小 blocker ＋ 能证到的最强结论，`status` 会诚实传播到 headline。**不要**让模型用"按约定视为已声明 (FIXED)"把洞糊过去——上一轮 N19 就是这么废掉的。

## 5. 旧产物怎么处理

`blocks/N19.md` 已被 `status` 判为 I3 违规（声称 PROVED-IN-PROJECT，但 N08/N09/N14 全未落盘，实际降级为 CANDIDATE）。

**建议**：推进到 L7 时按正常流程重写 N19（那时 N08/N09/N14 都在了）。在此之前可以留着当格式参考，但不要拼进论文。

## 6. 若要收 L9–L19 那根单链

审图建议删两条假边（N27←N26、N29←N28），关键路径可从 11 层降到 8–9 层，串行深度 24 → ~21。**我没有自动应用**——删边等于让块看到更少上下文，是优化不是纠错。等你推到 L9 附近再决定，理由见 `DAG-AUDIT-2026-08-19.md` 第 6 节。

## 7. 拼接（本批不做）

等有足够块落盘后：

```bash
python3 $S spec $T --out runs/pretest/seidel/spec.json
python3 phase2-paper/tools/splice.py runs/pretest/seidel/spec.json $B \
        runs/pretest/seidel/paper.md runs/pretest/seidel/check-report.json
```
再交 `phase2-paper/prompts/splicer.md` 做学术编辑。
