# G-0148 Stage-C final source audit preregistration

## Frozen audit identity and decision

- Reviewer: `RusticIbis` (`codex`, `GPT-5 Codex`), fresh same-lineage T1 context.
- Registered: 2026-08-31 before any frozen-subject source inspection, selector/native runtime check, scientific-input observation, or scientific replay.
- Mode: read-only W2 audit, mathematics domain, bounded to one decision: whether the exact frozen Stage-C producer bytes earn T1 source/custody clearance.
- Consumer: the G-0148 gate consumed by the Stage-C selector and the parent auditor.
- Gate: no G-0148 PASS receipt may be issued unless every obligation below passes against the exact frozen bindings.
- Observed defect class: the historical G-0143 FAIL findings F01--F05 and adjacent parser, custody, basis, filesystem, and claim-boundary failure modes named below.
- Retirement condition: this preregistration remains only as provenance for this G-0148 decision; it authorizes no later review rounds or new audit machinery.

The frozen selector commit supplied by the audit owner is
`848382ea3d9fb21ece3a4a7203a563daf497cf96`.

The six frozen subject bindings supplied by the audit owner are:

| Path | Expected SHA-256 |
|---|---|
| `artifacts/math/G-0140/stage_c_selector/complete_matrix_rank_selector_v1.py` | `950dc5edbae0c43f60e6fb2dd1c8dbb86d2c86d5766699ee513bd66469be38b9` |
| `artifacts/math/G-0140/stage_c_selector/ffpack_modular_pivots.cpp` | `198262e449c901f70b1e26cd260cbd5ade4e6eaf2868659e4cfd59a1ab72d9c7` |
| `artifacts/math/G-0140/stage_c_selector/ffpack_modular_pivots_v1` | `207fcf88fe3f89c8119bd6b38037d9f0919165eecf04b48d1b0aaae039843171` |
| `artifacts/math/G-0140/stage_c_selector/ffpack_modular_pivots_v1.build.json` | `5157c020cc343de6bb891fb339a1027a9f8f3059aa03ea2a32722bc13d0fff76` |
| `artifacts/math/G-0140/stage_c_selector/test_ffpack_modular_pivots_v1.py` | `5d2b920f06100a2a7bd4069ebe4f009d4c2ba8aecea8872c9d4c58abe9296b94` |
| `artifacts/math/G-0140/stage_c_selector/run-stage-c-selector-v1` | `786b42f28d4720ca2578de78a3e312ce0186b8609d2b2c9c85c8f76bdd409d78` |

Split last-touch commits are permitted. Every subject path's last-touch commit must exist and be an ancestor of this preregistration commit; the Python selector must bind to the supplied selector commit, and all six committed blobs and working-tree bytes must equal their supplied hashes.

## Outcome-blind boundary

Until this file is committed and pushed, the reviewer will not open or inspect any of the six subject files, run the selector or native oracle, inspect historical G-0143/G-0146/G-0147/G-0139 receipts, or run any subject check. Throughout the audit the reviewer will not open a future G-0140 manifest, any Stage-A or Stage-B scientific input, any Stage-C scientific output, or execute a scientific rank computation.

Allowed evidence modes after the preregistration is frozen are limited to:

1. exact Git/blob/worktree custody and ancestry checks;
2. source inspection of the six frozen subject paths and only the historical receipts/schema artifacts needed to adjudicate F01--F05;
3. selector `--self-test` and `--static-preflight` in non-scientific modes;
4. the frozen native oracle test;
5. an isolated native rebuild and custody comparison;
6. isolated synthetic/adversarial fixtures that do not contain or derive from scientific inputs or outputs.

Any accidental observation of a forbidden scientific artifact, or any scientific replay, is a terminal falsifier for PASS and must be disclosed.

## Precommitted obligations and falsifiers

PASS is all-or-nothing. A single unresolved discrepancy, fail-open parser path, unexecuted required control, subject drift, forbidden observation, or unsupported inference forces an honest non-consumable FAIL receipt.

### O01 — exact subject binding and committed-blob custody

Check the supplied commit, all six path/hash pairs, file types/modes, working-tree equality, each path's last-touch commit, and ancestry relative to this preregistration. Independently hash both `git show <binding-commit>:<path>` bytes and working-tree bytes. Hostile controls must cover a one-byte worktree drift and a committed-blob/worktree mismatch without modifying the subject checkout. Falsifiers: any missing path, unexpected symlink/type, hash mismatch, wrong Python last-touch commit, subject commit not preceding preregistration, or selector acceptance based only on mutable working-tree bytes.

### O02 — compiled source/executable custody and proposal-only native boundary

Bind C++ source, build metadata, shipped executable, test, and launcher to exact bytes. Inspect build metadata for source/compiler/flags/output hashes and reproduce the native build in an isolated temporary directory without overwriting the shipped executable. Run the native oracle test against the frozen executable and, separately, the isolated rebuild. Verify the native helper only proposes modular pivots/candidates and cannot establish exact-Q rank, exact compatibility, admission, or a scientific claim. Falsifiers: unverifiable build provenance, source/binary drift, shipped-artifact overwrite, a native result treated as dispositive, or any path by which native output bypasses exact Python verification.

### O03 — complete column-basis and exact-Q prefix protocol

Inspect and adversarially exercise the basis construction. Require a complete column basis for the exact matrix/prefix state, exact rational arithmetic for the theorem-bearing decision, deterministic pivot/census accounting, and an explicit proof bridge from prefix growth/dependency information to the claimed selector invariant. Hostile controls include column permutations, duplicate/dependent columns, rational coefficients with nontrivial denominators, and modular false positives. Falsifiers: sampled/incomplete columns presented as a basis, modular evidence promoted to exact-Q, an unproved prefix shortcut, a zero-run control, or inconsistent census totals.

### O04 — F01 cap-versus-compatibility and dependency-basis invariant

Require admission to stop after the first 32 growth rows while compatibility scanning continues through all 128 rows. Every later growth row must join the dependency basis even though it is not admitted. Exercise at least two independent synthetic late failures:

1. a dependency becoming incompatible only after the admission cap; and
2. a later incompatible dependency whose primitive relation necessarily uses an unadmitted post-cap growth row.

For each, independently recompute and compare the exact primitive integer relation, target pairing, incompatibility witness, and full-family separator replay. Also require a positive compatible late dependency and exact scan/admission/growth counters. Falsifiers: early break at cap, post-cap growth omitted from the dependency basis, relation normalization/pairing ambiguity, separator replay over a prefix rather than the full family, or any hostile fixture escaping rejection.

### O05 — F02 exact G-0146/G-0147 receipt admission

Require exact schema, verdict/result, evidence class, claim boundary/no-claim, scientific-observation flags, subject commit/path/hash bindings, and preregistration semantics for both prerequisite receipts. Test valid near-identical controls and reject hash-only lookalikes, wrong schema/result/evidence/boundary/flags/subject/hash, missing/extra mandatory bindings, duplicate JSON keys, type confusion, path aliases, and symlink/path escape. Falsifier: any receipt admitted because one expected digest or substring appears while the semantic contract is wrong.

### O06 — F03 exact G-0139 semantic/custody gate

Recover the exact G-0139 contract only after this preregistration is frozen. Require rejection of a minimal lookalike and every one of the six named historical mutants encoded by the subject/tests, with a valid near-identical control accepted. Verify schema/result/evidence/boundary, subject and custody bindings, flags, and exact hash semantics rather than filename or digest presence. Falsifier: any named mutant or minimal lookalike is accepted, or the genuine shape is rejected for a reason that masks a weaker gate.

### O07 — F04 exact G-0148 self-semantics without circularity

Require the selector's own G-0148 input contract to validate exact schema `max11-g0148-g0140-stage-c-final-source-audit-v1`, PASS verdict, result `SOURCE_CUSTODY_AUDIT_PASS_T1`, evidence class `T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT`, exact claim/no-claim text, four false scientific flags, exact six subject bindings, exact preregistration path/hash/commit and three true preregistration flags, and the exact required-check set. Reject self-referential `audit_git_commit`, circular dependence on the not-yet-existing receipt's commit/hash, alternate schemas/results/boundaries, missing checks, extra fail-open fields, duplicate keys, and forged preregistration timing/ancestry. Falsifier: the receipt can certify itself, can be accepted without the preregistration preceding inspection/checks, or relies on an audit commit field excluded by contract.

### O08 — F05 Stage-B top-level schema and mandatory bindings

Without opening any real Stage-B scientific output, derive the required top-level contract from source/tests and use synthetic manifests only. Require mandatory manifest, Stage-A, candidate, G-0139, source-input, and mutation bindings plus exact top-level schema/result/flags/boundaries; optional absence must fail closed. Reject missing, null, renamed, duplicated, path-escaped, symlinked, type-confused, and hash-only fields. Falsifier: any mandatory field is optional/fail-open or a minimal lookalike is accepted.

### O09 — full scan census and output/overwrite boundary

Require a 128-row full-pool compatibility census independent of the 32-row admission cap, internally reconciled counters, deterministic ordering, atomic/non-overwriting output behavior, strict JSON emission, and a claim boundary that says only what the producer bytes and eventual bounded run could support. Attack duplicate JSON, pre-existing output, input/output aliasing, output symlink/hardlink/path escape, traversal, non-regular files, and malformed/extra JSON. Falsifiers: partial scan reported as full, output overwritten or escaped, duplicate-key ambiguity, scientific claims inferred from source clearance, or a producer receipt claiming family membership/nonmembership or a MAX11 theorem.

### O10 — required observed checks and evidence record

The final review must record exact commands, exit codes, material stdout/stderr, environment/tool versions relevant to reproducibility, source citations, isolated fixture/rebuild locations, and limitations. It must independently observe and mark exactly these checks: `exact_subject_binding`, `compiled_source_executable_custody`, `complete_basis_protocol`, `full_pool_dependency_compatibility_scan`, `receipt_admission_strictness`, `committed_blob_custody`, `self_test`, `native_oracle`, `static_preflight`, and `claim_boundary`. A claimed-but-unrun, zero-test, stderr-silenced, cached, or scientific run falsifies PASS.

## Precommitted verdict contract

If and only if O01--O10 all pass, emit `SOURCE_AUDIT_RECEIPT.json` with exactly the owner-supplied PASS contract, including:

- schema `max11-g0148-g0140-stage-c-final-source-audit-v1`;
- verdict `PASS`, result `SOURCE_CUSTODY_AUDIT_PASS_T1`, and evidence class `T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT`;
- the exact supplied claim boundary and no-claim texts;
- all four scientific-observation/replay flags false;
- the exact subject commit and six nested path/SHA-256 bindings;
- `subject.commit_object_and_working_bytes_equal_for_all_bindings = true`;
- the exact preregistration path, its post-commit SHA-256 and commit, and all three timing booleans true;
- exactly the ten required checks listed in O10, each `PASS`;
- no self-referential `audit_git_commit`.

If any obligation fails, emit an honest FAIL that names exact blockers and cannot satisfy the PASS consumer. No failure will be softened into a warning, and no process completeness will substitute for source/runtime evidence.

## Claim boundary and no-claim

The maximum possible positive conclusion is exactly:

> T1 source/custody clearance for the exact frozen Stage-C producer bytes only; no scientific manifest, input, or output was observed, no scientific replay was run, and no mathematical claim is promoted.

The audit will carry this exact no-claim:

> This source audit does not adjudicate any future G-0140 scientific manifest or result and does not establish family membership, family nonmembership, a MAX11 lower bound, unrestricted nonrepresentability, minimality, an all-n theorem, refereed status, formalization, or a Lean theorem.

