# G-0171 preregistration: G-0168 exact first-row Schur rank-gate source/custody audit

## Registration, seal, and decision rule

- Auditor: Agent Mail identity `IcyBeaver`; program `codex`; model `GPT-5 Codex`.
- Audit class: fresh-context, same-lineage, outcome-blind source/custody audit.
- Evidence ceiling: `T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT`.
- Frozen scientific preregistration: commit
  `982efb2d78a7c8ca886efb9f81fa563024bdc4c1`, path
  `artifacts/math/G-0168/PREREGISTRATION.md`, SHA-256
  `335b82ad402ca0ccc9ca6b0124fd4f1cc133bb2d6854912a326f4e142d11b11b`.
- The commit-object bytes at that path were read and independently rehashed before this document
  was written; the digest matched exactly.
- No G-0168 producer source existed in the frozen commit. Before sealing this document, the
  auditor did not inspect any producer candidate, scientific manifest, scientific input, output,
  rank result, provisional rank outcome, or G-0169 message.
- This preregistration must be committed and pushed to `origin/master`, and its remote commit and
  byte hash recorded, before the auditor may receive or inspect the frozen producer source.
- A later `PASS` is permitted only if every exact check named below is supported against the
  subsequently supplied frozen source commit and bytes. Uncertainty, an unexercised branch, an
  unparseable artifact, or a custody mismatch produces no `PASS`.
- The audit is read-only toward the subject. The auditor may not repair, weaken, or replace the
  frozen source. A needed repair requires a new source freeze and a new audit subject.

This process artifact has one consumer and one gate: the G-0171 coordinator and the producer's
pre-run audit-receipt validator must both refuse the scientific run without it. It retires as the
active rubric after the source-bound G-0171 verdict is issued; it remains immutable only as
provenance.

## Exact audit question and no-claim boundary

The later audit asks only whether the exact frozen producer bytes implement the frozen G-0168
Stage-A first-row protocol as a deterministic, exact, fail-closed, custody-preserving program. It
does not ask which scientific branch is true.

Exact claim boundary for a passing receipt:

> Source/custody clearance for the exact frozen G-0168 first-row Schur rank-gate producer bytes
> only; no scientific manifest, bound scientific input, scientific output, or rank outcome was
> inspected or created, and no outcome-bearing producer mode was run.

Exact no-claim statement:

> This audit does not establish either G-0168 scientific branch, rank 350, incompatibility of the
> frozen 541-row system, a Fresh128 correction, family completeness, an unrestricted depth lower
> bound, minimality, an all-n theorem, refereed status, formalization, or a Lean theorem.

## Outcome-blind observation and execution boundary

After the source freeze is supplied, the auditor may inspect only the exact named source/build
bindings at that commit. Scientific input and output paths remain unopened. The only permitted
producer executions are synthetic `--self-test` and non-scientific `--preflight-static`, plus
language-level parse, format, lint, compile, and locked test/build commands that cannot load a
scientific input. Synthetic fixtures must live outside scientific paths and use invented small
matrices.

The auditor must not invoke a default mode, `--freeze-manifest`, `--preflight`, `--run`, resume,
scan, price, solve, or any alias or environment-variable route that can read a scientific binding
or reveal a branch. Filesystem-open/create and subprocess traces must confirm the boundary. Any
unexpected scientific access, output creation, or rank-bearing stdout/stderr contaminates the
audit and forces `FAIL` with no receipt.

The eventual receipt flags `scientific_manifest_observed`, `scientific_input_observed`,
`scientific_output_observed`, `scientific_run_executed`, and `rank_outcome_observed` must all be
strict JSON `false`.

## Frozen binding and custody contract

The later receipt must bind the supplied source freeze, not the auditor's working copy by name:

1. Resolve the supplied 40-hex commit object and every named source/build path directly from Git.
2. Recompute lowercase SHA-256 from the commit-object bytes, then require byte identity among the
   declared hash, Git blob, isolated audit copy, and any bytes compiled or executed.
3. Enumerate the complete transitive build surface. Source modules, package/lock manifests,
   generated inclusions, build scripts, local dependencies, and a frozen executable if one is
   supplied are bindings, not ambient context. An unbound executable byte is a failure.
4. Require unique canonical repository-relative paths, unique binding names, regular files, no
   symlinks or path traversal, and no displaced recursive lookalikes. Extra, missing, duplicate,
   or substituted bindings fail closed.
5. Bind the exact frozen G-0168 preregistration tuple above and every upstream certificate,
   basis/row/column list, canonical-family definition, hinge row, member, target, scale, and bridge
   artifact used by the scientific program through a committed pre-run manifest. Expected hashes
   may not be learned from the same bytes they purport to authenticate.
6. The source must require this audit receipt at the exact path and schema fixed below. The later
   scientific manifest must bind the committed receipt bytes by path, commit, and SHA-256; a
   self-referential receipt commit is forbidden.
7. Compilation, self-test, and static preflight may not mutate any bound source, input, receipt,
   or canonical campaign artifact.

Local Git and SHA-256 provide exact local byte binding and ordinary-drift detection. They are not
signatures, external custody, hostile same-user tamper resistance, or mathematical verification.

## Closed parsing and envelope requirements

Every producer-consumed JSON document and every published JSON document must be parsed as one
UTF-8 JSON object under a closed schema. The same production parser must reject:

- duplicate keys at every nesting depth, unknown or missing keys, trailing JSON values, a BOM,
  malformed UTF-8, and non-object top levels;
- wrong JSON types, including integers substituted for booleans and booleans substituted for
  integers; floating-point, exponent, `NaN`, or infinity encodings in exact-number fields;
- noncanonical integers (`+1`, `01`, `-0`), out-of-range indices, empty required arrays, duplicate
  row/column/sequence identifiers, and inconsistent counts;
- absolute paths, dot segments, path escapes, symlinks, non-regular files, substituted paths or
  hashes, duplicate binding occurrences, and unknown binding names;
- any branch token outside
  `FIRST_ROW_EXACT_RANK_GROWTH`,
  `FIRST_ROW_EXACT_INCOMPATIBLE_DEPENDENCY`, and
  `INVALID_NO_SCIENTIFIC_RESULT`.

All dimensions, sequence identifiers, row identifiers, and digests are checked before arithmetic.
Parsing a report that says a check passed is not the check. The validator must consume the live
artifact and recompute its bindings.

## Exact mathematical reconstruction contract

The source audit must establish the following code path statically and through invented positive
and hostile fixtures. These are acceptance criteria, not observed properties of any as-yet unseen
source.

### 1. Canonical family, basis, and square

Let `A` be the frozen `540 x 163740` integer matrix, `B` the frozen ordered 349 basis-sequence
identifiers, and `R` the frozen ordered 349 coordinate-row identifiers.

- Reconstruct the canonical family census and sequence order exactly: 163,740 unique records,
  neither sorted under a replacement key nor sampled, sharded, resumed, or truncated.
- Reconstruct all 349 basis columns as the exact integer matrix `A[:,B]` of shape `540 x 349` by
  the bound canonical kernel. Do not trust a same-run cache as its own certificate.
- Require the upstream frozen basis-column, coordinate-row, full-basis, and square serialization
  digests before using them. Serialization and order are the upstream certified ones; the producer
  may not invent a new self-authenticating digest convention.
- Form `S = A[R,B]` in the frozen `R` and `B` orders, require exact shape `349 x 349`, and compute
  `det(S) != 0` over arbitrary-precision integers. A changed order, duplicate index, out-of-range
  index, singular square, or digest mismatch is invalid.
- Bind the upstream exact statement `rank_Q(A) = 349`; do not infer it merely from a filename or
  from the producer's own reconstruction.

Every scanned `A[R,j]` and every full column used in a replay must come from the same canonical
record-to-column implementation as the reconstructed basis, with sequence identity checked before
position.

### 2. Exact transposed solve and canonical denominator clearing

Parse the canonical integer row `h` with exactly 163,740 entries and align `h[B]` by the frozen
sequence identities. Solve, without floating point or tolerance,

`S^T lambda = h[B]` over `Q`.

Multiply back in exact arithmetic and require all 349 equalities. Define `d` as the least positive
common denominator of the reduced coordinates of `lambda`, and define `z = d lambda` in `Z^349`.
The producer must require

- `d > 0`;
- `S^T z = d h[B]` exactly; and
- `gcd(d, z_1, ..., z_349) = 1`.

A rescaled, sign-flipped, nonprimitive, nonminimal, or multiply-back-failing `(z,d)` is rejected.
All integer products and sums are arbitrary precision.

### 3. Canonical first reduced-price scan

For canonical sequence index `j = 0, ..., 163739`, reconstruct `A[R,j]` and compute the exact
integer numerator

`N_j = d h_j - z^T A[R,j] = d Delta_j`.

The source may stop only at the first exact `N_j != 0`. Every earlier numerator must have been
computed as exact zero by the unchanged path. A fixed-prime screen may schedule an exact check, but
modular nonzero is never a witness and modular zero never licenses skipping the exact integer
calculation. The output must bind the visited count, first sequence identity when present, and a
canonical transcript/census digest sufficient to detect omission, duplication, reordering, or a
late-column truncation.

### 4. Rank-growth branch: exact 350-minor and null-vector replay

If the first exact nonzero is at `j`, require `j` not in `B` and build, in the stated order,

`M_j = [[S, A[R,j]], [h[B]^T, h_j]]`.

The producer must compute `det(M_j)` exactly and independently verify

`d det(M_j) = det(S) N_j != 0`.

This is the explicit 350-minor certificate. Together with the frozen `rank_Q(A)=349` and one
appended row, it supports exactly rank 350 for the frozen first-row system.

It must also solve `S q = A[R,j]` exactly, clear denominators canonically, and construct a primitive
sparse integer vector `v` supported on `B union {j}` with positive `j` coefficient. Reconstruct the
needed full columns and replay, independently of the coordinate-row check,

- `A v = 0` on all 540 rows; and
- `h v != 0`, with exact agreement to the reduced-price certificate.

Any determinant, identity, support, primitivity, full-row null replay, or hinge replay failure is
`INVALID_NO_SCIENTIFIC_RESULT`, never rank growth.

### 5. Full-scan dependency branch: separator and target bridge

This branch is eligible only after exactly 163,740 exact numerators have all equaled zero. Extend
`z` to `w in Z^540` by placing its coordinates at the ordered rows `R` and zero elsewhere. Replay
on every canonical column

`w^T A - d h = 0`.

Require `(w,-d)` primitive with `d > 0`. Parse the exact frozen 540-entry target `b`, the primitive
integer G-0164 member `c`, positive scale `s`, and nonzero residual `r`; require their exact frozen
identity/census bindings. Recompute rather than inherit by label:

- `A c = s b` on all 540 rows;
- `h c = r`;
- `tau = w^T b != 0`; and
- `d r = s tau` exactly.

Then and only then `(w,-d)` is an exact left-null separator of `[A;h]` from target `[b;0]`. A single
nonzero scan numerator, missing column, zero `tau`, member replay failure, residual mismatch, or
bridge sign/scale mismatch invalidates this branch.

## Branch-total decision table

| Exhaustive condition | Sole permitted scientific result |
|---|---|
| The first canonical exact numerator is nonzero and the 350-minor plus 540-row null-vector certificates both replay | `FIRST_ROW_EXACT_RANK_GROWTH` |
| All 163,740 canonical exact numerators are zero and the primitive dependency, separator, member replay, nonzero target pairing, and bridge all replay | `FIRST_ROW_EXACT_INCOMPATIBLE_DEPENDENCY` |
| Any other state, exception, parse error, mismatch, mutation, drift, partial scan, or failed replay | `INVALID_NO_SCIENTIFIC_RESULT` |

There is no scientific `UNKNOWN`, approximate, probable, modular, cached, partial, retry, or
best-effort branch. An invalid run may publish a bounded diagnostic failure receipt, but it may not
publish or preserve an outcome-bearing scientific manifest.

## Mutation, potency, and anti-laundering controls

The unchanged production validation path must pass invented fixtures for both scientific branches
and reject, at minimum, the following one-at-a-time mutations:

1. missing, extra, duplicate, mistyped, or trailing JSON fields at every envelope level;
2. every source/audit/input binding path and hash substitution, a displaced correct decoy, a
   duplicate occurrence, a symlink, and an unbound transitive source;
3. a changed, reordered, duplicated, or out-of-range `B` or `R` entry; one altered basis entry;
   a stored-basis or square digest mutation; and a singular `S`;
4. a changed `h[B]` alignment, a multiply-back error, a negative/nonminimal denominator, a common
   factor in `(z,d)`, and integer magnitudes beyond fixed-width arithmetic;
5. first nonzero numerators at the first, middle, and final canonical columns; an earlier planted
   nonzero preceding a claimed witness; a final-column dependency break; and a nonzero exact
   numerator chosen to vanish under a permitted fixed prime;
6. a corrupted 350-minor entry or determinant identity, and a mutation outside `R` that leaves the
   coordinate solve unchanged but breaks the 540-row null-vector replay;
7. a dependency coefficient or last-column mutation, zero `tau`, and separate `b`, `c`, `s`, and
   `r` mutations that break the member replay, residual replay, or target bridge;
8. a pre-existing output, a concurrent output creator, an input/source/audit-receipt change after
   initial hashing, a short/failed write, and a crash before manifest-last publication.

Controls must prove both directions: the valid near-neighbor passes and the single mutation fails.
Synthetic success is evidence only that the gate can discriminate; it is never presented as the
live scientific result. No test may hard-code the expected G-0168 branch, scientific sequence
identifier, reduced price, determinant, separator, or output digest.

## No-overwrite, mutation, and publication controls

- Snapshot and hash every bound source, build input, audit receipt, scientific input, and upstream
  certificate before parsing or arithmetic. Retain the exact byte snapshots or safe descriptors
  actually used.
- Rehash every bound path after all arithmetic and certificate replay, immediately before
  publication. Compare path identity, regular-file status, size, and digest to the initial
  snapshot. Any drift invalidates the run.
- Create the output directory and every final output exclusively. No `--force`, truncation,
  replacement, merge, append-to-existing, or reuse of a prior partial/output directory is allowed.
- Write only to a new contained staging location; validate and hash staged bytes; publish
  manifest-last by a no-clobber atomic transition. A crash or exception leaves no artifact that a
  consumer can parse as a scientific branch.
- Emit no provisional branch token, witness, separator, determinant, rank, reduced price, or
  outcome-bearing filename before all checks and the end rehash succeed.
- Rehash the committed receipt and final published artifact after publication and record their
  digests without rewriting either.

## Prohibited scientific modes and claims

Source clearance fails if the producer contains or accepts an unbound bypass for audit receipt,
input digest, exact parsing, replay, end rehash, or no-overwrite; an approximate/float/tolerance
decision; a probabilistic or modular terminal rank; adaptive basis/row selection; a sampled,
sharded, truncated, resumed, or reordered canonical scan; a cached or injected scientific result;
an outcome-specific fixture or hard-coded branch; or a hidden retry/alternate-answer path.

This first-row producer must not perform Fresh128 Stage B pricing, solve the later correction
system, select a new basis, re-certify a different family, claim family completeness, or emit an
unrestricted mathematical conclusion. Those are different scientific programs.

## Exact source-audit receipt contract

If and only if every gate succeeds, the later audit may write:

`artifacts/reviews/G-0171-g0168-first-row-source/SOURCE_AUDIT_RECEIPT.json`

The producer must hard-code and validate schema
`max11-g0171-g0168-first-row-source-audit-v1` and the exact check-name set below. The receipt has
exactly these top-level keys:

`schema`, `verdict`, `result`, `evidence_class`, `claim_boundary`, `reviewer`,
`preregistration`, `subject`, `required_checks`, `scientific_manifest_observed`,
`scientific_input_observed`, `scientific_output_observed`, `scientific_run_executed`,
`rank_outcome_observed`, `no_claim`.

Fixed `PASS` values are:

- `schema`: `max11-g0171-g0168-first-row-source-audit-v1`
- `verdict`: `PASS`
- `result`: `SOURCE_CUSTODY_AUDIT_PASS_T1`
- `evidence_class`: `T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT`
- `claim_boundary` and `no_claim`: the exact quoted strings above
- all five scientific observation/execution flags: strict JSON `false`

`reviewer` contains exactly `agent_name`, `program`, `model`, `same_model_lineage`, and
`fresh_context`. `preregistration` contains exactly `path`, `sha256`, `git_commit`,
`committed_and_pushed_before_source_inspection`, and
`committed_and_pushed_before_runtime_checks`. `subject` contains exactly `git_commit`,
`source_bindings`, `transitive_build_bindings`, and
`commit_object_and_working_bytes_equal_for_all_bindings`. Each binding entry contains exactly
`name`, `path`, and `sha256`; names and paths are unique across both arrays and are sorted by name.

`required_checks` contains exactly these 28 strict JSON booleans, all `true`:

1. `exact_frozen_preregistration_binding_verified`
2. `exact_source_and_transitive_build_bindings_verified`
3. `commit_object_working_bytes_and_paths_verified`
4. `strict_closed_schema_parsing_verified`
5. `hostile_receipt_parser_matrix_verified`
6. `canonical_163740_family_census_and_order_verified`
7. `certified_basis_rows_columns_and_digests_verified`
8. `exact_540x349_basis_and_349x349_square_reconstruction_verified`
9. `exact_st_solve_and_multiply_back_verified`
10. `canonical_denominator_clearing_verified`
11. `canonical_first_exact_reduced_price_scan_verified`
12. `modular_triage_nonterminal_verified`
13. `rank_growth_350_minor_identity_verified`
14. `rank_growth_null_vector_540_row_replay_verified`
15. `full_scan_dependency_relation_verified`
16. `dependency_separator_target_bridge_verified`
17. `exact_branch_totality_and_invalid_sink_verified`
18. `arbitrary_precision_only_verified`
19. `synthetic_both_scientific_branches_verified`
20. `mutation_and_late_column_controls_verified`
21. `no_hardcoded_outcome_or_fixture_laundering_verified`
22. `complete_input_snapshot_end_rehash_verified`
23. `exclusive_no_overwrite_atomic_publication_verified`
24. `no_partial_or_outcome_bearing_intermediate_publication_verified`
25. `producer_self_test_passed`
26. `producer_static_preflight_passed`
27. `live_receipt_validation_verified`
28. `prohibited_scientific_modes_not_run`

The receipt validator and hostile harness must reject `false`, missing, integer, string, duplicate,
and unknown-name mutations for every required check; unknown top-level and nested keys; duplicate
JSON keys; trailing data; every binding path/hash substitution; a noncanonical or self-referential
commit field; and `true` or numeric mutations for each scientific flag. It must validate the live
receipt, not a reduced surrogate, then rehash it without overwriting it.

If any requirement cannot be established, the correct audit product is a precise `FAIL`/null with
the unmet check names. No `PASS` receipt is emitted, and no scientific standing changes.
