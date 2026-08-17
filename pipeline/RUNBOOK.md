# Proof Expansion Evaluation Harness Runbook

## Purpose

This harness accepts proof packages incrementally. Terra can create a new `candidate` while previously frozen `ready` packages are evaluated. A package never needs to wait for a full benchmark set. `pipeline/EXECUTION_CONTRACT.md` is the canonical execution protocol; `pipeline/NEXT_ROUND_HANDOFF.md` is the next-session checklist; `pipeline/STATISTICS_CONTRACT.md` defines aggregation.

## State machine

```text
candidate → ready → claimed → running → reviewed → aggregated
              │          │        │
              └──────────┴────────┴──────→ blocked
```

- `candidate`: Terra/manual proposal; may still be edited.
- `ready`: human-approved, writer/judge visibility split frozen, and eligible for a claim.
- `claimed`: one session owns a lease (`run_id`, owner session, expiry); no other session may start it.
- `running`: paired A/B writer jobs are materialized in `runs/<run-id>/`.
- `reviewed`: all anonymous submissions have a raw judge JSON result.
- `aggregated`: paired condition labels are restored privately and the summary is written.
- `blocked`: invalid package, missing model route, malformed judge JSON, or other concrete fault. Fix with a new package version or a documented retry.

## Submission contract

1. Copy `pipeline/problem-package.template.yml` to `pipeline/packages/<package-id>.yml`.
2. Populate both `writer_bundle` and `judge_bundle`; do not put `judge_bundle` information in the writer bundle.
3. Set `split: dev` while prompts are being iterated. Only frozen `split: eval` packages contribute to an effectiveness claim.
4. Obtain human approval in `selection_record.human_approval`.
5. Set package `status: ready`, add it to `pipeline/queue.yml`, and set explicit writer model routes.

## Per-run artefact layout

```text
runs/<run-id>/
├── manifest.yml                 # private mapping from anonymous IDs to A/B; copy run-manifest.template.yml
├── jobs/                        # exact writer inputs, model route, prompt version
├── writers/                     # raw A/B closed-book outputs
├── anonymous/                   # shuffled/de-identified judge inputs
├── reviews/                     # raw GPT-5.6-SOL JSON verdicts
└── aggregate.md                 # restored paired comparison and failure-mode summary
```

Never mutate a completed run. A rerun gets a new run ID.

## Required orchestration order

1. Run `validate_package.rb` against the `ready` package, queue, and exact locked writer route; only a zero exit may proceed. Then choose one variant, writer model, and repetition. Apply that variant's `writer_bundle_patch` to a fresh in-memory copy of `writer_bundle`; never edit the package itself.
2. Materialize matched writer jobs:
   - A receives `prompt-baseline-writer.md` + only the patched writer bundle.
   - B receives `prompt-skill-writer.md` + only the same patched writer bundle.
   - Both use the same provider/model, one turn, closed-book tool policy, output budget, and repetition index.
3. Dispatch writers through the preset's `writer_closed` role row (hard zero-tool closed-book child; launch several in background in parallel). Never use the generic `subagent` or `workflow` tools for writers or judges, because those paths cannot enforce tool filters. Do not let any writer see another writer output.
4. Store private A/B labels in `manifest.yml`; generate anonymous IDs and randomize review order.
5. For each anonymous output, dispatch `judge_blind` (hard zero-tool child pinned to `micu/gpt-5.6-sol`) with `prompt-gpt56sol-reviewer.md`, the patched writer bundle, the selected variant's ground truth, and `judge_bundle`.
6. Validate that each judge response is JSON with H/D/R/C scores, step audit, and honesty assessment.
7. Run `ruby pipeline/aggregate_stats.rb --run runs/<run-id> --output runs/<run-id>/aggregate.data.json --bootstrap 10000 --seed <recorded-seed>`; if it exits nonzero, keep the derived JSON and mark the run blocked/not-shown.
8. Dispatch read-only `analyst_stats` with manifest + `aggregate.data.json`; parent writes its returned `aggregateMarkdown` verbatim to `aggregate.md`.
9. Update queue status through the claim/state-transition rules in `EXECUTION_CONTRACT.md`; write only a link to the immutable run artefact in `experiment-design.md`.

## Continuous operation

- **Terra lane:** may search and append new `candidate` packages at any time.
- **Evaluation lane:** processes the earliest `ready` package independently.
- **Human gate:** approves/freeze packages and chooses writer model routes; no agent promotes `candidate` to `ready` by itself.
- **Judge gate:** if exact `micu/gpt-5.6-sol` is unavailable, set the item `blocked`; never silently downgrade the judge.

## First execution

Do not run the placeholder queue entry. Add one approved dev package, select one writer route, then run:

```text
1 writer model × 2 conditions × 5 packages × 3 repetitions = 30 writer outputs
```

The first run validates the pipeline; it does not establish prompt effectiveness.

## Smoke test (current first action)

The queue currently holds `P001-smoke-harmonic-v1`, a hand-approved dev package whose only job is to prove the mechanics end-to-end:

1. Run `validate_package.rb`, claim the queue item, record writer/judge capability probes, then dispatch `writer_closed` twice per variant (condition A and B), 1 repetition each.
2. Materialize/record full permutation and hashes, shuffle/de-identify the four outputs, then dispatch `judge_blind` (pinned to `micu/gpt-5.6-sol`) for each.
3. Run `aggregate_stats.rb`; only if `aggregate.data.json.validation.ok=true`, dispatch read-only `analyst_stats` and have the parent write its `aggregateMarkdown` verbatim to `aggregate.md`.
4. Acceptance checklist:
   - writer and judge probes both report zero visible tools; judge route is pinned correctly;
   - writer outputs differ between A and B only through the prompt path;
   - every judge response is valid JSON with H/D/R/C, failure_modes, and a step audit;
   - manifest contains pair ids, patch hashes, route metadata and complete anonymous permutation;
   - `runs/<run-id>/` contains manifest, jobs, writers, anonymous, reviews, aggregate.data.json, aggregate.md;
   - `aggregate.md` is labelled `dev_validation_only` and makes no effectiveness claim.

After the smoke test passes, the real pilot can start on the same role rows; no route configuration is needed anymore.
