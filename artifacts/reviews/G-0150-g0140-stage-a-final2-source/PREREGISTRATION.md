# G-0150 Stage-A final2 source/custody audit preregistration

- Auditor: SilverFalcon (Codex, GPT-5 family; fresh context)
- Preregistered: 2026-08-31T20:17:40Z
- Operator-supplied frozen subject selector: `b59c5f8` (full object ID deliberately unresolved until after this preregistration is committed and pushed)
- Gate type: bounded ENABLER source/custody audit; no mathematical or scientific result is being produced or rerun
- Intended consumer: the G-0150 producer's typed receipt-admission path and the root orchestrator adjudicating the frozen Stage-A gate
- Retirement condition: this document ceases to be an active gate after final G-0150 adjudication and remains immutable historical evidence

## Outcome-blind scope

At the time of writing I have not opened the subject source, manifest, lockfile, executable, producer receipt schema, or any G-0140 scientific manifest/input/output, and I have not run a subject audit check. The post-preregistration audit is restricted to these operator-named Stage-A paths:

1. `artifacts/math/G-0140/stage_a_pool/src/main.rs`
2. `artifacts/math/G-0140/stage_a_pool/src/engine.rs`
3. `artifacts/math/G-0140/stage_a_pool/Cargo.toml`
4. `artifacts/math/G-0140/stage_a_pool/Cargo.lock`
5. `artifacts/math/G-0140/stage_a_pool/target/release/g0140-stage-a-pool128-global-replay`

The only permitted executable modes are `--self-test`, `--preflight-static`, and `--preflight-ancestor`. I will not invoke default/scientific execution, any other preflight mode, or open/create a G-0140 scientific manifest, input, or output. I will not modify producer code or historical artifacts.

## Predeclared audit questions and falsifiers

A PASS is admissible only if every applicable item below is supported by exact bytes and observed behavior. Any blocker, ambiguity, schema mismatch, unexpected mutation, or failed must-pass probe forces an immutable, non-consumable FAIL receipt.

### Frozen-source and custody binding

- Resolve `b59c5f8` to a full commit only after this preregistration commit is pushed; prove the four text files and the canonical executable exist at that commit.
- Hash frozen Git bytes and current working-tree bytes for all five named bindings and require equality at the audited endpoint.
- Bind the preregistration bytes, preregistration commit, audit commit, subject commit, canonical executable path, executable digest, and exact five path/digest bindings without permitting recursive or basename-only substitutes.
- Confirm the executable is the producer-declared canonical executable, that compiled-in custody/schema constants match source, and that the audit does not silently accept a rebuilt or displaced lookalike.
- Rehash the five bindings at the end and require stability; test overwrite refusal and error/exit-status propagation.
- Recheck the operator-identified prior G0141 repairs rather than assuming their continued presence.

### G0146-F1 exact-deny schema probes

The receipt consumer must accept exactly the producer-defined typed schema and reject all deviations. I will independently probe:

- exactly five named bindings, with no omitted, added, renamed, recursively discovered, or displaced lookalike path;
- a missing required named path even when a correctly digested decoy exists elsewhere;
- duplicate occurrences of any named path;
- unknown top-level/envelope fields and unknown nested subject/binding fields;
- the prohibited `audit_git_commit` field;
- duplicate JSON object keys at every relevant level;
- trailing non-whitespace data after the JSON value;
- wrong values/types/nulls/order assumptions where the producer's typed contract makes them relevant.

### Admission, execution, and failure semantics

- Inspect the producer's structs/constants before constructing any receipt; the receipt will contain precisely the defined fields and no extras.
- Require exact claim and no-claim strings, exact reviewer/preregistration fields, exact required-check names and truth values, and the exact five bindings declared by the producer.
- Exercise only non-scientific self-test/static/ancestor paths in isolated temporary fixtures; confirm malformed or adversarial receipts fail closed and propagate nonzero status and diagnostics.
- Confirm overwrite refusal for an already-existing receipt and that no failed path leaves a consumable partial receipt.

## Decision rule and reporting contract

The verdict has two possible shapes only:

- `PASS`: emit the producer's exact typed `SOURCE_AUDIT_RECEIPT.json`, with all required checks truthfully satisfied and no additional keys.
- `FAIL`: emit the producer's exact typed immutable non-consumable failure shape if one is defined; otherwise do not fabricate a PASS-compatible receipt and record the blocking evidence in the minimum operator-requested review artifact.

Neither outcome establishes a ReLU-depth theorem, lower bound, exhaustive Stage-A scientific result, or correctness beyond this frozen source/custody and consumer-admission gate.
