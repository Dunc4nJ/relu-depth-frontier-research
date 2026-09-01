# G-0165 outcome-blind source/custody audit preregistration

**Sealed before frozen-subject inspection:** 2026-09-01 UTC  
**Reviewer:** Agent Mail identity `WildCliff` · program `codex` · model `GPT-5`  
**Evidence ceiling:** `T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT`

## Frozen identities supplied to the reviewer

| Role | Path | Commit | Expected SHA-256 |
|---|---|---|---|
| Producer subject | `artifacts/math/G-0164/all128_direct_basis_master_v1.py` | `05e8acaebf1d6e293049858e3d85a1cda9a25eae` | `d8ea3d21e419f5a0fa7303a347af068e8f37e3f6fe53730879535f78b5070d90` |
| Scientific preregistration | `artifacts/math/G-0164/PREREGISTRATION.md` | `dbd488609efda9d6a4eba33fb2c82d67d49b9288` | `f28813a182327e38e713c8a20e9039f12d9722861455dcb1a5fb0bb332b00c10` |

This audit begins only after this file is committed and pushed. The later receipt must bind this audit preregistration by its own path, committed SHA-256, and commit.

## Audit question and fixed boundary

The audit asks only whether the exact frozen producer bytes implement a fail-closed, deterministic, custody-preserving direct-basis protocol consistent with the frozen scientific preregistration. It does not ask what the finite-family answer is and will not execute the scientific computation.

Exact claim boundary for any passing receipt:

> Source/custody clearance for the exact frozen G-0164 direct-basis producer bytes only; no G-0164 finite member or global replay output was inspected or created and no scientific solve was run.

Exact no-claim statement:

> This audit does not establish finite membership, a global MAX11 identity, frozen-family membership or nonmembership, a lower bound, unrestricted representability, minimality, an all-n theorem, or a Lean theorem.

## Contamination and execution controls

- Do not inspect any scientific output under `artifacts/math/G-0140`.
- Do not inspect or create `artifacts/math/G-0164/all128_manifest_v1.json` or `artifacts/math/G-0164/all128_direct_basis_member_v1.json`.
- Audit only in a sanitized isolated worktree or copy in which the G-0140 outputs and the two G-0164 output paths above are absent.
- Never invoke producer modes `--freeze-manifest`, `--preflight`, or `--run`.
- The only permitted producer executions are project-Python `py_compile`, `--self-test`, and `--preflight-static`.
- Synthetic and static hostile controls must use invented inputs in temporary storage and must not price or scan the scientific family, solve the scientific system, retry candidate selection, or publish a scientific artifact.
- Any unexpected access to or creation of a forbidden path, identity mismatch, nondeterminism, contract weakness, control failure, or unexplained exception forces a fail-closed verdict and no scientific claim.

## Precommitted inspection and control plan

The receipt may report `PASS` only if every check below is independently supported by source inspection, permitted execution, and/or hostile synthetic control:

1. `exact_source_and_preregistration_identity_verified`: recompute both frozen Git-object hashes and require exact path/commit/SHA-256 equality.
2. `strict_contract_validation_verified`: reject missing, extra, mistyped, out-of-range, path-escaping, or identity-inconsistent contract inputs before work or publication.
3. `stored_basis_digest_gates_verified`: require every stored basis identity/digest gate, and demonstrate rejection after a synthetic stored-basis mutation.
4. `exact_349_square_solve_protocol_verified`: establish that the committed protocol solves exactly one fixed 349-by-349 square system, with exact arithmetic and no adaptive column/rank search.
5. `primitive_integer_replay_verified`: establish primitive-integer normalization and exact replay against all frozen input rows before publication.
6. `exclusive_output_publication_verified`: establish exclusive, fail-closed output creation with no overwrite and no partial survivor publication.
7. `input_snapshot_end_rehash_verified`: establish end-of-run rehashing of all bound input snapshots before publication, with mutation refusal.
8. `no_pricing_rank_scan_or_retry_verified`: establish statically and dynamically that the producer performs no scientific pricing, family/rank scan, basis selection, retry, or branch-on-outcome search.
9. `synthetic_full_row_member_fixture_passed`: an invented internally consistent full-row member fixture must pass the same exact validation/replay path.
10. `synthetic_inconsistent_extra_row_rejected`: adding one invented inconsistent extra row must be rejected by the unchanged validation/replay path.
11. `coefficient_mutation_control_verified`: mutating one solved coefficient so an exact row identity breaks must flip acceptance to rejection.

The hostile harness will additionally watch filesystem opens/creates and subprocess invocations, require forbidden paths to remain absent, and compare before/after snapshots of the isolated audit tree.

## Receipt contract

If and only if all checks pass, write `artifacts/reviews/G-0165-g0164-all128-master-source/SOURCE_AUDIT_RECEIPT.json` with schema `max11-g0165-g0164-all128-master-source-audit-v1`, the exact required top-level key set, all eleven booleans true, `scientific_output_inspected = false`, `scientific_output_created = false`, `scientific_run_executed = false`, and the exact claim/no-claim strings above. The receipt is a source/custody review artifact only and cannot promote a scientific result.
