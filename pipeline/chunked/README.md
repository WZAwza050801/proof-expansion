# 分块撰写流水线原型（chunked paper-writing pipeline）

- 日期：2026-08-18
- 状态：原型 v0（可运行；写手派发暂由 operator 经 DSH 角色/subagent 执行，正式接入 proof-pipeline preset 列入阶段 3）
- 设计依据：`../CHUNKED-PAPER-WRITING-DESIGN.md`
- 文件地图：
  - `splice.py`：确定性拼接器＋一致性检查器（stdlib，无外部依赖）；
  - `demo/egz-paper.spec.json`：切割规格示例（论文 = 头号定理，切成 3 个证明义务块，含全局约定卡与块间依赖 DAG）；
  - `demo/outputs/`：各块写手输出（正文/结论/依赖与未决 三段）；
  - `demo/assembled-paper.md` 与 `demo/check-report.json`：拼接产物与检查报告（由 splice.py 生成）。

## 一、切块规格（spec JSON）

```json
{
  "paper_id": "...",
  "title": "论文标题/头号定理",
  "headline_block": "B3",
  "conventions": { "符号名": "全论文唯一含义", "...": "..." },
  "allowed_dependencies": ["D1", "D2"],
  "blocks": [
    {
      "id": "B1",
      "title": "块标题（一个证明义务）",
      "objective": "本块要建立什么（思路在、细节不全）",
      "completion_test": "本块算完成的客观验收标准",
      "deps": ["B2"],          // 前置块（DAG，必须无环且按拓扑序排列）
      "allowed": ["D1"]        // 本块可用的允许依赖
    }
  ]
}
```

## 二、块写手派发提示（operator 用，替换 {{}} 后交给零工具写手角色）

```
你是分块论文撰写流水线中的"块写手"。你只负责论文的第 {序号} 块（一个证明义务），
输入是局部上下文，输出三段式（缺一段即不合格）。

【全局约定卡】{{CONVENTIONS}}
【前置结论】{{PREDECESSOR_CONCLUSIONS}}
【允许依赖】{{ALLOWED_DEPENDENCIES}}
【本块义务】objective: {{OBJECTIVE}}  completion test: {{COMPLETION_TEST}}

纪律：
1. 只写本块的证明正文；不复述背景与全局约定（拼接后不许出现重复段）；
2. 引用前置块结论时写"由块{k}的结论：……"；引用允许依赖只写编号并核对前提；
3. 本块结论要写成一整句话，能被后续块直接引用；
4. 卡点处理：先补能补的部分；确需包外事实时在【依赖与未决】写最小 blocker＋最强已证定理。

输出（严格三段）：
【正文】
...
【结论】
一句话已证结论（无卡点时）。
【依赖与未决】
引用的块编号与允许依赖编号；本块新引入的局部符号（若有）；未决卡点（若有）。
```

## 三、拼接与检查（splice.py）

```bash
python3 splice.py demo/egz-paper.spec.json demo/outputs demo/assembled-paper.md demo/check-report.json
```

确定性检查（不消耗 LLM）：

1. **引用完整性**：正文中出现的"块k/Dn"必须在本块 spec 的 deps/allowed 内；每个 dep 块的【结论】非空；
2. **结论链闭合**：块 DAG 无环且按拓扑序；headline_block 的【结论】非空；
3. **符号一致性**：约定卡符号不得被任何块以不同含义重定义；同名局部符号在两块中的定义必须一致；
4. **重复检测**：跨块出现相同长句（≥60 字符）→ 报警，供拼接器删除。

## 四、与 A/B 测评的关系

- 块写手提示词 = `prompt-skill-writer.md` v0.4-dev 的纪律 ＋ 本流水线的三段接口；A/B 对比测的是【正文】质量（G/R/L/C），三段接口是流水线信封，不进入 A/B 评分。
- 拼接级质量是另一条评价轴（本脚本的确定性检查 ＋ 一次全局 judge 读），不混入块级分数。
