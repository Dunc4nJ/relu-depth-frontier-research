# G-0141 preregistration — outcome-blind T1 source/custody audit of G-0140 Stage A

## Identity, timing, and frozen subject

- Registered `2026-08-31T18:24:52Z`, before opening any G-0140 Stage-A
  producer source, examining or invoking its release executable, writing an
  audit checker, or observing any G-0140 scientific manifest/output.
- Reviewer: `GoldenSnow` (Codex / GPT-5; same model lineage and same campaign,
  T1 only). The reviewer previously performed the G-0136 Stage-A source audit
  and G-0139 Stage-D result audit. This disclosed history prevents any T2 or
  clean-room-independence claim.
- Exact frozen subject commit:
  `1ee34276dcbbd35aedf090cb19bddf57283eb1d2`.
- Exact source objects to bind at that commit:
  `artifacts/math/G-0140/stage_a_pool/src/main.rs`,
  `artifacts/math/G-0140/stage_a_pool/src/engine.rs`,
  `artifacts/math/G-0140/stage_a_pool/Cargo.toml`, and
  `artifacts/math/G-0140/stage_a_pool/Cargo.lock`.
- Exact release executable object: the committed regular executable below
  `artifacts/math/G-0140/stage_a_pool/target/release/` corresponding to the
  package's declared binary target. Its exact path, Git object, mode, size,
  and SHA-256 will be recorded after this preregistration is frozen; resolving
  those facts does not alter the audit plan or acceptance rule.

This is a read-only W2 source/custody audit. The producer and its scientific
paths are immutable. Audit artifacts may be written only below
`artifacts/reviews/G-0141-g0140-stage-a-source/`.

## Exact audit question and claim boundary

Does the frozen Stage-A Pool128 producer, as source plus committed release
executable at the exact subject commit, fail closed on custody and admission,
implement the declared static and ancestor preflight contracts, and confine a
future run to an exclusive, mutation-detected, strictly validated publication
of the preregistered Stage-A manifest/output pair?

A positive verdict is only `PASS` for the inspected code/custody/preflight
contract at these exact bytes. It is not evidence that Stage A has run, that
any manifest or scientific output exists or is correct, that Pool128 is
complete or scientifically adequate, that a residual or MAX11 claim holds, or
that any claim is `INDEPENDENTLY_REPLAYED`, `REFEREED`, or `FORMALIZED`.

## Outcome-blindness and allowed execution surface

- `scientific_manifest_observed` is fixed to `false`.
- `scientific_output_observed` is fixed to `false`.
- No future G-0140 scientific manifest/output may be listed, opened, hashed,
  parsed, copied, created, or inferred from result content.
- The producer's scientific/default/run path may not be invoked. No solver,
  enumeration, sampling, Pool128 construction, or other science may run.
- The committed release executable may be invoked only in the three
  outcome-blind modes `--self-test`, `--preflight-static`, and
  `--preflight-ancestor`. A mode that emits or consumes scientific data is an
  immediate `FAIL` and the audit stops.
- Read-only Git/object, filesystem-metadata, hashing, ELF, and source review
  commands are allowed. A locked release rebuild in an isolated temporary
  copy is allowed only to test the source/executable compiled-byte custody
  contract; it may not run the producer or publish into the subject tree.
- Mutation probes may operate only on isolated temporary copies and may invoke
  only the same three allowed executable modes. All temporary mutations must
  be outside the repository and discarded after the probe.

## Frozen audit obligations

1. **Exact subject binding.** Resolve and record full commit identity,
   ancestry, path, Git object/mode, byte length, and SHA-256 for the four source
   objects and release executable. Reject symlinks, path escape, duplicate
   resolution, missing/non-regular objects, untracked substitution, or drift
   between entry and exit.
2. **Compiled-byte custody.** Establish how the executable binds the exact
   source/lock bytes and exact subject commit; check the binding both
   statically and through the allowed preflights. Where the contract promises
   reproducible bytes, perform a locked isolated release rebuild and require
   byte identity. Otherwise report the narrower custody actually established
   and fail if the producer claims stronger byte identity than it proves.
3. **Ancestor anchors.** Verify every required commit/object anchor exists,
   has the required ancestor relation to the exact subject, and is checked
   before any scientific path could be reached. Reject prefix-only or
   working-tree-only ancestry, stale embedded commits, and unchecked fallbacks.
4. **G-0139 admission logic.** Verify admission is pinned to the exact G-0139
   audit receipt/commit and requires its schema, `PASS` verdict,
   `CONSISTENT_RESIDUAL_T1` bounded result, expected subject/transitive hashes,
   outcome-aware/T1 disclosure, and no-claim boundary. Reject mere file
   existence, prose matching, partially checked fields, alternate receipts,
   or any conversion of G-0139 into T2/scientific truth.
5. **Strict input/manifest/output contracts.** Trace all parsers and
   serializers. Require exact schemas, required-key equality, canonical
   integers/strings, duplicate-key and unknown-key refusal, path containment,
   regular-file/no-symlink checks, deterministic ordering/serialization,
   census reconciliation, and digest verification. A future output must be
   bound to the exact producer, preregistration, admitted predecessor, and
   configuration without reading that future output in this audit.
6. **Exclusive publication.** Verify no-clobber/create-new semantics, same-
   directory temporary staging, fsync/close/rename discipline as claimed,
   refusal of pre-existing or aliased destinations, and no partial scientific
   artifact becoming the accepted publication after interruption.
7. **Mutation controls.** Require the built-in outcome-blind self-test to
   exercise accepting fixtures and must-fail mutations covering source or
   executable drift, wrong ancestor/admission receipt, schema/key/type/value
   changes, path/symlink escape, pre-existing publication targets, ordering or
   census corruption, and payload/digest mutation. Supplement only with
   isolated outcome-blind probes where a decision-bearing branch otherwise
   lacks evidence.
8. **Claim boundary.** Confirm every success/reporting string is bounded to
   source/custody/preflight readiness and cannot be read as a scientific
   result, completeness statement, theorem, independent replay, or T2 review.

## Fixed procedure and falsifiers

1. Freeze and push this preregistration before source inspection, audit code,
   or tests.
2. Inventory the exact subject tree and hash the five bound objects without
   accessing any scientific manifest/output.
3. Review both Rust source files and Cargo metadata line by line, tracing every
   reachable branch from each of the three allowed modes and the prohibited
   scientific entry point. Record obligation-level evidence with line/byte
   locators.
4. Run the release executable exactly once per honest allowed mode unless a
   diagnostic retry is required. Capture stdout, stderr, exit status, and
   before/after repository state. Run no other producer mode.
5. Perform only preregistered outcome-blind mutation probes needed to show a
   decision-bearing guard can fail. No mutation probe may reveal a scientific
   result.
6. Rehash all five bound objects at exit and verify the audit itself changed
   only its reserved directory.

Any reachable scientific execution during an allowed mode, any observation of
a future G-0140 manifest/output, any false custody/admission/ancestor binding,
any overwrite or partial-publication path, any strict-contract bypass, or any
decision-bearing hostile mutation accepted forces `FAIL`. Missing evidence or
an unexercisable load-bearing guard also forces `FAIL`; it is never rounded up
to confidence.

The final machine receipt must use schema
`max11-g0141-g0140-stage-a-source-audit-v1`, carry `verdict` as exactly
`PASS` or `FAIL`, set both outcome-observation booleans to `false`, and include
nested exact subject bindings. The report must state the T1/same-campaign
limitations and an obligation list regardless of verdict.
