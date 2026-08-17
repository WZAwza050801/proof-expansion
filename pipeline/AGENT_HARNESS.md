# Proof Expansion Agent Harness

## What has been built

This is a **DSH agent preset plus workspace protocol**, not a one-shot benchmark script.

- User-owned DSH preset: `proof-pipeline` (`Proof Expansion Evaluation Harness`)
- Persistent queue: `pipeline/queue.yml`
- Versioned role prompts: project-root `prompt-*.md` files
- Package visibility boundary: `pipeline/problem-package.template.yml`
- Hard per-role capability locks in the preset: `terra_curator` (search allowed, `openrouter/openai/gpt-5.6-terra`), `writer_closed` (zero tools, `deepseek-v4-flash`), `judge_blind` (zero tools + `micu/gpt-5.6-sol`), `analyst_stats` (**read-only** artefact interpretation)
- Immutable per-run artefact convention: `runs/<run-id>/...`

The preset keeps a session in “harness operator” mode. It accepts candidate packages incrementally, selects ready packages independently, creates matched A/B jobs through role-locked subagents, anonymizes outputs for GPT-5.6-SOL review, and writes/aggregates artefacts. The native `workflow` tool is not used for writers or judges because it cannot enforce their tool filters.

## Why this is a harness rather than an automatic daemon

The DSH `workflow` tool executes a bounded fan-out job in the foreground; it is not a durable scheduler. Therefore the durable queue lives in the workspace and the harness agent acts as the scheduler whenever you tell it to run or continue. This is deliberate:

- every promotion to `ready` has a human approval gate;
- every run is versioned and auditable;
- Terra can add candidates at any time without blocking ready evaluations;
- no background process silently mutates packages or substitutes model routes.

## Normal usage in a new DSH session

1. Choose the **Proof Expansion Evaluation Harness** preset in the Web agent-preset picker.
2. Ask the agent to inspect the queue, validate a package, enqueue it, or run the next ready item.
3. The first run must be a `dev` package and validates mechanics only.
4. Once prompt versions are frozen, add approved `eval` packages; only those runs support a claim of prompt effectiveness.

## Agent commands in natural language

- “检查 proof-expansion 的队列和流水线状态。”
- “验证 `pipeline/packages/P001-...yml`，若合格则把它加入队列，但不要运行。”
- “按已冻结的 writer role，对队列中第一个 ready dev 包跑一次 A/B，3 次重复。”
- “我要换写手模型；先为该 route 新增零工具 writer role、mount-validate，再建 run。”
- “继续处理下一个 ready 包；Terra 的候选题不要阻塞已有任务。”
- “汇总 run `<run-id>`，但不要把 dev 结果写成有效性结论。”

## Execution safety contract

- A/B pairing is exact inside each writer model and repetition.
- Writers are closed-book **by capability, not only by prompt**: `writer_closed` children have zero tools, cannot search, read files, run commands, or delegate.
- Judges are blind **by capability**: `judge_blind` children have zero tools and a pinned model; `judge_bundle`, source reference proof, and A/B labels never enter writer prompts.
- Only `analyst_stats` restores A/B labels in its reasoning. It has no mutation tools; the parent Harness writes its `aggregateMarkdown` response verbatim to `aggregate.md` after deterministic `aggregate_stats.rb` completes.
- Raw artefacts are append-only. Corrections create new package or run versions; full execution rules are in `pipeline/EXECUTION_CONTRACT.md`.

## Current state

`P001-smoke-harmonic-v1` is the first queued `dev` item. It is a mechanics-only smoke package, not a benchmark and not evidence for prompt effectiveness. Its purpose is to verify zero-tool writers, anonymized micu/gpt-5.6-sol judging, and analyst aggregation end to end before Terra begins producing real candidates. The executable next-session sequence is in `pipeline/NEXT_ROUND_HANDOFF.md`.
