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
- [ ] H-0001 Build a split-6 exact pricing oracle for cross-component columns and seek a new dual for the enlarged family. (claimed-by: research-lead/crimsonbirch)
- [ ] G-0007 Obtain a genuinely different-family or human review of the frozen bounded theorem bundle. (claimed-by: unclaimed)
