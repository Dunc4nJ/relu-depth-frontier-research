# G-0153 Stage-D master source/custody audit — FAIL

## Verdict

**FAIL. No `SOURCE_AUDIT_RECEIPT.json` was emitted.** The frozen source does not
fail closed on the preregistered exact source-audit JSON schema: a one-field hostile
mutation from JSON Boolean `true` to JSON integer `1` is accepted for a required
check.

## Frozen binding

- Commit: `5b9fb81168d1a1f964b123b31edc3763439ecd7b`
- Subject: `artifacts/math/G-0140/stage_d_master/rank_aware_master_v1.py`
- SHA-256: `aa7ea5ca9174667ecae0c5e2d28d50e616b2da24d57f62d2026150c67f244935`
- Delegated validator SHA-256: `3f2dde3fdf2f458adc90f5d4e8ed2e5338013c95bab8b296d5136fb529a06838`
- Preregistration commits: initial `a3696e8`, pre-access clarification
  `af02117648e607895b6aba3ad5dddc1bfa07612d`

Working bytes and the frozen Git blob were identical regular-file bytes at audit
time. Both independently hashed to the required subject SHA-256.

## Minimal counterexample

Reproduce from the repository root:

```bash
.venv/bin/python artifacts/reviews/G-0153-g0140-stage-d-master-source/hostile_required_check_type_probe.py
```

The probe first submits the exact one-binding baseline and observes acceptance. It
then changes exactly one leaf:

```json
{
  "json_pointer": "/required_checks/exact_named_binding_contract",
  "baseline": true,
  "mutant": 1
}
```

The hostile JSON is parsed through the frozen strict JSON parser as Python type
`int`, but the frozen validator accepts it. Observed output (exit `1`, denoting the
audit failure):

```json
{"baseline_json_value":true,"baseline_python_type":"bool","differing_leaf_count":1,"hostile_fixture_accepted":true,"mutant_json_value":1,"mutant_python_type":"int","mutated_json_pointer":"/required_checks/exact_named_binding_contract","one_binding_count":1,"reason":"hostile JSON integer accepted as required Boolean","scientific_input_observed":false,"scientific_manifest_observed":false,"scientific_output_observed":false,"scientific_replay_run":false,"selector_sha256":"3f2dde3fdf2f458adc90f5d4e8ed2e5338013c95bab8b296d5136fb529a06838","subject_git_commit":"5b9fb81168d1a1f964b123b31edc3763439ecd7b","subject_path":"artifacts/math/G-0140/stage_d_master/rank_aware_master_v1.py","subject_sha256":"aa7ea5ca9174667ecae0c5e2d28d50e616b2da24d57f62d2026150c67f244935","validator_error":null,"verdict":"FAIL"}
```

## Cause and impact

The Stage-D source supplies its all-Boolean `SOURCE_AUDIT_CHECKS` object to the
delegated validator. That validator checks dictionary equality but does not check
that each received value is a Boolean. In Python, `1 == True`, including inside
dictionary equality. Thus strict JSON syntax and exact keys do not make the value
types exact.

This is not a cosmetic schema difference: an audit receipt can encode a required
check using a non-Boolean JSON scalar and still be accepted as the exact T1 PASS
contract. That contradicts preregistered item 2 (wrong scalar types must be
rejected) and the frozen source's `exact_named_binding_contract` claim. One
accepted hostile case is sufficient for FAIL; the source was not patched.

## Permitted checks run before the blocker

- `--self-test`: exit `0`; reported member and separator routes PASS.
- `--static-preflight`: exit `0`; exact frozen hashes reported; every future-input
  presence flag was `false`; `scientific_column_generation_run` and
  `scientific_result_written` were `false`.
- Imported selector, G-0135 master, and G-0135 result hashes matched the constants
  frozen in the subject.

Those checks do not cure the accepted hostile receipt. Following the preregistered
decision rule, the audit stopped at this decisive counterexample instead of
manufacturing an overall PASS from remaining green checks.

## Claim boundary and custody

No future G-0140 manifest or scientific Stage A/B/C/D output was opened. No
`--preflight` or default/scientific mode was run. No scientific result was written
or replayed. This FAIL says only that the exact frozen producer bytes did not earn
source/custody clearance under the fixed hostile-schema battery; it says nothing
about any unseen G-0140 mathematical result.

Consumer/gate: the orchestrator and the future G-0140 manifest admission gate.
Observed defect class: proof-contract type confusion in a required-checks object.
Retirement condition: supersession by new frozen producer/validator bytes and a new
outcome-blind source audit; this FAIL remains as historical custody evidence.
