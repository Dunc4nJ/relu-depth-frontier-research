# G-0138 preregistration — outcome-blind source audit of G-0135 Stage D

## Subject and blindness

Audit the future committed conditional Stage-D global replay producer before
Stage A, B, or C has emitted any scientific manifest, residual batch,
coordinate pack, or 412-row result.  The Stage-C candidate does not yet exist.
The reviewer must not create it or run a complete scientific replay.

## Required verdict

Return `PASS` only if independent source inspection and probes establish:

1. The producer admits only an exact-Q member from the frozen 412-row Stage-C
   protocol, validates its complete selected/support axes, primitive integer
   coefficients and target scale, and independently replays all 412 finite rows.
2. Every nonzero term receives a complete labelled `S_11` ordered-chamber
   normal form.  The term count is variable but the exact census must equal
   `terms * 11!`; every per-term generated/visited/accepted count closes, with
   zero skipped, failed, or unclassified contributions.
3. Scientific coefficients, products, target subtraction, residual aggregation,
   comparisons, and terminal decisions use signed arbitrary-precision integers.
   Any bounded kernel is independently bounded and diagnostic only.
4. All 100 accumulated hinge directions (the prior 68 plus Stage A's 32) are
   recomputed by an independent exact coordinate route and required to be zero.
   All 11 linear residuals are exact after one subtraction of
   `target_scale * 11!` at the pinned target coordinate.
5. The complete hinge union—not merely accumulated rows—is aggregated.  Exact
   global zero is selected iff every hinge and linear coefficient is zero.
6. On residual, selection is exactly the first 32 nonzero primitive active hinge
   directions in signed-`i8` tuple lexicographic order, with the preregistered
   signed-byte and canonical-decimal-LF digests.  No modulus, magnitude, rank,
   or sparsity criterion influences selection.
7. Coefficient-plus-one, target-scale/coordinate, omitted-term/orbit/direction,
   census, direction-order, and digest mutants fail; planted exact-zero and
   nonzero fixtures take the correct terminals.
8. Shared manifest, Stage A/B/C receipts, sources, audits, candidate, kernel,
   executable, Git ancestry, and all transitive inputs are bound at entry and
   exit.  Publication is atomic and no-overwrite.

## Independent probe and artifacts

Write a fresh probe that does not import the producer.  It must independently
exercise exact normal-form/direction pricing on planted records, variable-term
census arithmetic, exact zero/nonzero aggregation, signed tuple ordering and
both digest streams, plus must-fail candidate, target, omission, and custody
mutants.  Run only self-tests/preflights incapable of scientific output.

Publish a report, self-test receipt, independent probe source/receipt, and a
source-audit receipt under this directory.  Bind the exact committed source,
dependencies, and release executable; record
`scientific_manifest_observed=false` and `scientific_output_observed=false`.

This is T1 source clearance only.  It cannot promote a future Stage-C member,
global identity, residual, frozen-family conclusion, unrestricted MAX11 result,
or Lean theorem.  Any unresolved candidate-admission, completeness, arithmetic,
terminal, or custody defect is `FAIL`.
