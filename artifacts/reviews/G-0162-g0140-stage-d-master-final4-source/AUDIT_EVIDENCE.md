# G-0162 Stage-D final4 source-audit evidence

This evidence is source/custody-only. No G-0140 scientific manifest or Stage
A--E scientific output was opened. Full preflight and scientific/default modes
were not run, and no scientific output was created.

## Custody

- Frozen subject commit:
  `19107c5eed2cad00d48eff3dd9bea0c015ecce89`
- Frozen subject SHA-256:
  `1f4e7f3a141bfbfb7a090ee681bab649ba0cebc191021b112db0368fe2256581`
- Frozen subject Git blob:
  `f9f473e089ba362d9162c5ca03ae67e107c0a21a`
- Preregistration commit:
  `a264e1c7ae1e7df7ac13b38b85d2dad7abde93e0`
- Preregistration SHA-256:
  `83a04b4ae21845b4450a31a2b17b7ac2156f3cc9ccfebd3d46b0d4bc4c4d42f8`
- Imported Stage-C selector SHA-256:
  `f6cbb7b83f25ce88b6448ab363eb73bcb7bc4cb8427c167009c98ae0a06a60d3`
  at commit `f56b92ab8e13401ccd8a63d8c24137e16450d5ef`.
- Imported exact core SHA-256:
  `c84f259d393756c9ff658aab9a1488b145b9607a939dbccfce47069168b40a1a`
  at commit `ff579acd4dcad838a582cd6c8411fdec5650d94e`.

The target commit exists as a commit object, is the last commit modifying the
subject as of the preregistration, and is an ancestor of the preregistration.
The committed blob, sanitized checkout, and main-worktree subject bytes are
equal. The target commit changed only the subject path. Function-level AST
comparison against its parent found changes only in `input_snapshot_digest`
and `self_test`; every other function, including the mathematical protocol,
was identical.

## Sanitized execution boundary

Before source or runtime inspection, the detached audit checkout omitted all
five paths below, and they remained absent after every permitted command:

- `artifacts/math/G-0140/pool128_manifest_v1.json`
- `artifacts/math/G-0140/pool128_global_replay_v1.json`
- `artifacts/math/G-0140/pool128_coordinate_prices_v1.json`
- `artifacts/math/G-0140/pool128_exact_rank_selection_v1.json`
- `artifacts/math/G-0140/rank_aware_master_result_v1.json`

The project environment was CPython 3.13.7 with python-flint 0.9.0. Source
`py_compile`, `--self-test`, and `--static-preflight` passed. Static preflight
reported every future input absent, `scientific_column_generation_run=false`,
and `scientific_result_written=false`.

## Independent fixtures and hostile controls

- Independent TAB serialization fixture SHA-256:
  `9973c87a16e71a92d98c70278c07a46a3d224e103e643b2bc359e476dfc31fb9`.
- Independent retired-NUL serialization fixture SHA-256:
  `ab7b0f7fcd820a946bfa33d060317501b816a6aceb55d476c6379292ae7819dc`.
- The frozen Stage-D function equals the imported Stage-C selector on the TAB
  fixture and differs from the NUL fixture.
- Independent exact-Q member and complete-separator fixtures passed.
- The strict positive source-audit fixture passed; 25 malformed schema,
  binding, Boolean, observation, duplicate-key, and trailing-data controls were
  rejected.
- The exact required-check dictionary equals the frozen
  `SOURCE_AUDIT_CHECKS`, including
  `stage_c_snapshot_digest_contract_verified`, with no missing or extra key.

Reproduction harness:
`source_audit_tests.py` in this directory. It accepts only a sanitized root,
the main root for working-byte comparison, and the preregistration commit.
