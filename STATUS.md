# STATUS — relu-depth-frontier-research

**The resume pointer.** A fresh session runs `./skill-runtime verify-quick`, reads
`RESEARCH_RUNBOOK.md`, then uses this file for orientation. Keep it short and current — never a place
where standing is asserted. Active queue object IDs are mechanically cross-checked; phase, round,
commit, counts, and the last displayed verifier result are operator-maintained summaries. Reconcile
them against ledger, `phases/ROUNDS.md`, and Git before acting.

## Where the campaign is
- Phase: {P#} · Round: {R-####} · Last commit: {SHORT_SHA}
- Ledger: {N} claims · {N} open gaps · {N} active routes · {N} dead ends · verify-ledger: {green|red}
- Clean-pass streak (P10 only): {N}

## Next work queue (dual-written to `beads/QUEUE.md`)
1. {NEXT_DISCRIMINATING_WORK_ITEM — object ID + one line}
2. {…}

`walk-consistency` compares the object-ID set on the real numbered lines above with the set on real
unchecked lines in `beads/QUEUE.md`. Brace-slot lines are ignored line by line while this template is
being filled; a missing counterpart is reported as INFO. Once real work exists, both files must name
exactly the same active IDs.

## Open blockers
{NONE | the exact missing thing and the cheapest resolving step — vague uncertainty is not a blocker}

## Standing reminders for the resuming agent
- Do not re-derive settled state; challenge it through the ledger if it looks wrong.
- Interrupted reviews are recorded with `verdict = "cannot-verify"` and residual_doubts noting the
  interruption; they NEVER count toward any clean bar, whatever their harvested findings show.
