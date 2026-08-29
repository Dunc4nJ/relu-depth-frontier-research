# STATUS — relu-depth-frontier-research

**The resume pointer.** A fresh session runs `./skill-runtime verify-quick`, reads
`RESEARCH_RUNBOOK.md`, then uses this file for orientation. Keep it short and current — never a place
where standing is asserted. Active queue object IDs are mechanically cross-checked; phase, round,
commit, counts, and the last displayed verifier result are operator-maintained summaries. Reconcile
them against ledger, `phases/ROUNDS.md`, and Git before acting.

## Where the campaign is
- Phase: P4 · Round: R-0001 · Commit anchor: `4714b1e` (R-0001 parent)
- Ledger: 8 claims · 6 open gaps · 3 active routes · 0 dead ends · verify-ledger: green
- Clean-pass streak (P10 only): 0

## Next work queue (dual-written to `beads/QUEUE.md`)
1. EXP-0002 — fresh-context Stage A clean-room verifier implementation; no registered-subject runs before lead review.
2. G-0004 — reconstruct and statement-match the complete skip-free indexed compiler.

`walk-consistency` compares the object-ID set on the real numbered lines above with the set on real
unchecked lines in `beads/QUEUE.md`. Brace-slot lines are ignored line by line while this template is
being filled; a missing counterpart is reported as INFO. Once real work exists, both files must name
exactly the same active IDs.

## Open blockers
None for Stage A. T2 review remains unavailable and caps later promotion; it does not block T1 implementation or falsification work.

## Standing reminders for the resuming agent
- Do not re-derive settled state; challenge it through the ledger if it looks wrong.
- Interrupted reviews are recorded with `verdict = "cannot-verify"` and residual_doubts noting the
  interruption; they NEVER count toward any clean bar, whatever their harvested findings show.
