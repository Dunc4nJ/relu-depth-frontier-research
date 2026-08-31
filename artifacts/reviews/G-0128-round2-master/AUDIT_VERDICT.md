# G-0128 round-2 exact-Q master — T1 source audit verdict

- Review completed: `2026-08-31T03:41:26Z`
- Reviewer: `MagentaEagle` (Codex / GPT-5; fresh context, same model family, T1 only)
- Review preregistration: `artifacts/reviews/G-0128-round2-master/REVIEW_PREREGISTRATION.md`, commit `b6c3515`
- Frozen subject source: `artifacts/math/G-0128/full_family_master_v2.py`
- Subject commit: `e717dbee700374c01058ca8a5b32f972d000b25e`
- Subject SHA-256: `cfdb3f3d758d8cc5cc81c8ad9a71f4b9bd5c2001f1ff2f8a646715a4c6ca3da8`
- Audited ancestor SHA-256: `dc77467b31c12b40eaec8b33bbe806d0c6f2ea8e2dac3f2731324deb3c1b9cac`
- Custody: read-only toward the subject; no G-0128 manifest or scientific result existed or was inspected during this audit

## Verdict

`PASS` for source and manifest-builder implementation readiness at the narrow preregistered meanings, with **no current correctness blocker found** on the exact source SHA above.

This clearance permits building the one-shot manifest and, if every bound-input validator succeeds and the manifest names this exact source SHA, executing the preregistered master. It is not a verdict on a future scientific output. Any source edit invalidates this clearance and requires a diff audit plus the full hostile suite.

The only terminal meanings this source can support are:

- `FULL_FAMILY_380ROW_EXACT_Q_MEMBER`: exact membership of the fixed unscaled target on the frozen 380 rows in the span of the frozen 163,740 T1-family columns; only a candidate for a separately preregistered complete global replay.
- `FULL_FAMILY_380ROW_EXACT_Q_NONMEMBER`: an exact primitive integer separator on those same 380 rows that annihilates all 163,740 frozen columns and pairs nontrivially with the target; only a bounded obstruction for this frozen dictionary.

Neither branch establishes a global MAX11 identity, family completeness, an unrestricted lower bound, a Lean theorem, `REFEREED` standing, or T2 independence.

## Obligation-by-obligation adjudication

| Obligation | Verdict | Basis |
|---|---|---|
| Exact row system and provenance | PASS | `full_column` assembles exactly 301 panel, 11 linear, 4 accumulated, 32 old Batch32, then 32 new Batch32 coordinates. Typed old/new blocks bind separate selection and price receipts. The manifest records all 64 decisions in row order as `KEPT_CONSERVATIVELY`, with empty discarded and pivot-enrichment lists. |
| G-0126/G-0127 custody and directions | PASS | Complete expected inputs and executables are rehashed. Receipt schemas, exact key sets, binding maps, dimensions, selected order/digest, nonzero residues, and the G-0117 direction invariants (zero sum, first-positive orientation, primitive gcd, ordered-cone activity) are enforced. |
| New-row arithmetic bridges | PASS | All 32 rows recompute the 131-term exact candidate dot, require canonical equality to the matching nonzero G-0126 residual, ordered-prime reductions, per-row and aggregate hinge digests, extrema/nonzero censuses, and the frozen decimal-LF digest. All 11 linear dots are recomputed exactly, with coordinates 0–9 zero and coordinate 10 equal to `prior_scale * 11!`. |
| Warm seed and target | PASS | The 156 sorted unique prior selected/support sequences and 131-term projection are checked. Runtime reconstructs the first 348 coordinates, recomputes the signed-i128 basis digest, exact rank 156, and the old scaled identity; it then checks full-380 rank 156 and augmented rank 157. The target is rebuilt unscaled as 301 panel entries, ten zeros, `11!`, and 68 hinge zeros, and is serialized verbatim in the manifest. |
| Rank-growth loop | PASS | Iterations are exactly `0..224`. A separator violation is appended only if it is outside the selected set; the next iteration requires exact rank growth by one. Since the seed rank is 156 and there are 380 rows, the bound is sufficient without sampling or modular decisions. |
| Membership branch | PASS | Pivot columns and coordinate rows are extracted over exact FLINT rationals; the solve is replayed on all 380 rows before and after denominator clearing. Coefficients and scale are jointly primitive with positive scale, zero terms are removed, support positions remain aligned, the final basis digest is row-major/column-minor signed-i128, and a `+1` coefficient mutant must fail an actual row equation. |
| Nonmembership branch | PASS | A primitive first-positive integer left separator with independently checked nonzero target pairing is priced exactly over `range(163740)`. Only a null return after visiting the final column emits nonmembership with census 163,740. Loader errors propagate. A `+1` separator mutant must break annihilation or kill the target pairing. |
| Transcript and claim boundary | PASS | Every completed iteration records exact ranks, branch, separator fields, first violating sequence/price, and scan census. Both result strings explicitly refuse global identity, family completeness, unrestricted MAX11/lower-bound, and Lean implications. |
| Staleness, paths, and publication | PASS | Source, preregistration, prior artifacts, G-0126/G-0127 receipts, executables, and all transitive expected inputs are checked before work and rehashed before publication. Paths are contained, manifest inputs are canonical and unique, pre-existing outputs are refused early, JSON is pre-serialized, and same-directory exclusive-temp + fsync + no-overwrite hard-link publication cleans up on failure. |
| Hostile controls | PASS | The production document validators receive deep-copy mutations for prior seed/support/basis/terms/coefficients, G-0126 order/residuals, G-0127 bindings/order/duplication/streams/dots/source swap, warm arithmetic, manifest target/inputs/solver/pivot/provenance/seed, and ordered old/new blocks. The audited ancestor's 15 controls remain live. |

## Independent probes

1. `python -m py_compile`: PASS on the frozen source.
2. Subject self-test: PASS — ancestor 15 plus 48 G-0128 hostile mutations; independent run took 69.93 seconds and peaked at 962,480 KiB RSS.
3. Independent probe source: `artifacts/reviews/G-0128-round2-master/independent_probes.py`, SHA-256 `17997268c6790e9efe0458548c937ee7f609c6c6a12aa1fefca9d895060fd9b6`.
4. Probe receipt: `artifacts/reviews/G-0128-round2-master/INDEPENDENT_PROBE_RECEIPT.json`, SHA-256 `3f8b314d6cf49773f55f2e601dcfbd7be48cb8cddd4d6989b8228e60558dfc5c`, result `PASS`.
5. The independent battery cross-checked 400 random exact ranks, 230 target-separating primitive null vectors, 230 unit-rank-growth witnesses, and 250 exact member solves/normalizations/mutants against a separate `Fraction` eliminator. It additionally sent 201 coefficient/support permutations through terminal row arithmetic and rejected one exact non-unit rank-growth mutant.
6. Scan probes placed the only violation in the fifth and final column, completed a true five-column null scan, and confirmed a planted loader exception was propagated at index 3 rather than converted to success.
7. Target/order probes recovered exactly 380 target entries and 68 hinge rows; target decimal-LF SHA-256 was `dbd973914dc41f82d6404b21412762e5541f2be580b44d12f3caa5bf371b862d`.
8. Atomic probes rejected pre-existing output, serialization failure, temporary-write failure, link failure, and post-link directory-fsync failure without leaving the attempted final artifact.
9. Path/seed probes loaded the real production components and confirmed that the production prior-document validator rejects duplicate and out-of-range seeds. The production containment/uniqueness helpers also rejected a resolved duplicate introduced through a symlink and a symlink path escape.

## Preregistered hostile-probe traceability

| Preregistered probe family | Disposition |
|---|---|
| Validator reachability and ancestor/v2 semantic diff | Discharged by complete static source audit of the final 596-line revision diff and both manifest-build/run call paths; all terminal validators are reachable before their respective decisions. |
| Final-column/null scans and loader exception propagation | Discharged independently: final-only violation visited all five synthetic columns; true null visited all five; planted exception propagated at index 3. |
| Exact rank/member/nonmember cross-checks | Discharged independently by the 400/230/230/250-case battery; the non-unit rank mutant was rejected and 201 coefficient/support permutations failed terminal row arithmetic. |
| New-row order/content, G-0126/G-0127 bindings and digests | Discharged by production-validator self-test mutations covering order, truncation, duplication, direction/residue, exact residual, row and aggregate hinge digests, linear stream, extrema, nonzero census, binding maps, and old/new source swap. |
| Old/new concatenation and 348-row false member | Discharged by the production concatenation-order mutant and the retained ancestor false-member control whose omitted new coordinate is decisive. |
| Warm seed, basis, old witness, and target | Reorder, support mismatch, basis digest, term/coefficient/scale, target contamination, and coefficient/support permutation were discharged by the production self-test; duplicate and out-of-range seed mutations were independently routed through the actual prior-document validator. |
| Terminal member/separator mutants | Discharged by the subject's real all-row `+1` member replay and annihilation/pairing separator check, with independent member mutations also exercised in 250 cases. |
| Cache/shape, manifest paths/staleness, and atomic cleanup | Cache truncation, ragged columns, stale source/preregistration/manifest/receipt/input, and ordinary duplicate/path cases were discharged by subject/ancestor controls. Resolved-duplicate and symlink-escape cases were independently rejected. Five independent publication-failure probes covered pre-existence and serialization/write/link/fsync cleanup. |

## Audit yield and repair history

The review was not ceremonial. The first frozen draft accepted G-0126 selected directions without independently checking the kernel's semantic invariants. It also omitted an explicit manifest target and the empty pivot-enrichment record, used ambiguous new-row provenance, and advertised several tautological or absent hostile controls. Those issues blocked source clearance. Commits `1f44a60` and `e717dbe` repaired them in production paths and added must-fail controls that traverse the same validators used by manifest construction and runtime.

## Residual risks and next obligations

1. This is same-family T1 review only. It cannot promote a mathematical claim to `REFEREED` or `FORMALIZED`, and agreement among same-lineage agents is not T2.
2. Hashes and local Git attest exact local bytes; they are drift detection, not signatures or hostile multi-principal custody.
3. The audit validates the consumer and its exact bridges but does not clean-room rederive all 5,239,680 G-0127 hinge entries or prove the imported FLINT/kernel/toolchain correct. Those remain provenance and independent-replay obligations for evidence promotion.
4. Manifest creation must hard-stop on any validator failure. The generated manifest should be committed/hash-bound before the master is invoked, and its solver field must equal the cleared SHA above.
5. Whichever terminal branch appears requires a separate result-level audit: a member needs binding-clean complete global exact replay; a nonmember needs an independent all-163,740-column separator replay.
6. No Lean work is triggered by either bounded branch. Formalization is eligible only after a separately established, statement-matched global result.
