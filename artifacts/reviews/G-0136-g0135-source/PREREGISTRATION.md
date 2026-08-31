# G-0136 preregistration — outcome-blind source audit of G-0135 Stage A

## Subject and blindness

Audit the future committed G-0135 exact Batch32 replay/selection producer,
Cargo manifest, lockfile, and release executable before its scientific manifest
or output exists.  The reviewer must not run the full G-0135 scientific replay
and must record `scientific_manifest_observed=false` and
`scientific_output_observed=false`.

The audit may inspect the already-public G-0132 residual because G-0135 is an
outcome-aware continuation.  It must not know the other 31 selected directions
or coefficients, which do not yet exist.

## Required source verdict

Return `PASS` only if independent inspection and probes establish all of the
following for the exact committed source and executable:

1. The G-0128 176-slot member is projected to exactly 132 nonzero terms without
   changing sequence/coefficient correspondence.
2. Every scientific sum, product, target subtraction, residual comparison, and
   selected coefficient uses arbitrary-precision signed integers.  Any bounded
   integer arithmetic is independently bounded and cannot decide the result.
3. Each term enumerates its complete labelled `S_11` orbit with exact inactive
   multiplicity and reconciles generated, visited, accepted, skipped, failed,
   and unclassified counts.
4. The aggregate is required to reproduce G-0132's census, support, nonzero
   count, exact stream digests, first direction, and first coefficient before
   selecting anything.
5. Selection is exactly the first 32 nonzero primitive active hinge directions
   in signed-`i8` tuple lexicographic order.  No modulus, magnitude, rank,
   sparsity, or dependency filter affects admission.
6. The two selection digests implement exactly the preregistered byte streams:
   11 signed bytes per direction, and canonical signed decimal plus LF per
   coefficient.
7. All 68 accumulated directions and all 11 linear residuals must be exactly
   zero; duplicates, noncanonical decimals, fewer than 32 rows, or any mismatch
   fail closed.
8. Candidate, preregistration, prior replay, kernel, transitive inputs, source,
   executable, source-audit receipt, Git ancestry, and end-of-run bindings are
   checked; output publication is atomic and no-overwrite.
9. Positive known-answer and hostile mutants can both pass/fail as intended,
   including coefficient, direction order, omitted contribution, census, and
   digest mutations.

## Independent probe

Write a fresh probe rather than importing the producer.  It must at minimum:

- rederive and check every direct/transitive path and SHA binding;
- check the source structurally for exact aggregate, signed-lexicographic
  Batch32, no modular admission, and end rehash/publication guards;
- independently exercise direction-byte and decimal-LF digest semantics;
- independently compare the exact/pinned kernels on planted and near-frontier
  records, including a must-fail mutant;
- run producer `--self-test` and preflight failure cases without producing a
  scientific manifest or output.

Publish:

- `SOURCE_AUDIT_REPORT.md`
- `SELF_TEST_RECEIPT.json`
- `independent_probe.py`
- `INDEPENDENT_PROBE_RECEIPT.json`
- `SOURCE_AUDIT_RECEIPT.json`

The final receipt schema is `max11-g0136-g0135-source-audit-v1`; its subject
binds the committed source, Cargo files, and executable; its `frozen_inputs`
matches the producer's complete input set; both self-test and independent probe
are `PASS`; all audit artifacts are hashed; and its promotion boundary is:

> T1 source clearance for this exact committed producer and executable only;
> no scientific manifest or output was observed, and no mathematical result is
> promoted by this receipt.

Any unresolved arithmetic, selection, custody, or completeness defect is
`FAIL`.  This audit cannot promote a residual, identity, family obstruction, or
Lean theorem.
