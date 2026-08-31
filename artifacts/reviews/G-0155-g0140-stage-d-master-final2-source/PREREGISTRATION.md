# G-0155 preregistration — G-0140 Stage D master final2 source/custody audit

- Preregistered UTC: `2026-08-31T21:49:29Z`
- Reviewer: `CoralRabbit`
- Reviewer program: `codex`
- Review posture: fresh-context, same-model-lineage, outcome-blind source/custody audit
- Frozen subject commit: `69a3449c7bc291f283c10c669e5d39f2a1212782`
- Frozen subject path: `artifacts/math/G-0140/stage_d_master/rank_aware_master_v1.py`
- Expected frozen subject SHA-256: `6112c55f943c20acd80402a9800db581c1ee6d5caf35c2f418d2a52cf09ad03e`
- Receipt schema: `max11-g0155-g0140-stage-d-master-final2-source-audit-v1`
- Passing result literal: `SOURCE_CUSTODY_AUDIT_PASS_T1`
- Evidence class literal: `T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT`

## Frozen claim boundary

`T1 source/custody clearance for the exact frozen G-0140 reopened-master producer bytes only; no scientific manifest, input, or output was observed, no scientific column-generation run was executed, and no mathematical claim is promoted.`

## Frozen no-claim boundary

`This source audit does not adjudicate any future G-0140 scientific manifest or result and does not establish family membership, family nonmembership, a MAX11 identity, a lower bound, unrestricted nonrepresentability, minimality, an all-n theorem, refereed status, formalization, or a Lean theorem.`

## Scope and access firewall

This is a source/custody-only audit of the exact frozen producer bytes and the exact imported core bindings those bytes declare. It will not access any future G-0140 scientific manifest, scientific input, or scientific output. It will not execute a scientific replay, scientific column-generation run, preflight over future data, or any other mode requiring future scientific artifacts. Only static inspection and explicitly source-audit-safe self-test/static modes are authorized.

The audit may inspect only after this preregistration is committed and pushed:

1. the frozen subject blob at the commit and path above;
2. exact dependency blobs that the frozen subject itself declares as imported exact-core bindings, limited to resolving and auditing those bindings;
3. ordinary Git object/custody metadata needed to bind the frozen blobs;
4. isolated temporary copies or mutants derived solely from those authorized source bytes and self-test fixtures.

## Frozen required checks

Every following exact JSON key must be present with the JSON boolean value `true` for a PASS receipt:

1. `exact_named_binding_contract`
2. `displaced_recursive_lookalikes_rejected`
3. `correct_decoy_with_missing_named_binding_rejected`
4. `unknown_envelope_fields_rejected`
5. `audit_git_commit_rejected`
6. `duplicate_json_keys_rejected`
7. `trailing_json_data_rejected`
8. `imported_exact_core_binding_verified`
9. `future_input_gate_verified`
10. `exact_column_generation_protocol_verified`
11. `member_and_separator_fixtures_verified`
12. `committed_blob_custody_verified`
13. `producer_self_test_passed`
14. `producer_static_preflight_passed`
15. `prohibited_scientific_modes_not_run`

The receipt must also bind `reviewer_program` to `codex`, bind `same_model_lineage` and `fresh_context` to the JSON boolean `true`, and bind every `scientific_*` observation/execution flag to the JSON boolean `false`. Integers, strings, nulls, containers, or other truthy/falsy substitutes do not satisfy any boolean field.

## Preregistered audit procedure

1. Resolve the frozen subject from the named commit, verify its SHA-256 before interpretation, and reject working-tree substitution.
2. Extract the subject's declared exact-core import bindings, resolve only those frozen dependency blobs, and verify their declared paths, commits/digests, and binding identities without following or reading any scientific-data path.
3. Perform a static fail-closed source review of the named-binding contract, decoy/lookalike refusal, envelope schema closure, Git-commit custody, future-input gate, exact column-generation protocol, member/separator fixtures, and mode dispatch.
4. Run only the producer's source-audit-safe self-test and static source-audit-safe mode(s). Never invoke scientific or future-artifact preflight/replay modes.
5. Exercise the strict JSON contract with isolated mutants. At minimum: replace a required JSON `true` with numeric `1`; replace an expected JSON `false` with numeric `0`; try string booleans, `null`, arrays, and objects; delete a required key; add an unknown key; duplicate a key; append trailing JSON data; alter the audit Git commit; displace a required recursive named binding with a lookalike; and provide a correct decoy while omitting the required named binding. Each material mutant must be rejected nonzero/fail-closed.
6. Verify that a positive source-audit-safe fixture is accepted, so mutation rejection is not a reject-all implementation.
7. Emit the exact PASS receipt only if the frozen blob/digest/custody bindings, every required check, strict boolean contract, and all permitted self-tests/static checks satisfy the embedded validator. Otherwise emit only a minimal FAIL receipt naming the failed check(s).

## Preregistered adjudication rule

PASS is limited to the frozen claim boundary above. It cannot promote a mathematical or scientific claim. Any forbidden future-artifact access or scientific execution is itself disqualifying and forces FAIL. Any ambiguity, skipped required check, unavailable declared dependency, digest mismatch, permissive boolean coercion, partial mode, or validator fail-open forces FAIL rather than an inferred PASS.

## Process-artifact creation gate

- Boundary: process artifact; runtime does not branch on it.
- Consumer: the G-0155 orchestrator/adjudicator explicitly requesting the independent audit.
- Gate: no G-0140 Stage D frozen source/custody clearance may be accepted without this precommitted audit contract.
- Observed defect class: the dispatched repair targets strict JSON boolean coercion and other material fail-open source/custody paths; preregistration prevents post-outcome criterion selection and self-certification.
- Deletion/retirement condition: this preregistration retires as an active gate when G-0155 is adjudicated against the exact frozen commit, while remaining only as immutable custody evidence.
- Opportunity cost: the highest-priority ready work is this bounded independent audit; the minimum preregistration directly gates it.
- Verdict: `LEGITIMATE GATE`.
