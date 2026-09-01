# G-0166 preregistration: G-0164 global-replay source/custody audit

## Registration and decision rule

- Auditor identity: `BlackThrush`
- Program/model: `codex` / `gpt-5.4`
- Audit class: fresh-context, same-model-lineage, outcome-blind source/custody audit
- Frozen subject commit: `29f0610068dd47933f78a5e2222513d65e56713f`
- This document is written only from the binding hashes and audit contract supplied to the auditor. No subject source, scientific manifest, scientific input, scientific output, or scientific result was inspected before this preregistration.
- This preregistration must be committed, pushed to `origin/master`, and confirmed from the remote before any subject source inspection or runtime check.
- A `PASS` receipt is permitted only if every preregistered gate below succeeds against the exact committed bytes. A null/`FAIL` outcome is preferred to a false or unsupported `PASS`. No assertion may be weakened, inferred from a report, or replaced by a fixture presented as live evidence.
- This audit may clear source/custody only. It cannot establish the MAX11 identity or any other scientific claim.

## Frozen named bindings

The audit binds exactly these eight names. Each name must occur exactly once, resolve to the listed path, and match the listed SHA-256 in the subject commit, the commit object/blob view, and the working tree used for compilation and checks.

| Binding name | Exact path | SHA-256 |
|---|---|---|
| `main_source` | `artifacts/math/G-0164/stage_b_global_replay/src/main.rs` | `acadf6bcbc2b0ac6d87b096ff7909d5e07cfd31cae1e84fa7301a2b1488b2ef0` |
| `candidate_source` | `artifacts/math/G-0164/stage_b_global_replay/src/candidate.rs` | `572e2bf6bbd6e5f9b27e4f99700ec1960cc20114f0228e8a2d3343325a8b28fc` |
| `engine_source` | `artifacts/math/G-0164/stage_b_global_replay/src/engine.rs` | `b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c` |
| `cargo_manifest` | `artifacts/math/G-0164/stage_b_global_replay/Cargo.toml` | `05df37270ef89f78b8a764484ce2049b4b0bf152f1ef778b4d88352546318996` |
| `cargo_lock` | `artifacts/math/G-0164/stage_b_global_replay/Cargo.lock` | `fc18595480e30ffeda7fcedcd6d63019744b8b9718fff7d6d31a71a373f89595` |
| `g0117_cargo_manifest` | `artifacts/math/G-0117/Cargo.toml` | `0e2ff3c73ce82b508ae21b35bc973c202efbeae03b7e9cf78d3b784664ce5815` |
| `g0117_lib_source` | `artifacts/math/G-0117/src/lib.rs` | `2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6` |
| `release_executable` | `artifacts/math/G-0164/stage_b_global_replay/target/release/g0164-stage-b-global-replay` | `38de94fd68af9eb0aaa4fa2f26908ab4771caa42ab89f569d8ba6b729e93ce94` |

Displaced recursive lookalikes, a correct decoy with a missing named binding, duplicate path occurrences, path substitutions, hash substitutions, unknown binding names, and missing or extra bindings are rejection conditions.

## Outcome-blind observation boundary

The auditor must not open or read any of the following:

- `artifacts/math/G-0164/all128_manifest_v1.json`
- `artifacts/math/G-0164/all128_direct_basis_member_v1.json`
- any future global manifest or global output
- any G-0140 scientific output
- any other scientific result

The auditor must not invoke `--preflight` or `--run`. The only permitted producer runtime modes are `--self-test` and `--preflight-static`, run from the repository root against the frozen executable and both clean rebuilds as applicable. Compilation must not read scientific JSON.

The only permitted build/check commands are:

- `cargo fmt --check`
- `cargo test --locked`
- `cargo clippy --locked --all-targets -- -D warnings`
- two clean `cargo build --locked --release` builds using distinct `CARGO_TARGET_DIR` values from the same committed source path
- frozen/rebuilt executable `--self-test`
- frozen/rebuilt executable `--preflight-static` from the repository root

All four eventual receipt flags `scientific_manifest_observed`, `scientific_input_observed`, `scientific_output_observed`, and `scientific_replay_run` must remain strict JSON `false`.

## Static source/custody gates required for PASS

Before `PASS`, the auditor must independently verify all of the following against the frozen commit and working bytes:

1. The subject commit resolves exactly, and commit-object bytes, blob bytes, working bytes, paths, and SHA-256 values agree for all eight uniquely named bindings.
2. The manifest/envelope schemas are exact and strict: required fields and their types are enforced; unknown fields, missing fields, duplicate JSON keys, and trailing JSON data are rejected.
3. Custody and ancestry are exact, including the frozen audit/producer chain; a self-referential `audit_git_commit` is rejected.
4. The G-0164 engine bytes are exactly equal to the already-audited G-0140 engine bytes.
5. The complete G-0117 path-library build surface is covered by the two named bindings: `Cargo.toml` and `src/lib.rs`, with no `build.rs` and no external source modules or otherwise unbound build inputs.
6. The finite member-source parser and replay implementation are auditable and independent, with exact `540 x 349` BigInt replay logic.
7. Global aggregation uses exact normal-form arithmetic.
8. The producer subtracts `target_scale * 11!` at coordinate `10` exactly.
9. `GLOBAL_EXACT_ZERO` is possible if and only if every hinge residual and every linear residual is zero; otherwise the result is `EXACT_RESIDUAL_CONTINUE`, including the linear-only residual case.
10. The residual prefix is the first `min(128, nonzero hinge count)` nonzero hinge residuals in the specified order and remains correct when only linear residuals are nonzero.
11. Mutation/cancellation checks are total: mutations cannot cancel to a false zero or evade residual reporting.
12. The complete term and label census is enforced without omission, duplication, or substitution.
13. End-of-run rehash controls cover every bound input and source artifact required by the contract.
14. Existing-output overwrite refusal and race-safe publication controls are enforced.
15. Hostile receipt/parser checks cover unknown fields, duplicate keys, trailing data, wrong types, substituted paths/hashes, duplicate occurrences, displaced lookalikes, missing named bindings, self-reference, and forbidden scientific flags.
16. Two clean locked release builds are byte-identical to each other and to the frozen `release_executable` binding.
17. Every permitted frozen/rebuilt `--self-test` and `--preflight-static` invocation succeeds without observing scientific inputs or outputs.

## Exact receipt requirements

A receipt may be emitted only after every gate succeeds. Its path is:

`artifacts/reviews/G-0166-g0164-global-replay-source/SOURCE_AUDIT_RECEIPT.json`

It must use schema `max11-g0166-g0164-global-replay-source-audit-v1` and have exactly these top-level keys:

`schema`, `verdict`, `result`, `evidence_class`, `claim_boundary`, `reviewer`, `preregistration`, `subject`, `required_checks`, `scientific_manifest_observed`, `scientific_input_observed`, `scientific_output_observed`, `scientific_replay_run`, `no_claim`.

Fixed values on `PASS` are:

- `verdict`: `PASS`
- `result`: `SOURCE_CUSTODY_AUDIT_PASS_T1`
- `evidence_class`: `T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT`

`reviewer` must contain exactly `agent_name`, `program`, `model`, `same_model_lineage`, and `fresh_context`. `preregistration` must contain exactly `path`, `sha256`, `git_commit`, `committed_and_pushed_before_subject_source_inspection`, and `committed_and_pushed_before_runtime_checks`. `subject` must contain exactly `git_commit`, `commit_object_and_working_bytes_equal_for_all_bindings`, and `bindings`. `bindings` must contain exactly the eight names and exact path/hash pairs frozen above. The exact `claim_boundary` and `no_claim` strings will be copied from the final bound `main_source` only after this preregistration is remotely confirmed; they will not be guessed or paraphrased.

`required_checks` must contain exactly these twenty strict JSON booleans, all `true`:

1. `exact_named_binding_contract`
2. `displaced_recursive_lookalikes_rejected`
3. `correct_decoy_with_missing_named_binding_rejected`
4. `duplicate_path_occurrences_rejected`
5. `unknown_envelope_fields_rejected`
6. `audit_git_commit_rejected`
7. `duplicate_json_keys_rejected`
8. `trailing_json_data_rejected`
9. `producer_self_test_passed`
10. `producer_static_preflight_passed`
11. `compiled_source_manifest_lock_match_working_bytes`
12. `engine_byte_identity_with_g0140_verified`
13. `finite_member_source_audit_gate_verified`
14. `finite_member_global_manifest_commit_chain_verified`
15. `scientific_outputs_excluded_from_manifest_bindings`
16. `dynamic_direct_basis_member_contract_verified`
17. `global_zero_and_residual_branches_verified`
18. `complete_label_census_and_end_rehash_verified`
19. `overwrite_refusal_verified`
20. `prohibited_scientific_modes_not_run`

The receipt validator/harness must be parameterized and must reject, at minimum:

- `false`, missing, and integer mutations for each of the twenty checks
- unknown top-level fields, unknown nested fields, and unknown check names
- duplicate JSON keys at every relevant level and trailing JSON data
- a self-referential audit commit
- every binding path substitution and every binding hash substitution
- `true` and numeric mutations for each of the four scientific-observation/execution flags

The receipt must be validated as the actual live artifact, not a weakened surrogate. After creation, all bound inputs and the receipt must be rehashed; overwrite/refusal controls must be exercised. If any requirement fails or cannot be established, no `PASS` receipt will be emitted.

## Evidence discipline and lifecycle

- Reports are claims, not evidence. Every cited command must be re-executed against the exact committed bytes.
- No hard-coded `PASS`, faked tests, or fixtures presented as live proof are admissible.
- The audit machinery is justified only as the hard outcome-blind gate before the single scientific replay and must be deleted or retired after that replay.
- Any uncertainty, unexpected scientific observation, prohibited-mode execution, source mismatch, custody mismatch, schema weakness, build mismatch, or incomplete check forces null/`FAIL` rather than `PASS`.
