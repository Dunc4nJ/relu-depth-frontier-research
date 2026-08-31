# G-0146 preregistration — final G-0140 Stage-A source/custody audit

Date: 2026-08-31
Reviewer: GoldWaterfall (fresh Codex context; same model lineage, therefore T1 only)
Mode: W2 read-only audit, mathematics domain

## Decision use and boundary

This is a legitimate bounded gate, not a capability claim. The G-0146 orchestrator and the
G-0140 ancestor-preflight admission path consume the result before admitting the frozen Stage-A
producer as source/custody-cleared. It responds to the observed G-0141 failures in semantic
admission and Git/working-byte custody. It is immutable and single-use for the frozen subject
below; any changed bound byte requires a new audit.

The maximum possible conclusion is T1 source/custody clearance for exact producer bytes. This
audit cannot promote a mathematical claim, validate a candidate, validate a scientific run, or
establish the correctness/completeness of any Stage-A scientific result.

## Frozen subject

- Git commit: `2157fd2a9776277354c45487ae1cbc0670ffc9b8`
- Primary source: `artifacts/math/G-0140/stage_a_pool/src/main.rs`
- Expected primary-source SHA-256: `5fd91773b1e16cc54d09c20c72ef729a333bef4c8b6804f24a525a4be8258790`
- Release executable: `artifacts/math/G-0140/stage_a_pool/target/release/g0140-stage-a-pool128-global-replay`
- Expected executable SHA-256: `366acb1e70a2699e3a26089263173f142af021b4a6379632e4786d460bf00f4a`
- Additional mandatory bindings: the exact engine source resolved by the frozen crate, plus
  `artifacts/math/G-0140/stage_a_pool/Cargo.toml` and
  `artifacts/math/G-0140/stage_a_pool/Cargo.lock`, all at the same commit.

The final receipt must contain five nested `{path,sha256}` bindings: primary source, engine source,
Cargo manifest, Cargo lockfile, and release executable. For every binding, the commit blob/object
and working bytes must be equal.

## Outcome-blindness and prohibited observations

This preregistration is committed and pushed before source inspection or audit execution. During
the audit I will not open any future G-0140 scientific manifest, any candidate/scientific input,
or any Stage-A scientific output. I will not execute scientific replay. The only permitted runtime
modes are self-test, static preflight, and ancestor preflight. Any accidental scientific
observation is a blocker and forces an honest FAIL.

## Predeclared obligations and falsifiers

The verdict is PASS if and only if every obligation below is supported by exact command evidence.
Any failure, ambiguity, skipped hostile control, unexpected permissiveness, or custody mismatch is
a blocker and yields FAIL without a consumable PASS-shaped substitute.

1. **Frozen-object and five-file custody.** The named commit must exist as the inspected commit.
   Each of the five required working files must be a regular, non-symlink file whose bytes equal
   its committed Git blob. The two supplied SHA-256 values must match exactly; the other three
   hashes will be independently computed and recorded. A changed working byte, missing blob,
   wrong path, symlink/path escape, or executable/source substitution falsifies clearance.
2. **Executable/source binding.** Static inspection must show how the frozen executable binds or
   checks the exact source/crate bytes it claims to implement. A release binary with the expected
   name but unbound/different compiled bytes, an unchecked stale binary, or a check that trusts a
   filename/receipt assertion instead of bytes falsifies clearance.
3. **Exact G-0139 semantic and custody admission.** The ancestor admission path must positively
   require the intended G-0139 receipt and reject, independently: wrong subject Git commit; wrong
   evidence class; wrong lineage or outcome-awareness; widened/different claim boundary; false or
   missing custody equality; and wrong/missing source-audit anchor. Each field must be compared by
   exact semantics, not merely be present or truthy.
4. **G-0140 manifest Git/working equality.** Before any permissible preflight can admit a G-0140
   manifest, the manifest's current working bytes must equal its blob at the bound commit. A valid
   committed object paired with modified working bytes must be rejected.
5. **Strict structured-data parsing.** Duplicate JSON keys, trailing JSON values/garbage,
   wrong primitive types, unknown or lookalike field names, missing required nested bindings,
   flattened substitutes, and extra ambiguity-bearing fields must fail closed. Parser coercion or
   last-key-wins behavior on a security-relevant record falsifies clearance.
6. **Receipt identity and nested bindings.** Renamed/copycat receipts, correct-looking receipts for
   another subject, wrong nested paths, wrong nested hashes, missing nested fields, and internally
   inconsistent path/hash pairs must be rejected. Admission may not rest on a schema/verdict/result
   string alone.
7. **Mutable-input drift / TOCTOU.** Every admitted mutable input must be rehashed at the point it
   matters or consumed from an immutable snapshot already bound by digest. A preflight that can
   validate one version and later consume changed bytes without detection falsifies clearance.
8. **No self-reference or circular custody.** The G-0146 PASS receipt must not contain an
   `audit_git_commit` field and may not certify itself. Producer admission must anchor to prior,
   independent exact-byte evidence rather than a circular chain of mutually asserted receipts.
9. **Fail-closed behavior.** Missing, unreadable, malformed, semantically wrong, or command-failing
   prerequisite records must produce a nonzero rejection. Zero-test success, ignored stderr,
   warnings-with-success, panic-as-acceptance, and skipped checks falsify clearance.
10. **Mode and claim containment.** Tests must not read scientific manifests/inputs/outputs or run
    replay. Evidence remains T1 same-lineage, outcome-blind source/custody evidence only.

## Hostile-control matrix

Controls will operate only on temporary copies or synthetic fixtures, never by editing producer
or historical receipt artifacts.

| Attack | Required response |
|---|---|
| One-at-a-time mutation of each G-0139 semantic/custody field | Nonzero rejection naming the violated obligation |
| Replace a required G-0139 nested source binding while retaining PASS-like top-level strings | Nonzero rejection |
| Modify G-0140 manifest working bytes while retaining its committed blob | Nonzero rejection |
| Duplicate security-relevant JSON keys with conflicting values | Parse/admission rejection, never last-key-wins |
| Append a second JSON value or trailing non-whitespace | Parse/admission rejection |
| Wrong types, Unicode/lookalike keys, missing nested objects, extra top-level ambiguity | Parse/admission rejection |
| Swap/copy/rename a receipt with plausible schema/verdict/result | Nonzero subject-identity rejection |
| Wrong path or hash in each of the five nested producer bindings | Nonzero rejection |
| Change a previously validated mutable fixture before its use | Drift detected or immutable-snapshot design demonstrated |
| Missing/unreadable/malformed prerequisites and unsupported runtime mode | Nonzero fail-closed response |
| Deliberately defective self-test fixtures | Each defect is detected; a control that never turns red does not count |

Positive controls must also pass for the exact permissible frozen fixtures; hostile controls are
not credited if they merely make every invocation fail.

## Exact PASS contract

Only if all obligations pass, `SOURCE_AUDIT_RECEIPT.json` will contain:

- `schema`: `max11-g0146-g0140-stage-a-final-source-audit-v1`
- `verdict`: `PASS`
- `result`: `SOURCE_CUSTODY_AUDIT_PASS_T1`
- `evidence_class`: `T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT`
- `claim_boundary`: `T1 source/custody clearance for the exact frozen Stage-A producer bytes only; no scientific manifest, input, or output was observed, no scientific replay was run, and no mathematical claim is promoted.`
- all four scientific-observation/replay booleans set to `false`
- `subject.git_commit`: `2157fd2a9776277354c45487ae1cbc0670ffc9b8`
- `subject.commit_object_and_working_bytes_equal_for_all_bindings`: `true`
- nested `{path,sha256}` objects for all five exact subject files
- no self-referential `audit_git_commit` field

If any obligation fails, the receipt will retain the same schema but honestly report FAIL and the
exact blockers; it will not imitate the producer's declared consumable PASS contract.
