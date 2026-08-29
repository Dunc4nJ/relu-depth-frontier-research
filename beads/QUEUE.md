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

- [ ] {OBJECT_ID} {FIRST_WORK_ITEM} (claimed-by: unclaimed)
