# G-0157 / G-0140 Stage-E final2 source-custody audit preregistration

- Auditor identity: `PurpleThrush` (`codex`, GPT-5)
- Audit role: fresh, outcome-blind source-custody auditor
- Audit schema required on success: `max11-g0157-g0140-stage-e-final2-source-audit-v1`
- Required success result: `SOURCE_CUSTODY_AUDIT_PASS_T1`
- Frozen subject commit: `664b95445365600aadc5a876edc6b7e97b06c1e4` on `origin/master`
- Freeze rule: this preregistration is committed, pushed, and verified from the remote before any subject byte is read, inspected, hashed, or executed.

## Handed-off bindings (unverified at preregistration time)

These are hypotheses to test, not observations:

| Subject member | Expected SHA-256 |
|---|---|
| `Cargo.toml` | `a701d142aeb88cae15d30997dcc3039b5fee105cb3c26621fec9ddcca552f5c9` |
| `Cargo.lock` | `eaaa98ae381bed0f1b48f27e5ca7c3841c2e6e1b8fa6b07e09cff11d172ef2d0` |
| `src/main.rs` | `d239df56d6fee876a6eb8b12ecbc5e8fead501d7847010aaa30f11438bd001b4` |
| `src/engine.rs` | `b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c` |
| bound release executable (path to be resolved from the frozen tree) | `b4e87e38dbde333890b84aa8c567c75d5327af691706bc653dea6a85f2a87ff4` |

No handed-off digest will be treated as verified until independently recomputed from the frozen commit after the preregistration freeze.

## Claim boundary and constants

The audit is limited to source custody and deterministic rebuild equivalence. It does not validate, reproduce, inspect, or make a scientific claim. The evidence-class, claim-boundary, and no-claim constants encoded by the frozen source will be transcribed verbatim only after the freeze and must be preserved exactly in the strict receipt. Their semantic requirements are preregistered as follows:

1. evidence class remains source-custody / implementation evidence only;
2. the claim boundary excludes scientific-result validation;
3. the no-claim statement must explicitly prevent treating this audit as evidence for a scientific conclusion.

Any source constant that expands the audit into scientific evidence is a failure.

## Required checks and decision rule

After the remote freeze, I will enumerate every field of the frozen source's `StageESourceAuditChecks` definition verbatim. Success requires the strict receipt to include every such field exactly once and requires every field to be `true`; an omitted, duplicated, renamed, non-Boolean, or false field is an automatic `NO-GO`.

The following obligations are independently preregistered even if the implementation uses different field names:

1. the frozen commit resolves exactly to the commit above and is reachable from the stated remote ref;
2. each handed-off file/release digest matches independently recomputed SHA-256 evidence from the frozen commit;
3. committed-blob checks remain present and enforced for every bound source or receipt object required by the source contract;
4. exact A/B/C/D receipt bindings remain present and enforced, including exact paths and digests where the contract requires them;
5. the required ancestry chain remains enforced as manifest -> A -> B -> C -> D, with no skipped, reversed, or merely set-membership substitute;
6. `scientific_outputs_excluded_from_manifest_bindings` exists as an exact required Boolean and is true;
7. both the direct manifest-binding set and its transitive union reject every one of the five A/B/C/D/E scientific-output paths individually;
8. those rejection checks do not remove or weaken the exact A/B/C/D receipt bindings, committed-blob checks, or manifest -> A -> B -> C -> D ancestry checks;
9. a clean `--locked` release rebuild is byte-identical to the bound release executable;
10. the permitted cargo test suite passes;
11. both the bound and rebuilt executables pass `--self-test` and `--preflight-static`;
12. the source emits the required schema and result constants exactly, with the evidence-class, claim-boundary, and no-claim constants unchanged.

The manifest exclusion test is conjunctive: all ten per-path assertions (five paths x direct/transitive views) must be demonstrated. Aggregate-only evidence is insufficient. The hostile harness will mutate or synthesize one condition at a time and must demonstrate rejection rather than merely searching for reassuring strings.

`GO` is permitted only if every required check above and every verbatim `StageESourceAuditChecks` Boolean passes. Otherwise the outcome is `NO-GO`; there is no partial-pass category and unexpected tooling errors are not converted into positive evidence.

## Frozen-subject protocol

1. Resolve the full commit and remote reachability using Git object/ref metadata after this preregistration is remotely confirmed.
2. Materialize only the frozen subject members needed for this source-custody audit into an isolated temporary directory, directly from the commit object. Never substitute mutable working-tree bytes.
3. Hash the exact frozen blobs and bound release, recording byte counts and SHA-256 values.
4. Inspect `StageESourceAuditChecks`, the receipt schema/result constants, evidence-class/claim-boundary/no-claim constants, manifest binding construction, committed-blob enforcement, exact A/B/C/D bindings, and ancestry enforcement.
5. Build a focused, independent hostile harness under this review directory. It must exercise each A/B/C/D/E output path against both direct and transitive manifest-binding logic while retaining affirmative tests for exact A/B/C/D receipt bindings, committed blobs, and ordered ancestry.
6. Perform a clean locked release rebuild in isolation and compare the rebuilt executable byte-for-byte with the frozen bound release.
7. Run only the permitted tests and executable modes listed below.
8. Materialize a strict machine-readable receipt and concise focused evidence. Recompute and report the receipt SHA-256.

## Permitted and forbidden operations

Permitted subject operations after the freeze:

- read-only Git object/ref/tree inspection of the frozen commit;
- exact extraction and hashing of the bound source-custody subject members;
- clean Cargo build/test operations with the lockfile enforced;
- execution of the bound and rebuilt executables only with `--self-test` and `--preflight-static`;
- static source analysis and an independent synthetic hostile harness scoped to the source-custody checks.

Forbidden throughout this audit:

- opening, reading, hashing, statting for content analysis, copying, or creating the future G-0140 manifest;
- opening, reading, hashing, statting for content analysis, copying, or creating any future G-0140 scientific output A/B/C/D/E;
- executing full preflight, scientific, generation, experiment, or other unlisted subject modes;
- editing the frozen subject or using mutable working-tree source as evidence;
- inferring scientific correctness from source-custody success.

Path strings for the forbidden objects may be observed inside the frozen source solely to audit exclusion logic. The actual objects must never be accessed. Hostile cases must use synthetic temporary paths and synthetic bytes that are not the future manifest or scientific outputs.

## Planned receipt shape

The final strict receipt will be a single JSON object with no duplicate keys and at least:

- exact `schema`, `result`, frozen commit, remote-ref, and auditor identity;
- exact verified subject paths, SHA-256 digests, byte counts, Git blob IDs, and committed-blob status;
- the frozen source's verbatim evidence-class, claim-boundary, and no-claim constants;
- a verbatim-keyed `StageESourceAuditChecks` object containing every required Boolean;
- explicit per-path direct/transitive exclusion evidence for scientific outputs A/B/C/D/E;
- exact A/B/C/D receipt-binding and ordered-ancestry evidence;
- locked rebuild digest/equality evidence;
- exact permitted command/mode outcomes;
- hostile-harness cases and outcomes;
- forbidden-object non-access attestation;
- final `GO`/`NO-GO` decision.

This document fixes the audit method and pass/fail rule before outcome observation.
