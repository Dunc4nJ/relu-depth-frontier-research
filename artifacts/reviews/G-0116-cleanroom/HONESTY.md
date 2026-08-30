# G-0116 clean-room review — anti-ceremony and honesty disposition

## Creation gate

- Boundary: this review is process; runtime does not branch on it.
- Consumer: the root research lead deciding whether to accept G-0116 and
  restart G-0113.
- Gate: acceptance of the evaluator and corrected 301-row scan.
- Observed defect: shared-code self-checking in G-0116 and the actually found
  G-0113 boundary-conjunction bug.
- Retirement: after the corrected scan is accepted/rejected; no further
  evaluator-review rounds without a new object-level discrepancy.
- Integrity exception: not invoked; the ordinary creation gate passes.
- Highest-priority ready capability: the MAX11 scan.  More audit time would
  now be lower value, so this audit stops.  Verdict: `LEGITIMATE_GATE`.

## Real-work audit

Window: this audit session.  Core purpose: decide the exact MAX11 finite-panel
seed without confusing finite computation with a global theorem.

- Tally: USER 0, ENABLER 2 (literal evaluator; caught/corrected scan predicate),
  PROCESS 2 (preregistration; verdict), UNKNOWN 0.
- Two-minute demo: the clean-room vector hashes match, while the adversarial
  review forced an invalid run to stop before output and planted a regression.
- Without the process records, acceptance would not be auditable; they gated
  the restart rather than standing in for it.
- The enablers ran on real frozen data and the actual scanner.
- The oldest user-relevant item is MAX11; this work unblocked its finite scan.
- This reviewer did not orchestrate closes; no close-count comparison applies.
- No plan/spec substitution or follow-up laundering occurred.
- Verdict: `HEALTHY`, with evaluator-review machinery now frozen.

## Honesty inventory

1. No test weakening (checked clean-room files and corrected G-0113 source).
2. No mock/fixture presented as live proof; frozen files are the subject.
3. No golden regeneration.
4. The reviewer edited neither G-0113 nor G-0116.  No bypass/tolerance/retry
   relaxation was added.  The pre-existing `allow(dead_code)` only supports
   the frozen include and was not semantic evidence.
5. No demo-path hardcoding or post-result denominator change; sequences 0 and
   3 and the 10x gate were frozen first.
6. **Yes:** G-0116 `cargo test` was a zero-test green.  It is disclosed,
   receives no correctness credit, and is replaced by live binary controls
   plus the literal route.  G-0113 ran 4/4 tests.
7. No unrun command is claimed (checked session outputs).
8. No proof-class inflation; T1 status and the post-hoc check are explicit.
9. **Yes, failures existed and were prominent:** the one-thread timing miss
   and G-0113 predicate bug were immediately sent to the lead; the run died.
10. No stderr was discarded.  One run redirected it to a file; the blank
    chained result was followed by printing the retained timing/error line.
11. No item was self-closed; this is not a MAX11 completion.
12. No requirement was edited to fit an outcome.
13. No tracker close was performed; this reviewer did not orchestrate closes.
14. No subagent was dispatched.
15. No report was accepted on trust: binaries, values, tests, clippy, hashes,
    abort paths, and refreeze were re-executed/read.
16. No refusal farming; the review built a semantic verifier and found a bug.
17. Same-origin agreement was not counted as independence.
18. No denominator was selected after results; the one-thread miss is carried.
19. The blank chained one-thread command is the only moment needing advance
    explanation; its retained stderr was immediately surfaced.
20. Strongest re-executable evidence: the byte-identical clean-room rerun and
    its two complete literal 301-entry hashes.

Disposition: the predicate defect was corrected by its owner, disclosed,
recorded `INVALID_ABORTED`, and guarded by a hostile regression.  The
zero-test, shared-code, and timing limitations remain visible.  No undisclosed
contrary result was found.
