// DEPRECATED FOR THE CANONICAL PROOF-EXPANSION PIPELINE.
//
// Do NOT pass this file to DSH `workflow` for writers or judges. The workflow
// hook supports provider/model overrides but cannot apply per-child toolFilter
// or persona, so it would weaken the closed-book and blind-review guarantees.
//
// Canonical execution:
//   1. writer_closed  — zero-tool, maxDepth:0 child (A/B jobs)
//   2. judge_blind    — zero-tool, micu/gpt-5.6-sol child (anonymous reviews)
//   3. analyst_stats  — aggregate-only child (restore A/B labels)
//
// See pipeline/NEXT_ROUND_HANDOFF.md and pipeline/RUNBOOK.md.
// Keep this file only to prevent a later operator from reviving the old soft
// workflow path by mistake.
