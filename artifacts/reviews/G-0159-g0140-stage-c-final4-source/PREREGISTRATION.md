# G-0159 preregistration: G-0140 Stage-C final4 source-custody audit

This audit is preregistered before opening or reading the Stage-C selector subject, the current G-0140 manifest, any current or superseded Stage-A result, or any A-E scientific output.

## Scope and blindness covenant

- This is a fresh, outcome-blind, source-only custody audit.
- No scientific input or scientific output will be read, produced, interpreted, or certified.
- The audit may inspect source, executable, build/test/launcher custody, prerequisite source-audit receipts, Git history, blob identity, and deliberately constructed source-only hostile controls.
- It will not execute the scientific selector in `--preflight` or default mode and will not create selector outputs.
- `--static-preflight`, if exercised, will run only in sanitized isolation with the scientific manifest and all scientific outputs absent.
- This audit is valid only for the exact bytes and Git identities bound below. If any bound byte changes, this audit can never be reused for the changed bytes; a new outcome-blind audit is required.

## Exact six-subject byte bindings supplied before inspection

| Binding name | Expected identity |
|---|---|
| `selector` | path `artifacts/math/G-0140/stage_c_selector/complete_matrix_rank_selector_v1.py`; SHA-256 `f6cbb7b83f25ce88b6448ab363eb73bcb7bc4cb8427c167009c98ae0a06a60d3`; last-modifying commit `f56b92ab8e13401ccd8a63d8c24137e16450d5ef` |
| `native_source` | SHA-256 `198262e449c901f70b1e26cd260cbd5ade4e6eaf2868659e4cfd59a1ab72d9c7` |
| `native_executable` | SHA-256 `207fcf88fe3f89c8119bd6b38037d9f0919165eecf04b48d1b0aaae039843171` |
| `build_receipt` | SHA-256 `5157c020cc343de6bb891fb339a1027a9f8f3059aa03ea2a32722bc13d0fff76` |
| `native_test` | SHA-256 `5d2b920f06100a2a7bd4069ebe4f009d4c2ba8aecea8872c9d4c58abe9296b94` |
| `launcher` | SHA-256 `786b42f28d4720ca2578de78a3e312ce0186b8609d2b2c9c85c8f76bdd409d78` |

The audit receipt will expose these as six separate named bindings, including exact repository paths, Git/blob custody, and dependency terminal paths once those source-only facts are inspected.

## Preregistered prerequisite contract

The exact G-0158 Stage-B final3 source-audit receipt must be committed and pushed before G-0159 can pass. Its exact path, schema, claim/no-claim constants, scientific flags, and required-check set will be validated. In particular, the prerequisite must truthfully assert `g0139_subject_and_exact_fixed_inputs_gate_verified`; retired G-0151, missing, false, integer-valued, and displaced-control substitutions must be rejected.

The G-0139 gate will be checked against the exact candidate fixed-map repair and hostile missing, wrong, and displaced-decoy mutants. The exact complete-basis and full-pool dependency terminal paths will be checked for byte identity and Git/blob custody.

## Preregistered validation and decision rule

The audit implementation will use schema `max11-g0159-g0140-stage-c-final4-source-audit-v1`. Its required checks are the prior Stage-C source-audit check set plus:

- `g0139_subject_and_exact_fixed_inputs_gate_verified`
- `stage_b_final3_source_audit_exact_contract_validated`

Validation must include Python compilation, the source auditor's `--self-test` with 36 hostile controls, the native oracle, and the sanitized source-only `--static-preflight`. PASS is permitted only if every required check is exactly true, all six bindings and prerequisite contracts match exactly, Git/blob and pushed-branch custody hold, claim/no-claim constants are exact, and all scientific-read/scientific-run/scientific-output flags are false. Otherwise the receipt must be non-PASS.

No Stage-C subject file will be edited by this audit.
