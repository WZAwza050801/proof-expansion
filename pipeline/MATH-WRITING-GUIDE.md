# 数学学术写作指南（开源材料归纳）

- 日期：2026-08-18
- 用途：给写手（局部扩写）与拼接/学术编辑 agent 提供"学术写作特调"的依据。信息尽量保留，逐条给出来源，便于回溯。
- 主要来源：
  - [Halmos, *How to Write Mathematics*](https://marktomforde.com/academic/gradstudents/images/Halmos-Summary.pdf)（1970，20 节；此处据 Peter Cameron 的逐节摘要）
  - [Tao 写作建议（Andrew Best & Yuval Peres 整理）](https://bimsa.net/activity/MathematicalCommunication/files/Lec2,3%20--%20Advice%20from%20Tao%20on%20Writing.pdf)
  - Steenrod 等主编 [*How to Write Mathematics*](https://books.google.com.sg/books?id=Qj0PAQAAMAAJ)（经典合集）
  - [Evan Chen, Notes on proof-writing style + LaTeX style guide](https://web.evanchen.cc/olympiad.html)（MOP 讲义；含 LaTeX 洁癖清单）
  - [Better writing math texts（Khesin 收集）](https://www.math.utoronto.ca/khesin/biblio/better_writing.pdf)

---

## 0. 心法（全局）

**Halmos 二十节的骨架（逐条）**：

1. 没有菜谱；但有些基本原则。
2. **Say something**：既别说空话，也别什么都想说。
3. **Speak to someone**：明确写给谁；脑中想一个具体的人，对他讲。
4. **Organize first**：先自由乱写，再强迫自己画一张"要写什么"的结构图。
5. **Think about the alphabet**：符号别打架——Σ 别既当指标又求和；ax+by 与 a₁x₁+a₂x₂ 二选一；∈ 和 ε 分清；"序列 n_ε 随 ε 无穷而趋于 0"是噩梦；"二次方程 xa²+ya+z=0"是噩梦。
6. **Write in spirals**：按 1,2,1,2,3,1,2,3,4 的顺序写；第一遍倾泻，后面再清。每节给个标题——想不出标题，可能你根本不知道这节在讲什么。
7. **Organize always（螺旋式组织）**：第 1 节的例子要为第 2 节备好；数学写作可以像侦探小说有伏笔和线索（如"度量空间"是"一般拓扑"的伏笔）。
8. **Write good English**：既不懒散也不花哨；语言要**正确且不扎眼（unobtrusive）**。
9. **Honesty is the best policy**：目的是帮人懂，不是炫技。尤其小心 "obvious" 及其近亲——六个月后你自己再读、或给别人讲时，它还 obvious 吗？
10. **Down with the irrelevant and trivial**：平凡情形要处理、别藏，但别唠叨。定理陈述就该是陈述：自足、无闲聊、无多余假设（当然也无缺失假设）。
11. **Do and do not repeat**：定理 2 若与定理 1 几乎相同，措辞尽量一致、并把差异用"鼓点"点出；但逐字重复同一句话无助于理解——要再说就用别的方式说。若定理 2 的证明几乎复制定理 1，可能是你还没真正懂。
12. **The editorial "we"**：指的是"作者＋读者"，不是君主的"朕"。
13. **Use words correctly**："any" 危险（可表全称可表存在）；"where""equivalent""if…then if…then" 都要小心。
14. **Use technical terms correctly**：别说"函数 z²+1 是偶（even）"；区分 set/sequence、contains/includes；**最重要是前后一致**。造术语三原则：(1) 能避免就避免；(2) 必须造的认真想、查同义词；(3) 老术语用对、用一致、别卖弄。
15. **Resist symbols**："Every continuous function f is bounded" 里的 f 多余；别写"g 也满足 (*)"。长串以 = 开头的等式链，读者怎么跟？
16. **Use symbols correctly**：该用 ∈ 用 ∈、该用 "in" 用 "in"（"For x in A, we have x∈B" 可同句并用）；**避免两个公式只用标点隔开**；**避免句子以公式开头**。
17. **All communication is exposition**：写书、写论文、备课，规则通。
18. **Defend your style**：抵抗编辑的机械修改（如把 "negative or positive" 改成 "positive or negative" 反而错义）。
19. **Stop when you come to the end**：说完了就停，哪怕还能说更多。
20. **Do as I say, not as I do**。

---

## 1. 引言与推销（Tao）

1. **快速进入要点**（attention is limited）。
2. **主结果适当详述**：先写一个特殊情形，再写完全一般的形式。
3. **对比已有工作**说明新意、优点、后果（Yuval：部分可延后到 "Related Results" 一节）。
4. 引用写**全作者名＋年份**（不是 "[4]"），可用 "[F77]" 式（LaTeX 自动）。
5. 问：**能否去掉主结果中的假设而仍成立？** 有 sharpness 反例吗？给出。

---

## 2. 组织与结构（Tao + Yuval）

- 读者只知道你告诉他的结构（作者有 **curse of knowledge**）。
- 章节 = 结果的**里程碑**：**Step 2 测试**——若一节只能叫 "Step 2/Step 3"，就该重组织。标题要有信息量（"Counting polynomial configurations"），少用数学符号当标题；别叫 "Technical lemmas"。
- 引言里写 **Roadmap / Structure / Outline**。
- 画一张**蕴涵/依赖图**（implication map）：少数关键结果靠若干次要结果支撑，这结构要让读者一眼看清。是否放进论文另说，但画图过程本身能厘清里程碑。
- **每节最好能一句话概括**（读者能安全忘掉除一个结果外的全部内容）。
- **引理该独立出来的条件**（Tao）：心理上重要，或用两次以上。只用一次、又次要的子论证 → **折进重要引理的证明里**。
  - ⚠️ **Yuval 反对**：主张**模块化**——论证的每一步都给它一个引理，读者才能"核对一部分→忘掉→回头再核对另一部分"。
  - （这条分歧**正好对应我们依赖树的拆题粒度**：折得细=Yuval，折得粗=Tao；交给 G0 拆题门人工定。）
- **Aggressively hide less important content**：旁注、冗长计算、过度技术化的证明尽量后置。
  - Yuval：**别用附录**，用正常章节、放后面即可；别叫自己的工作 "technical"（创新往往就在技术部分，要好好推销）。

---

## 3. 定理/引理陈述要自足（Tao，最该写进我们提示词的一条）

- **Self-contained**：结果里所有术语都在文中定义过，所有附加假设都写在定理/引理正文里。
- 反例（要避免）：在论文/章节开头写一句"In Section 2, all functions are assumed to be nondecreasing and continuously differentiable"——读者多不按顺序读，这句极易漏。
- 若假设**又长又反复用**：写成 "Assumption (1)"，之后引理写 "Let f satisfy Assumption (1). Assume also f is green. Then…"。
- 若假设**长但只用两三次**：一个引理写全假设，后续写 "Let f be as in Lemma 3.1. Then…"。
- 标准引理**没有好理由不要重证**（显得不熟领域）；能引教材就引；源难读/过时才考虑用现代语言重写并注明。

---

## 4. 引用规范（Tao + Yuval）

- 引用写全作者名＋年份；给**精确引用**（"Proposition 7.1" 而非整本书）。
- "well-known" 的结果也要找好引用；找不到就请教领域内的人。

---

## 5. LaTeX 学术排版惯例

- **环境与编号**：`\newtheorem` 系列——`theorem / lemma / proposition / corollary / definition / remark / proof`；编号自动（`\ref`/`\eqref` 引用，不手写编号）。
- **行内 vs 独立**：行内用 `$...$`；独立公式用 `\[ ... \]`（**别用 `$$`**）；多行用 `align`/`align*`、`gather`、`cases`。
- **符号规范**（Evan Chen "LaTeX pet peeves" 与通用洁癖）：
  - 整除用 `\mid`（留空），别用裸 `|`；
  - 算子用 `\operatorname`/`\DeclareMathOperator`（如 `\hom`、`\Spec`）；
  - 文字下标用 `\text{...}`，别用斜体 `max_{prime p}`；
  - 区分 `-`（减号）、`--`（en-dash）、`---`（em-dash）；
  - 分段函数用 `\begin{cases}`；
  - 集合写 `\{ x \in X : P(x) \}`（`\mid` 或 `:`）；
  - 句子以公式开头、公式间只靠标点相连、标点缺失——都是病（对齐 Halmos 16）。
- 文档类：`amsart`/`article`+`amsthm, amsmath, amssymb`。

---

## 6. 落到我们两个 agent 的"学术写作特调"清单

**写手（局部扩写，任务一）**：

1. 该块若是一步可独立陈述的引理，用 `Lemma`/`Proposition` 环境＋编号（编号按依赖树拓扑序，由拼接器统一赋，写手先占位 `\label`）；
2. 陈述**自足**（Tao §3）：不依赖"上文已假设"的隐藏前提；
3. 学术语体（Halmos 8/13/14）：不用懒散/花哨句；`we`=作者+读者；"any"→each/every；术语全篇一致、不造新词；
4. 字母表纪律（Halmos 5）：符号不与全局约定卡冲突、∈/ε 分清、不重载 Σ；
5. 符号规范（Halmos 15/16）：能省符号就省、别句首公式、别两公式只靠标点连；
6. "obvious" 少用（Halmos 9）——这步是不是 obvious，要按"六个月后还 obvious 吗"自查。

**拼接/学术编辑 agent（任务二，待建 `prompt-splicer.md`）**：

1. 章节 = 里程碑（Tao Step 2 测试），标题有信息量、少符号；
2. 写 Roadmap/Outline，画依赖图（我们的 dep-tree 就是现成的 implication map）；
3. 引言卖点（Tao §1）：快进要点、先特例后一般、对比已有工作、给 sharpness 反例；
4. 隐藏次要内容（Tao）：旁注/冗长计算后置；Yuval 式不用附录；
5. 引理折留取舍（Tao vs Yuval）：基于依赖树，把"只用一次的次要子论证"折进父证明、把"用两次以上或心理重要"的保留为引理——这步可设人门；
6. 符号/术语全篇统一（Halmos 14）、去重（Halmos 11：同构定理一致措辞并点出差异；重复内容换说法）；
7. 说完了就停（Halmos 19）。
