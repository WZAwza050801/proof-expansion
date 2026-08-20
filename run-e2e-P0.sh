#!/bin/bash
# P0 微组装 E2E（S2→S4）：装配指令 + fragments → paper-P0.tex → 编译门 → 覆盖断言
set -e
cd "$(dirname "$0")"
S=phase2-paper/scheduler/schedule.py   # (unused here; keep for context)
FRAG=runs/pretest/seidel/fragments
INSTR=runs/pretest/seidel/instructions-P0.json
BASE=runs/pretest/seidel/baseline-P0.md
TEX=runs/pretest/seidel/paper-P0.tex

echo "== S2 组装 =="
python3 phase2-paper/tools/assemble.py "$INSTR" "$FRAG" \
  runs/pretest/seidel/dep-tree.v3.json "$TEX" \
  --report runs/pretest/seidel/asm-P0-report.json

echo "== S4 编译门（两遍）=="
cd runs/pretest/seidel
xelatex -interaction=nonstopmode paper-P0.tex > /dev/null 2>&1 || true
xelatex -interaction=nonstopmode paper-P0.tex > paper-P0.compile.log 2>&1
echo "xelatex exit=$?"
ERRS=$(grep -c '^!' paper-P0.compile.log || true)
UNDEF=$(grep -ci "undefined" paper-P0.compile.log || true)
echo "errors=$ERRS undefined-refs=$UNDEF"
[ "$ERRS" = "0" ]
cd ../../..

echo "== S4 覆盖断言（paper 模式：产物 vs 基准）=="
python3 phase2-paper/tools/coverage_check.py paper \
  runs/pretest/seidel/paper-P0.tex "$BASE" \
  --report runs/pretest/seidel/coverage-P0-paper.json

echo "== E2E PASS =="