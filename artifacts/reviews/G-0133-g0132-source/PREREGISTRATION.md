# G-0133 preregistration — T1 source audit of the G-0132 MEMBER replay

## Freeze and prospective boundary

- Registered: `2026-08-31T04:08:57Z`.
- Reviewer: `ProudMink` (Codex / GPT-5; fresh context, same model lineage; T1 only).
- Campaign: mathematics, W1 prove/refute. This is a read-only source/readiness audit, not a result audit or proof campaign.
- During registration, the path names `artifacts/math/G-0132/Cargo.toml` and `artifacts/math/G-0132/src/main.rs` appeared as untracked draft files. The reviewer observed those names but did **not** open, hash, parse, diff, compile, execute, or inspect their bytes. No frozen source SHA/commit, executable, G-0132 manifest, or G-0132 scientific output existed or was observed. Thus this document does not claim to predate draft creation; its valid prospective boundary is before source freeze and before reviewer source inspection.
- The reviewer will not edit the producer. Only the exact future source SHA and commit explicitly released by the orchestrator are admissible.
- No G-0132 manifest may be created and no G-0132 scientific or control run may begin before a committed G-0133 `PASS` receipt for that exact source SHA. Audit activity is limited to syntax/build checks, self-tests, and independent synthetic hostile probes that cannot emit a scientific outcome.

## Frozen anchors

```text
6db51f8716d0ba0a82606bddc7573dafd889f2fe  G-0132 preregistration commit
73ccd2ce2a96c0d46b0a40166ca6a84050577cdba3f23ff12d1b89e043e8c692  artifacts/math/G-0132/PREREGISTRATION.md

b5b73a1b6ffec75ca2c54a31bf2ebb62ec9dbf0c  G-0128 result commit
17c4fd5c8890006feaf5b9b9d6dbd542002dfca80e85b27b2dcacec16ebca838  artifacts/math/G-0128/full_family_master_result_v2.json

0f384376dde61e025e1978c3f5102c951396aef5  G-0131 audit-preregistration commit
74594f4a88a840dd144b69d154a7b77445d13b20ff55630e9b5d932253e1d799  artifacts/reviews/G-0131-g0128-result/PREREGISTRATION.md

2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6  artifacts/math/G-0117/src/lib.rs
39de1eb61aaee37a24c8a45d55cbc5fd6f27c7b68d506f8757f352881a6e0c17  artifacts/math/G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md
```

The future G-0131 admission receipt is fixed at
`artifacts/reviews/G-0131-g0128-result/cleanroom_member_audit_v1.json`, schema
`max11-g0131-cleanroom-380row-member-audit-v1`. Its exact SHA and commit will be
recorded only after orchestrator release. Admission requires, without
reinterpretation: `verdict == CONSISTENT_MEMBER`,
`mathematical_certificate_verdict == CONSISTENT`, all 380 rows and the
coordinate-square solve exactly zero, the hostile mutant rejected, the selected
basis matched, primitive positive normalization, dimensions
`rows=380`, `records=163740`, `selected_columns=176`, and 21 exact rank receipts
ending at `rank=augmented_rank=176`. `INCONSISTENT`, `CANNOT_VERIFY`, drift, an
unknown schema, or a different branch blocks G-0133 `PASS`.

## Exact audit question and claim boundary

Does the eventual frozen G-0132 source implement the preregistered MEMBER arm
as a complete arbitrary-precision ordered-chamber normal-form replay of the
exact G-0128 member, fail closed under every named corruption, and make a
scientific decision only after complete exact aggregation?

The strongest clearance is implementation readiness for the frozen orbit
identity

```text
sum_s a_s F_s(x) = L * 11! * max(x_0,...,x_10).
```

Even exact zero establishes only that frozen global orbit identity through the
pinned normal-form uniqueness/symmetry seam. It does not by itself establish a
compiled two-hidden-layer network, family completeness, the all-`n` target, an
unrestricted lower bound, `REFEREED` standing, or a Lean theorem.

## Source-clearance obligations

1. **Custody and admission.** Strictly rehash the G-0132 preregistration, the G-0128 result and its transitive bindings, both G-0117 kernel/uniqueness inputs, the committed G-0131 receipt/report, Cargo files, source, embedded source/kernel/lemma bytes, and executable. Reject missing/extra/duplicate/resolved-duplicate inputs, path or symlink escape, stale executable, source/input drift, unknown fields, malformed/noncanonical integers, and any branch except `FULL_FAMILY_380ROW_EXACT_Q_MEMBER`.
2. **Exact projection.** Require 176 unique, strictly increasing, in-range selected/support slots; exact equality of those two lists; exactly 176 integer coefficient slots with exactly 44 zeros; and exactly 132 nonzero `terms`. Reconstruct the 132-term list as the order-preserving nonzero projection of `(selected_sequence, integer_coefficient)` and require exact sequence/coefficient equality and canonical digests. Require positive primitive `target_scale` and no hidden zero, duplicate, reorder, or omitted final term.
3. **Complete orbit census.** Reconstruct each term from its frozen family record, never from cached 380-row columns. Visit exactly `132 * 11! = 5,269,017,600` labelled permutation contributions, including the last contribution of the last term; duplicates induced by stabilizers still count. Generated, visited, accepted, inactive, and failed totals and per-term digests must reconcile with zero skipped/unclassified/failed contributions.
4. **Complete normal form.** Apply the pinned zero-sum, gcd-one, first-positive, active-prefix direction rules and exact branch/orientation linear correction. Accumulate every dynamically encountered primitive active direction, not merely a sampled/support list or the 68 prior rows, and all 11 linear coordinates. Independently require the exact ordered list/digest and replay value of all 68 prior G-0128 hinge directions.
5. **Unconditional exact terminal path.** Every coefficient product, hinge sum, linear sum, cancellation, and decision is a signed arbitrary-precision integer operation. Modular screens may be diagnostic only: the unconditional exact pass still traverses the full census and alone determines the terminal enum. Floating point, tolerance, fixed-width overflow, modular equality, or a sampled direction set can never decide.
6. **Target and terminal semantics.** After complete orbit aggregation, subtract exactly `L*11!` once from linear coordinate 10 and nothing from coordinates 0--9 or any hinge. `MEMBER_EXACT_GLOBAL_NORMAL_FORM_ZERO` is reachable only when the complete census and all bindings pass, the exact zero-pruned hinge map is empty, and all 11 linear residuals are zero. Otherwise, after completing the census, emit `MEMBER_EXACT_GLOBAL_NORMAL_FORM_RESIDUAL` with the lexicographically first canonical nonzero hinge/coefficient, or the first nonzero linear index/value if all hinges vanish. Exceptions, resource failures, serialization failures, or incomplete counts are errors, never scientific outcomes.
7. **Atomic custody.** Refuse a pre-existing manifest or either branch output. Pre-serialize in memory; publish through an exclusively created same-directory temporary, flush/fsync, no-overwrite atomic link, and directory fsync; rehash source, executable, preregistration, result, G-0131 receipt, kernel/lemma, Cargo, and all inputs immediately before publication. Any failure leaves no final path, and the unselected NONMEMBER output remains absent.

## Precommitted hostile probes

`PASS` requires static reachability review plus source self-tests and an
independently written probe harness that force rejection/detection for:

- `+1` to the first nonzero coefficient, `target_scale`, target coordinate 10, and the last nonzero term; omission/reorder of the last support slot or term;
- omission of the final labelled orbit contribution, orbit relabelling/branch swap, and a final-only orbit discrepancy;
- direction sign, gcd, active-prefix, deduplication, or omitted-direction corruption;
- omitted/swapped linear coordinate, linear-orientation correction, and exact target-subtraction corruption;
- a planted nonzero residual divisible by every configured screening prime, which must survive all modular screens and be found by the unconditional exact pass;
- mutation/omission/reorder of one of the 68 prior directions and disagreement between prior-row replay and the complete aggregate;
- frozen source, embedded source, executable, Cargo, G-0132 preregistration, G-0128 result/inputs, G-0131 receipt/report, kernel, and uniqueness-lemma drift;
- pre-existing output plus serialization, temporary-write, link, and post-link fsync failures, all without overwrite or false success.

At least one exact-zero fixture and the planted G-0117 nonzero normal-form
fixture must pass by two routes. Mutants must traverse the same validators and
terminal decision functions used by the future run; digest-only decorations do
not discharge them.

## Verdict, receipt, and stop rule

- `PASS`: every obligation is reachable on one exact frozen source SHA and every hostile probe behaves in the precommitted direction.
- `FAIL`: a reachable scientific false positive, incomplete exact path, admission bypass, or custody/atomicity defect.
- `INCONCLUSIVE`: missing frozen evidence or resources prevent a required audit obligation.

The committed machine-readable receipt will be
`artifacts/reviews/G-0133-g0132-source/SOURCE_AUDIT_RECEIPT.json`, schema
`max11-g0133-g0132-source-audit-receipt-v1`. It will bind the subject source
path/SHA/commit, Cargo and executable hashes, all frozen inputs including the
future G-0131 receipt, verdict, self-test command/status/receipt hash, every
audit artifact path/hash, `scientific_manifest_observed=false`,
`scientific_output_observed=false`, and the T1 promotion boundary. Only exact
`verdict == PASS` for the exact admitted source SHA authorizes later manifest
creation or any G-0132 run. Any source edit invalidates clearance and requires
a new audit; the reviewer stops after source clearance and does not inspect or
run the later scientific output.
