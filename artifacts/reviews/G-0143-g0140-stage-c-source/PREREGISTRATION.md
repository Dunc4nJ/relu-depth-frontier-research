# G-0143 preregistration — outcome-blind source/custody audit of G-0140 Stage C

## Identity and frozen subject

- Registered UTC: `2026-08-31T18:45:24Z`, before inspecting any Stage-C
  source internals, executing its launcher/binaries/tests, or writing the audit
  checker.
- Auditor: `ChartreuseCondor` (`codex`, `GPT-5`; same model lineage as the
  producer and therefore at most T1). The dispatch supplied high-level history
  that stale-native-binary, parser-shape, and rank-certificate defects had been
  found during development. That defect awareness is disclosed; no claim of T2
  or clean-room scientific independence is permitted.
- Mode/domain: read-only W2 source/custody audit inside the W1 mathematics
  campaign; outcome-blind with respect to every future G-0140 scientific run.
- Exact subject commit: `2bdc6f5c7132b0ed30d291c5ba116e84fda5044e`.
- Audit writes are confined to
  `artifacts/reviews/G-0143-g0140-stage-c-source/`; producer bytes are immutable.

The exact committed subject is:

| Path | Git mode | Git blob | Bytes | SHA-256 |
|---|---:|---|---:|---|
| `artifacts/math/G-0140/stage_c_selector/complete_matrix_rank_selector_v1.py` | `100755` | `554aba6ddd26715027253f417a8401a3f195c7e7` | 112422 | `a86e8ac8ee3dd37e980336b09c0345f87327243c1f113546c23ccdb57ddc2c18` |
| `artifacts/math/G-0140/stage_c_selector/ffpack_modular_pivots.cpp` | `100644` | `b73b6c739925b8974ee11f3f621f485411977fa2` | 7783 | `198262e449c901f70b1e26cd260cbd5ade4e6eaf2868659e4cfd59a1ab72d9c7` |
| `artifacts/math/G-0140/stage_c_selector/ffpack_modular_pivots_v1` | `100755` | `ce896fac4b22c9adce25344d963547b8d37b923d` | 344936 | `207fcf88fe3f89c8119bd6b38037d9f0919165eecf04b48d1b0aaae039843171` |
| `artifacts/math/G-0140/stage_c_selector/ffpack_modular_pivots_v1.build.json` | `100644` | `fc1a1b2f5d363408a88e9e9e3ef1910f0040ebca` | 1027 | `5157c020cc343de6bb891fb339a1027a9f8f3059aa03ea2a32722bc13d0fff76` |
| `artifacts/math/G-0140/stage_c_selector/run-stage-c-selector-v1` | `100755` | `7e20c32bfa45ac333d2b3282f2845c4d90b514bd` | 566 | `786b42f28d4720ca2578de78a3e312ce0186b8609d2b2c9c85c8f76bdd409d78` |
| `artifacts/math/G-0140/stage_c_selector/test_ffpack_modular_pivots_v1.py` | `100755` | `afce9ee0bd391b20ab672063a0542205f7736803` | 5360 | `5d2b920f06100a2a7bd4069ebe4f009d4c2ba8aecea8872c9d4c58abe9296b94` |

Any subject-path, Git-object, mode, size, byte, or end-of-audit rehash mismatch
forces `FAIL`.

## Audit question and no-claim boundary

Is this exact frozen Stage-C producer suitable for one future manifest-gated
execution, in the narrow sense that its code and committed native executable
implement the declared complete-matrix exact rank/row-selection protocol,
strictly bind all inputs and gates, and fail closed under outcome-blind hostile
controls?

A `PASS` establishes only bounded source/custody suitability for these exact
bytes. It does **not** establish that Stage C has run; that its 540 by 163740
matrix is mathematically the intended matrix; that a future rank, dependency,
separator, or selected-row result is correct; that the frozen family is a
complete ReLU family; that MAX11 has or lacks a representation; or that any
claim is independently replayed, T2, refereed, or formalized.

## Outcome-blind execution boundary

- `scientific_manifest_observed`, `scientific_input_observed`, and
  `scientific_output_observed` are fixed to `false` for a passing audit.
- The scientific/default/run path is forbidden. No full matrix, Pool128 result,
  rank computation over campaign data, target decision, selector run, or
  scientific output may be produced or consumed.
- Allowed execution is limited to committed self-tests and static/preflight
  modes that use synthetic fixtures and do not open a future one-shot manifest
  or Stage-A/B scientific output. Native tests may use independently authored
  tiny matrices only.
- Read-only Git/object/hash/ELF/dependency/source inspection is allowed. A
  rebuild may occur only in an isolated temporary directory to adjudicate the
  source-to-binary custody claim; it may not publish into the repository.
- Hostile mutations must occur in isolated temporary copies and may exercise
  only the same non-scientific modes.
- If a forbidden future artifact exists, only its pathname existence may be
  noted. Opening, hashing, parsing, copying, or inferring its contents forces
  `FAIL` under this protocol.

## Frozen obligations and falsifiers

1. **Exact custody and ancestry.** Bind all six files above to the exact
   subject commit, require regular contained paths (no symlink/escape or
   untracked substitution), verify promised build metadata and native-binary
   provenance, and rehash at exit. Every required ancestor/audit commit must
   exist in the exact history; prefix, mutable-worktree, or fallback matching
   is insufficient.
2. **Future admission gates.** Before any scientific work, require the exact
   G-0140 preregistration and one-shot manifest plus exact G-0139 result audit,
   G-0141 Stage-A source audit, G-0142 Stage-B source audit, admitted Stage-A/B
   inputs, and this G-0143 receipt. Required schemas, verdicts, evidence/T1
   boundaries, paths, hashes, commits, and transitive anchors must be checked;
   partial semantic checks or file-existence checks are a `FAIL`.
3. **Strict interfaces.** Every JSON/binary parser must fail closed on duplicate
   or unknown keys, wrong types (including booleans as integers), noncanonical
   integer/string encodings, order/cardinality/digest drift, trailing bytes,
   short reads, duplicate/reordered records, path escape/symlink substitution,
   and schema/result-name drift. Publication must be exclusive/no-clobber and
   mutation-detected from entry through exit.
4. **Matrix and order contract.** The frozen intended dimensions are 412
   existing rows followed by 128 Pool128 rows, against 163740 canonical family
   columns. Direction/record/row/target order, orientation, and all censuses
   must be explicit and reconciled. The target is the 412-row inherited target
   followed by 128 zeros; no row or column may be silently skipped, duplicated,
   permuted, transposed, or narrowed.
5. **Modular proposals are non-authoritative.** Each fixed-prime native result
   may propose candidate column indices only. No modular rank, pivot, residue,
   or agreement across primes may establish exact rank, independence,
   compatibility, or a separator. Every admitted basis column and all final
   claims must be reconstructed and checked over exact integers/rationals.
6. **Complete exact column basis.** Starting from proposals, exact arithmetic
   must form an independent basis and canonically scan **all 163740 columns**.
   Whenever a column is outside the current exact span it must be appended;
   completion requires every column to be checked and to lie in the final span.
   An exact basis certificate, all-column census/digest, and a checkable
   annihilator or equivalent span certificate are required. Early exit at a
   modular/full-rank guess, proposal-only rank, or unscanned suffix is `FAIL`.
7. **Prefix-rank theorem and row selection.** For a complete exact column-basis
   matrix `B`, the implementation may derive prefix row ranks from the ordered
   column-rank profile of `B^T` only if it preserves original row order and
   verifies the theorem that `rank(B[0:k,:])` equals the count of profile
   indices below `k`. Tiny asymmetric/random exact fixtures must compare the
   optimized profile method with direct exact rank for every prefix. Selected
   Pool128 rows must be the first at most 32 canonical rows whose exact prefix
   rank grows relative to the 412-row base, with terminal/dependent-row
   metadata unable to imply processing that did not occur.
8. **Target compatibility and exact certificates.** Compatibility is exactly
   `rank(M) = rank([M|t])` over characteristic zero. A compatible result must
   provide enough exact data to replay target membership. An incompatible
   result must provide an exact nonzero left separator `y` with `y^T M = 0`
   over **every** family column and `y^T t != 0`, with row order and primitive
   normalization pinned. Dependency certificates must likewise replay exactly;
   a modular or selected-column-only separator is `FAIL`.
9. **Native streaming and I/O.** Audit orientation, signed-value encoding,
   fixed-prime arithmetic, little-endian assumptions, dimensions, byte counts,
   EOF/trailing-data behavior, stdout schema, stderr/exit behavior, and pivot
   canonicality. Require full-stream census even after rank saturation. A
   stale binary, source/build-receipt mismatch, host-endian dependence, short
   stream, overwrite, noncanonical residue, malformed stdout, or accepted
   compiled-byte mutation is `FAIL`.
10. **Potent tests and claim boundary.** Reexecute the committed self-tests,
    static preflight, native asymmetric oracle, and build/source custody. Add
    independent hostile controls for any uncovered load-bearing branch. Tests
    must contain honest positive fixtures and must-fail mutations; zero-run,
    hard-coded-success, weakened assertions, regenerated goldens, and fixtures
    represented as live science are `FAIL`. Success language must remain
    source/custody readiness only.

Any missing evidence for a load-bearing branch, checker exception, scientific
path reachability from an allowed mode, accepted hostile mutation, or failure
of an obligation above yields `FAIL`; uncertainty is never rounded up.

## Fixed audit procedure and receipt

1. Commit and push this preregistration alone.
2. Inventory and initial-hash the exact six-file subject without observing
   scientific artifacts.
3. Inspect the Python selector, native C++ adapter, build receipt, launcher,
   and native test harness line by line; trace every allowed and forbidden
   entry path against the obligations above.
4. Independently derive the relevant linear-algebra invariants and exercise
   them on synthetic exact fixtures, including asymmetric and adversarial cases.
5. Reexecute only committed outcome-blind tests/preflights and an isolated
   custody rebuild. Capture commands, stdout/stderr, exit codes, denominators,
   and countermetrics without suppressing stderr.
6. Rehash the subject at exit and confirm that only the reserved audit path was
   edited by this auditor.
7. Emit one machine-readable receipt at
   `artifacts/reviews/G-0143-g0140-stage-c-source/SOURCE_AUDIT_RECEIPT.json`
   with schema `max11-g0143-g0140-stage-c-source-audit-v1`, exact `PASS` or
   `FAIL`, nested subject bindings, executed-evidence records, obligation
   verdicts, hostile-control results, all three observation booleans `false`,
   T1 limitation, residual doubts, and minimum decision-bearing repairs on
   `FAIL`. Commit and push the audit artifacts.

## Anti-ceremony creation-gate worksheet

- Boundary: the receipt is process, although the future Stage-C admission path
  and one-shot manifest decision branch on it.
- Consumer: research leader `RainyGorge` and the frozen Stage-C admission gate.
- Gate: no G-0140 Stage-C scientific execution may be authorized from these
  bytes without a G-0143 `PASS` bound in the one-shot manifest.
- Observed defect class: development already exposed stale native bytes,
  permissive parser/recursive-binding behavior, and a rank-certificate/census
  bug; each can silently invalidate the claimed complete-basis computation.
- Deletion condition: the receipt stops controlling immediately when any of
  the six subject bytes, subject commit, or required predecessor gate changes;
  it remains historical provenance only.
- Highest-priority ready capability: the actual exact Stage-C run. This one
  bounded audit is its explicit hard gate; an hour on the run is not valuable
  if its native/exact boundary is unsound. No broader governance or second
  meta-audit is authorized.
- Integrity exception: not invoked; the ordinary creation gate is satisfied.
- Verdict: `LEGITIMATE GATE`; create only this preregistration, one focused
  checker/test bundle, and one receipt.
