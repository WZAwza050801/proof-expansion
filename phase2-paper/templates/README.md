# 模板目录 — 无目标模板时的保守配置（2026-08-21 定稿）

> 原则（operator 定调）：**先选目标会议/期刊官方模板；没有目标模板才用这里**。
> 标准文档类＋Latin Modern＋默认版心；不模仿"arXiv 风格"（arXiv 是发布平台不是期刊），
> 不压缩页边距、不 `\resizebox` 公式、不手写引用角标。

## 文件

| 文件 | 用途 |
|---|---|
| `arxiv-base.tex` | 通用保守基座：article 11pt + T1 + lmodern + microtype + amsmath/amssymb/mathtools + booktabs + hidelinks hyperref；定理环境白名单已配 |
| `arxiv-xelatex-cn.tex`（未建） | 中文/复杂 Unicode 时：article + fontspec + Latin Modern Roman + xeCJK + Noto Serif CJK；**提交前必须干净环境测试**（arXiv 环境需能取到所引字体） |

## 引擎决策表

| 场景 | 引擎 | 字体 | 依据 |
|---|---|---|---|
| 英文数学论文（默认） | **pdflatex** | T1 + lmodern | 兼容性最好；本仓库 Seidel 运行区绿灯配方见对照 |
| 中文 / 复杂 Unicode | xelatex | fontspec + xeCJK（Noto Serif CJK SC） | 唯一可行；依赖字体须进提交包或环境可得 |
| Times 风格 | pdflatex | **newtxtext + newtxmath 成对** | 禁用裸 `\usepackage{times}`（正文变 Times 数学不变，风格断裂） |

## 本项目（Seidel 预试）现状对照

- 现行配方（2026-08-21 起迁）：**`sibling-wu`**＝article 11pt＋geometry margin=1in＋
  lmodern/microtype＋colorlinks 蓝链＋tcolorbox 红框（UNPROVED INPUT G#）＋状态字形＋
  目录＋按节定理编号，xelatex 编译；参照系＝Gao–Lou–Wu–Zhang 2026-08-19（operator
  实地对比拍板：原版"综合下来丑"，三真凶＝灰弹幕状态标注/窄版心小字号/隐形链接）；
- 历史：08-20 曾定"amsart＝AMS 官方类不迁移"——当时**无参照物**；08-21 参照物到位后
  推翻。`amsart-arxiv` 保留于 assemble `TEMPLATES` 作保守回退；
- B 层 PDF 技术质量已验证 PASS（paper_lint 2026-08-21：字体全嵌入、0 Type 3、
  单一页面尺寸、0 空白页；sibling-wu 迁移后复验保持 PASS）。

## 提交前最低流程（paper_lint 已内建 A/B/C/D 评级）

```bash
latexmk -pdf -interaction=nonstopmode -file-line-error -halt-on-error main.tex
python3 ../tools/paper_lint.py main.tex --log main.log --pdf main.pdf
qpdf --check main.pdf && pdffonts main.pdf && pdfinfo main.pdf
```

- **A（可编译）/ B（PDF 技术）应 PASS**——机械判定，无主观成分；
- **C（版式）/ D（引用）**：机械代理项过门后，残余视觉项（孤寡行、浮动体、角标重叠）
  逐页人工抽查——"硬指标全过＋视觉启发式＋最终人工确认"三段式（operator 判据原文）；
- 提交打包（收集依赖/清注释）用 arxiv-collector / arxiv-latex-cleaner，属确定性脚本，
  不是 agent skill。
