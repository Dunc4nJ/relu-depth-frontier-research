# G-0163 outcome-blind T1 source/custody preregistration

Date: 2026-09-01

Receipt schema: `max11-g0163-g0140-stage-e-final4-source-audit-v1`

## Scope and blindness contract

This is a fresh, independent, outcome-blind T1 source/custody audit of the
frozen G-0140 Stage-E final4 producer. Before this preregistration was
committed and pushed, the auditor did not open or read the subject source, the
bound engine source, any G-0140 scientific manifest, or any Stage-A through
Stage-E scientific output. Earlier scientific outcomes will not be consulted.
The audit will make no scientific observations, will perform no full preflight
or scientific run, and will not create scientific output.

All source and runtime inspection will occur only in a fresh sanitized
isolated copy/worktree in which the G-0140 scientific manifest and all five
Stage-A through Stage-E scientific-output paths are absent. Repository and Git
metadata may be inspected outside that environment, but prohibited scientific
files will not be opened, copied into the audit environment, or used as audit
evidence.

This audit is valid only for the exact bytes pinned below. Any identity,
ancestry, contract, required-check, build, test, or hostile-control mismatch is
fail-closed and yields no PASS receipt.

## Frozen identities supplied before inspection

- Subject: `artifacts/math/G-0140/stage_e_global_replay/src/main.rs`
- Last subject-changing commit: `4944a58e0816fcf8e62dbdd134448daffce10738`
- Main source SHA-256: `be4852b63ff2118182cdd07ead85708f0b4ef0785445f0f873ebd4367c9e866a`
- Engine SHA-256: `b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c`
- `Cargo.toml` SHA-256: `a701d142aeb88cae15d30997dcc3039b5fee105cb3c26621fec9ddcca552f5c9`
- `Cargo.lock` SHA-256: `eaaa98ae381bed0f1b48f27e5ca7c3841c2e6e1b8fa6b07e09cff11d172ef2d0`
- Release binary SHA-256: `99ba4017c42ab08043b9aacaef554192ce50beff37a41df07ba8d4f7e4ba7179`
- Repaired Stage-D source: `artifacts/math/G-0140/stage_d_master/rank_aware_master_v1.py`
- Repaired Stage-D source commit: `19107c5eed2cad00d48eff3dd9bea0c015ecce89`
- Repaired Stage-D source SHA-256: `1f4e7f3a141bfbfb7a090ee681bab649ba0cebc191021b112db0368fe2256581`
- Required G-0162 receipt commit: `e93afa3abb8128f955792f95150e889433100f3b`
- Required G-0162 receipt SHA-256: `2e09106c38cdb366b7cf2ef62aa43b61c28a41eeb42587ec83ea808d39fca2d0`
- Required repaired Stage-D check: `stage_c_snapshot_digest_contract_verified`

## Fail-closed audit gates

A PASS receipt will be emitted only if every gate below is established against
the frozen bytes without inspecting or generating scientific outputs:

1. The subject commit, Git blob, checked-out file, and working bytes agree with
   the supplied main-source SHA-256. The engine, `Cargo.toml`, `Cargo.lock`, and
   frozen release binary agree with their supplied SHA-256 values.
2. The subject-changing commit is in the verified source/audit ancestry, the
   preregistration precedes the audit receipt, and the receipt commit is
   verified on `origin/master` before handoff.
3. The repaired Stage-D source commit and SHA-256 are exact, and the exact
   G-0162 receipt at its supplied commit and SHA-256 is bound by path, schema,
   status, identities, claim fields, and typed checks.
4. An exact typed-positive G-0162 fixture is accepted. Independent negative
   fixtures are rejected fail-closed for wrong receipt bytes/commit/schema,
   status, check name, check type/value, required-check-set membership,
   identities, and claim/no-claim fields. The positive fixture and exact
   required-check set include
   `stage_c_snapshot_digest_contract_verified`; its omission, renaming,
   duplication, non-boolean type, or false value is rejected.
5. All ten direct and transitive Stage-A through Stage-E future-output
   exclusions are present, exact, and enforced. Hostile fixtures show that
   each prohibited output path is rejected and that no scientific output is
   required for source-only validation.
6. The compiled engine identity and all source bindings are exact. Engine
   identity mismatches and binding substitutions are rejected.
7. The Stage-E source-audit receipt required-check set equals the frozen
   producer's required-check set exactly, with neither omissions nor
   additions. Hostile controls reject malformed schemas, status, check names,
   check types/values, identities, ancestry, source pins, receipt pins,
   exclusions, scientific flags, and claim fields.
8. The receipt schema is exactly
   `max11-g0163-g0140-stage-e-final4-source-audit-v1`; the producer's frozen
   claim and no-claim constants are copied exactly and enforced.
9. `cargo fmt --check`, the complete two-test suite, and
   `cargo clippy --locked -- -D warnings` pass in the sanitized isolated tree.
10. Two independent clean `cargo build --release --locked` builds are
    byte-identical to one another and to the frozen release binary.
11. The frozen producer's `--self-test` and sanitized `--preflight-static`
    pass. Full preflight and scientific mode are forbidden.
12. The receipt records every scientific/replay/execution/inspection flag as
    false and contains no scientific claim, observation, result, or output.

Any failed or indeterminate gate terminates the audit without a PASS receipt.
