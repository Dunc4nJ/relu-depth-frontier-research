# QUEUE — relu-depth-frontier-research

The campaign's native work queue. Dual-written with `STATUS.md` at every round close; the two must
agree (walk-consistency checks). Format — one line per item, newest appended last:

```
- [ ] <object-id> <one-line work item> (claimed-by: <role/instance>|unclaimed)
- [x] <object-id> <one-line work item> (done: R-####)
```

Rules: items reference ledger objects by ID (a queue line with no object ID is a vibe, not work);
completion marks the round that did it; lines are never deleted — a dead item is checked off with
`(dropped: reason)`. An external beads-style work tracker MAY mirror this file when one is
available in the environment; this file remains canonical and the package requires no such tool.

`walk-consistency` checks only real `- [ ]` lines outside fenced examples. Every such line must carry
an ID that exists in the canonical ledger, and their object-ID set must exactly equal the real numbered
items under `STATUS.md`'s `Next work queue`. Checked lines are history, not active work. A line containing
a `{BRACE_SLOT}` is ignored line by line until filled; a missing STATUS or QUEUE file is INFO because a
partial/non-campaign workspace may not yet have both, but disagreement when both exist is SE-15.

- [x] EXP-0002 Fresh-context Stage A clean-room verifier implementation. (dropped: superseded as the active priority by the direct bounded MAX11 theorem campaign; experiment remains planned)
- [x] G-0004 Reconstruct and statement-match the complete skip-free indexed compiler. (dropped: deprioritized after the bounded theorem; gap remains open)
- [x] H-0001 Build a split-6 exact pricing oracle for cross-component columns and seek a new dual for the enlarged family. (dropped: superseded on the critical path by the exact full-core signed-mass-four gate; route H-0001 remains active)
- [x] G-0007 Obtain a genuinely different-family or human review of the frozen bounded theorem bundle. (dropped: still open but not on the active mathematical critical path)
- [x] G-0008 Run the exact lower-degree quotient gate on all 526 zero-high natural lifts, exact-replay any potent kernel, and independently replay the natural high-degree sketch deficiency. (dropped: superseded on the critical path by the exact G-0078 separator and broad degree-five pricing discriminator; gap remains open)
- [ ] G-0006 Prove a completeness bridge for the finite pair-orbit ansatz or find an asymmetric escape relevant to unrestricted MAX11. (claimed-by: research-lead/crimsonbirch)
- [x] EXP-0008 Execute the preregistered resumable natural-lift census and one-sided nonzero-high rank gate over all 11,542 genuine columns. (completed: exact 526/11,016 partition; sketch rank 6,626 is deficient and strictly inconclusive pending complete-row replay)
- [x] G-0009 Exact-price the complete loop-inclusive degree-five universe with the new 230-row separator and target-aware solve the nonzero-price extension. (dropped: retained as a broad fallback after the smaller complete same-component Y-spoke closure; gap remains open)
- [ ] G-0011 Exact-price all 18,582 same-component Y-spoke orbits, run capped target-aware quotient CEGIS on the piercing columns, and exact-lift the resulting member or separator. (claimed-by: research-lead/crimsonbirch)
