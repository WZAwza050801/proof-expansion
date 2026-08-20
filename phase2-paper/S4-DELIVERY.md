# S4 编译审查与交付（模板与规范）

- 阶段：DESIGN.md §4.4 S4——编译审查、交付。G2 人确认在此之后（`GATES.md`）。
- **过门条件**：xelatex exit=0 且 0 errors（英文版 `amsart + amsmath/amssymb/amsthm/amscd`；中文回退加 `ctex`，配方同 `tools/fragment_wrapper.tex`）。

## 编译审查清单

1. 两遍编译（交叉引用解析）；第二遍 exit=0 且 0 errors。
2. `grep -c '^!' *.log`＝0；undefined references / multiply-defined labels＝0（log 内查 Warning）。
3. 版面抽查：overfull hbox 数量与宽度记录在报告（>10pt 列明细，回 S3）。
4. PDF 页数、文件大小记录（与 fragments 总量做 sanity 对比：页数骤降＝覆盖断言遗漏的信号）。

## 交付包（固定清单，缺一不算交付）

| # | 件 | 路径（相对 run 目录） |
|---|---|---|
| 1 | 论文源码 | `paper.tex` |
| 2 | 论文成品 | `paper.pdf` |
| 3 | 覆盖断言报告（块级汇总＋全文） | `coverage-*.json` |
| 4 | 装配指令 | `instructions.json`（含 meta/sections/numbering/xrefs/edits） |
| 5 | 编辑与问题两本账 | `EDITS.md` ＋ `QUESTIONS.md`（S1 各块【编辑记录】【问题】汇编） |
| 6 | 六态账本快照＋编译日志 | `ledger-snapshot.json` ＋ `paper.log` |

## 交付记录（追加制，每轮一行）

```
<日期> | R<n> | xelatex <exit> errors=<n> | coverage PASS/FAIL | 页数 <n> | 备注
```
