# G-0113e invalid/aborted scan record — boundary-agreement mismatch

The first production invocation of the scanner frozen at source SHA-256
`89ee08b1b6def2a07b351e6f5a7ba6a8d8819f94d8127fbd9169beb9fdf7e8f8`
was explicitly stopped after clean-room review found a preregistration mismatch.

The source computed the two global report booleans from union ranks and union
target decisions only.  The preregistration requires p1/p2 agreement at both
the DISJOINT boundary and the union boundary.  A later union agreement therefore
could have hidden a DISJOINT-stage disagreement.  The evaluator and per-prime
rank states were not implicated, but the reporting/validity predicate was too
weak, so the entire invocation is classified `INVALID_ABORTED`.

## Interrupted invocation

- solver PID: `3221715` (`/usr/bin/time` wrapper PID `3221683`);
- elapsed time at SIGINT: `3:21.91`;
- user/system CPU: `246.26s` / `8.17s`;
- maximum RSS: `100,276 KiB`;
- last emitted checkpoint: none (the first checkpoint was frozen at 5,000
  records);
- observed ranks or target decisions: none;
- `panel_scan_v1.json`: absent;
- `panel_retained_columns_v1.json`: absent.

No partial artifact or scientific outcome from this invocation is retained.
The corrected source must conjunct agreement at both boundaries, expose all
four boundary-specific booleans, pass a planted stage-disagree/final-agree
regression, be re-frozen under a new hash, and restart from record zero.
