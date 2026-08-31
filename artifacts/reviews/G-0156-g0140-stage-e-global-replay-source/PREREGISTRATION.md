# G-0156 Preregistration — G-0140 Stage E Global Replay Source-Custody Audit

## Outcome-blind freeze declaration

This protocol is written before reading, inspecting, hashing, executing, or otherwise accessing
any frozen subject byte. It is based only on the audit handoff. The audit begins only after this
file is committed and that commit is confirmed on the remote.

The audit is a fresh-context, same-lineage, read-only source audit. It adjudicates the frozen
implementation and its custody boundaries; it does not create scientific evidence, repair the
subject, rerun the research program, or infer a scientific result.

## Frozen subject binding

- Subject commit: `af608ad38dde2a9b4d25aaefca8bd8407c9a0699`
- Subject root: `artifacts/math/G-0140/stage_e_global_replay/`
- `Cargo.toml`: `a701d142aeb88cae15d30997dcc3039b5fee105cb3c26621fec9ddcca552f5c9`
- `Cargo.lock`: `eaaa98ae381bed0f1b48f27e5ca7c3841c2e6e1b8fa6b07e09cff11d172ef2d0`
- `src/main.rs`: `e2a7121aab0edcea463031ba09ab75bbd9441a443bcf819aa5d653d1db17e2a6`
- `src/engine.rs`: `b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c`
- Release executable `target/release/g0140-stage-e-global-replay`:
  `a2151ab92ad732fecaa48d41ebfa8e574db93720393b8afe72c29ca170f1aeb8`

Each digest is SHA-256 over the exact named file. A byte-identical file at any other path does not
satisfy a named binding. A missing, extra, displaced, or multiply occurring named binding is a
failure, not a repair opportunity.

## Audit question and decision rule

Does the frozen Stage E implementation, at the exact binding above, fail closed at its source and
custody boundaries; encode semantic truth as `true -> 1` and `false -> 0`; reject the named
structural mutants; preserve all upstream and end-of-run custody gates; and expose only the
permitted source-only self-test/static-preflight behavior during this audit?

The positive result is eligible only if every required boolean below is supported by direct,
reproducible evidence and is `true`, all five named SHA-256 bindings and the subject commit bind
exactly, every permitted command succeeds in its intended direction, every negative control fails
in its intended direction, and no prohibited access or mode occurs. Otherwise the verdict is FAIL
or BLOCKED; ambiguity is never rounded up to PASS.

If eligible, the typed receipt must use:

- schema: `max11-g0156-g0140-stage-e-global-replay-source-audit-v1`
- result: `SOURCE_CUSTODY_AUDIT_PASS_T1`
- evidence class: `T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT`

These strings prescribe the shape of a possible passing receipt; they do not preregister its
outcome.

## Required booleans

The receipt must contain these exact boolean keys, with no omission or alias:

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
12. `engine_byte_identity_with_stage_a_verified`
13. `g0155_stage_d_source_audit_gate_verified`
14. `scientific_output_commit_chain_gate_verified`
15. `dynamic_stage_d_member_contract_verified`
16. `global_zero_and_residual_branches_verified`
17. `complete_label_census_and_end_rehash_verified`
18. `overwrite_refusal_verified`
19. `prohibited_scientific_modes_not_run`

## Falsifiers and hostile matrix

The implementation must be tested in both semantic directions: a canonical true predicate must
produce integer `1`, and a canonical false predicate must produce integer `0`. Exit status alone
does not establish the mapping. The structural negative matrix is fixed before inspection:

- move an otherwise correct named binding beneath a recursive/displaced path;
- supply a correct decoy while omitting the exact named binding;
- supply duplicate occurrences of one required path;
- add an unknown envelope field;
- add or substitute an `audit_git_commit` field;
- duplicate a JSON object key;
- append trailing JSON data after an otherwise valid value;
- break each upstream custody link named by the required booleans;
- exercise both the global-zero and residual/nonzero branch;
- make the label census incomplete or make the final rehash disagree;
- target an already-existing output to test overwrite refusal.

Each negative control must be rejected before acceptance or output replacement. Synthetic
structural envelopes may be used only to exercise these source/custody parsers and branches; no
scientific input, result, manifest, or provenance record may be fabricated.

## Permitted evidence acquisition

Only after remote preregistration freeze, the auditor may:

1. resolve the subject commit without checking it out over the shared worktree;
2. hash and inspect every byte of the five named bound files, including static review of every
   source line;
3. run source-only checks, tests, and isolated rebuilds against exactly those bound sources and
   lockfile, with build output directed outside the frozen subject tree;
4. run the bound release executable only as `--self-test` and `--preflight-static`;
5. run a focused hostile harness over structural/custody-only fixtures and record exact commands,
   exit statuses, stdout, and stderr without suppressing stderr;
6. inspect Git metadata and exact historical source bytes only as necessary to verify the frozen
   commit and the explicitly named upstream source/audit/commit-chain bindings encoded by the
   Stage E source.

Evidence must distinguish source inspection, compiled-source behavior, and execution of the
prebuilt release executable. A producer self-test is a control, not independent proof; required
booleans also need hostile or static corroboration where applicable.

## Prohibited actions

The auditor must not access or execute any future G-0140 manifest; any G-0140 Stage A, B, C, D,
or E scientific artifact; full preflight; or any scientific mode. The auditor must not fabricate
scientific inputs, edit frozen subject bytes, overwrite scientific output, weaken a check, infer
success from a label, or use a successful rebuild to substitute for the prebuilt executable's
binding. Scientific results and their values are outside the audit and must not be reported.

If a permitted command attempts to read a prohibited scientific artifact, the attempt is recorded
and the audit cannot pass, even if the command exits successfully. `prohibited_scientific_modes_not_run`
means both that the auditor did not invoke such a mode and that the captured permitted executions
show no prohibited artifact access.

## Stop and reporting rules

- No subject-byte access occurs until this preregistration commit is confirmed on the remote.
- Any binding mismatch, incomplete evidence, non-discriminating control, unexpected write,
  prohibited access, or unavailable required check prevents PASS.
- No failure is repaired in place. The failing command, output, and relevant bytes are preserved
  in the audit path, and the outcome is reported as FAIL/BLOCKED.
- Retries may diagnose harness mistakes but may not change the frozen subject or relax the matrix;
  all retries are recorded.
- A passing receipt is written only after the full matrix closes. It contains the exact schema,
  result, evidence class, frozen bindings, required booleans, command/evidence digests, limitations,
  and a statement that prohibited scientific modes were not run.
- The final commit contains only
  `artifacts/reviews/G-0156-g0140-stage-e-global-replay-source/**`, is pushed, and is reported by
  commit and receipt SHA-256.

## No-claim boundary

Even a passing audit establishes only T1 same-lineage confidence in the frozen Stage E source and
its tested custody behavior. It does not independently reproduce, validate, reveal, or upgrade any
G-0140 scientific result; it does not constitute T2 review; and it does not authorize access to or
execution of prohibited scientific artifacts or modes.
