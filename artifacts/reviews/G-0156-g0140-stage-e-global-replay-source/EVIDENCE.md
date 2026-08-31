# G-0156 focused evidence and honesty inventory

## Verdict

No blocker was found. The exact frozen Stage-E source-custody subject at
`af608ad38dde2a9b4d25aaefca8bd8407c9a0699` passed the preregistered T1 source-only audit.
No future G-0140 scientific manifest or Stage A/B/C/D/E scientific artifact was opened, full
preflight was not run, and scientific mode was not run.

## Frozen custody

The preregistration was pushed and confirmed at
`15a9d2cca19532593b76d91b62b9da92fed58720` before the first subject-byte access. Its SHA-256 is
`3f4ffa51b205d0c2d76c7bf9968c1254ecff7e81f612a9d2dcd8b32e6903fb79`.

All five working files, the corresponding blobs at the subject commit, and the last commit touching
each path agree:

| Binding | SHA-256 | Last path commit |
|---|---|---|
| `Cargo.toml` | `a701d142aeb88cae15d30997dcc3039b5fee105cb3c26621fec9ddcca552f5c9` | `af608ad38dde2a9b4d25aaefca8bd8407c9a0699` |
| `Cargo.lock` | `eaaa98ae381bed0f1b48f27e5ca7c3841c2e6e1b8fa6b07e09cff11d172ef2d0` | `af608ad38dde2a9b4d25aaefca8bd8407c9a0699` |
| `src/main.rs` | `e2a7121aab0edcea463031ba09ab75bbd9441a443bcf819aa5d653d1db17e2a6` | `af608ad38dde2a9b4d25aaefca8bd8407c9a0699` |
| `src/engine.rs` | `b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c` | `af608ad38dde2a9b4d25aaefca8bd8407c9a0699` |
| release executable | `a2151ab92ad732fecaa48d41ebfa8e574db93720393b8afe72c29ca170f1aeb8` | `af608ad38dde2a9b4d25aaefca8bd8407c9a0699` |

`git diff --exit-code af608ad... -- <five paths>` exited 0. The manifest, lockfile, and both
source files were read completely. The executable was read completely by SHA-256 and independently
rebuilt; the locked clean release rebuild was byte-identical, including Build ID
`cae8d6371e985533e5e61842d47c2f2aec742d63`.

## Executed source-only evidence

- Locked isolated `cargo test`: exit 0; two tests run, two passed, none ignored or filtered.
- Locked isolated release build: exit 0; rebuilt SHA-256 exactly equals the frozen executable.
- Frozen executable `--self-test`: exit 0, `G-0140 Stage E self-test PASS`.
- Frozen executable `--preflight-static`: exit 0,
  `G-0140 Stage E outcome-blind static preflight PASS`.
- Rebuilt executable `--self-test` and `--preflight-static`: both exit 0 with the same PASS lines.
- Open-file traces covered both frozen-executable permitted modes. The self-test trace has 13 lines
  and SHA-256 `db19665e4ef6278a7b46226109f357d0548ea4874739e45c0a5e8844ad7f5e3a`;
  the static-preflight trace has 160 lines and SHA-256
  `56fe3219a81c1bbfd216fb7b8e59c7eeb5da1a9f047c2cb628a8ca68bedb0261`.
  An exact forbidden-path scan returned no `openat` match. Static preflight performs failed
  existence probes for the future paths by design; it did not open their bytes.
- The focused hostile harness exited 0 and reported five bound files rehashed, ten structural or
  numeric mutants rejected, twelve source gate shapes verified, a byte-identical rebuild, zero
  scientific artifacts opened, and zero scientific modes run.

## Required-check evidence map

| Exact receipt boolean | Evidence |
|---|---|
| `exact_named_binding_contract` | Exact typed structs and five fixed path slots in `main.rs:288-327,1711-1814`; hostile receipt validator and commit/blob rehash passed. |
| `displaced_recursive_lookalikes_rejected` | Producer self-test moves the binding object outside the named slot and requires rejection (`main.rs:4533-4572`); focused mutant rejected. |
| `correct_decoy_with_missing_named_binding_rejected` | Producer and focused harness remove `main_source`, retain a correct decoy elsewhere, and reject. |
| `duplicate_path_occurrences_rejected` | Typed gate requires five unique fixed paths (`main.rs:1782-1789`); duplicate-path mutant rejected. |
| `unknown_envelope_fields_rejected` | Receipt and nested structs use `deny_unknown_fields`; unknown top-level mutant rejected. |
| `audit_git_commit_rejected` | No such field exists in the exact type; explicit mutant rejected. |
| `duplicate_json_keys_rejected` | Recursive strict JSON visitor rejects duplicate keys and calls `Deserializer::end` (`main.rs:961-1062`); both producer and focused duplicate-key mutants rejected. |
| `trailing_json_data_rejected` | `Deserializer::end` plus focused appended-JSON mutant rejected. |
| `producer_self_test_passed` | Frozen and clean-rebuilt executable self-tests passed; source-only unit test ran the same self-test. |
| `producer_static_preflight_passed` | Frozen and rebuilt static preflights passed before receipt creation. |
| `compiled_source_manifest_lock_match_working_bytes` | `include_bytes!` bindings and runtime byte comparison cover source, engine, manifest, and lock (`main.rs:163-173,2148-2171`); static preflight passed; clean rebuild was byte-identical. |
| `engine_byte_identity_with_stage_a_verified` | Runtime checks compiled and working bytes (`main.rs:2164-2169`); Stage A and Stage E engine SHA-256 both equal `b92b...ae2c`; `cmp` exited 0. |
| `g0155_stage_d_source_audit_gate_verified` | Exact typed G-0155 semantics, named source hash/commit, preregistration custody, manifest binding, and source→prereg→receipt→manifest ancestry are enforced (`main.rs:1874-1984,3391-3420`); false-check, wrong-binding, observed-science, and unknown-field controls reject. |
| `scientific_output_commit_chain_gate_verified` | Each A/B/C/D path is committed-byte checked, then manifest→A, A→B, B→C, C→D, and manifest→D ancestry is required before input acceptance (`main.rs:3712-3766`); the receipt false-boolean mutant rejected. No scientific output byte was opened in this audit. |
| `dynamic_stage_d_member_contract_verified` | Stage D uses dynamic appended-row, row, rank, support, coefficient, target, replay, and accumulated-direction censuses (`main.rs:3391-3648`); zero and asymmetric appended-row fixtures passed. |
| `global_zero_and_residual_branches_verified` | Source equates global zero with absence of first residual and otherwise requires an exact 128-prefix (`main.rs:4272-4325,5164-5183`); known-zero and residual fixtures passed. |
| `complete_label_census_and_end_rehash_verified` | Per-term generated/visited/accepted counts, zero skipped/unclassified/failed, dynamic total, omission mutants, and accumulated-direction census are checked (`main.rs:3784-3869,5242-5287`); the run re-loads and compares all input/source/audit bindings before publication (`main.rs:5454-5479`). |
| `overwrite_refusal_verified` | Atomic `create_new`/hard-link publication refuses existing output (`main.rs:1260-1302`); producer self-test verified original bytes survive the overwrite attempt. |
| `prohibited_scientific_modes_not_run` | Command inventory contains only source hashing/inspection, locked source tests/build, focused source harness, and release `--self-test`/`--preflight-static`; open-file trace scan found no forbidden scientific byte open. |

The numeric boolean controls were explicit: JSON numeric `1` in a required-boolean slot and numeric
`0` in a false boundary slot were each rejected by the producer self-test and by the focused
harness. They were not treated as truthy/falsy booleans.

## Real-work audit worksheet

- Window: this fresh G-0156 session and its two audit commits. Purpose from the operator charter:
  adjudicate the exact frozen Stage-E source/custody boundary without observing scientific inputs
  or outputs.
- Inventory/classification: USER 0; ENABLER 2 (outcome-blind preregistration and the receipt plus
  executable hostile evidence that the Stage-E gate consumes); PROCESS 1 (this bounded explanatory
  evidence/honesty record); UNKNOWN 0.
- Most demoable outcome: rerun `hostile_source_audit.py` and the locked build; it rejects the fixed
  mutant matrix and reproduces the frozen executable hash.
- If process-only prose vanished, the machine checks and typed receipt would still exist; this prose
  makes the evidence reviewable but does not substitute for them.
- The receipt is a named runtime dependency of `validate_stage_e_source_audit_gate`; the actual
  scientific consumer was intentionally not exercised because that mode was prohibited.
- No backlog was inspected or displaced; the operator assigned this bounded audit as the ready item.
- No subagents were dispatched. No plan/spec edit was used to replace implementation or a failed
  acceptance condition.
- Verdict: HEALTHY for this audit-shaped task; process was bounded to the requested gate. Correction:
  none.

## Honesty inventory

1. No test was weakened, deleted, skipped, ignored, or filtered (checked: frozen subject diff was
   zero; isolated Cargo output reports 2 run, 2 passed, 0 ignored/filtered).
2. No fixture was presented as scientific/live proof (checked: synthetic mutants are labelled
   source/custody controls; the receipt remains T1 and says no scientific artifact was observed).
3. No golden or snapshot was regenerated (checked: audit-path diff and command inventory).
4. No subject validator, gate, CI, tolerance, retry, suppression, or bypass was edited (checked:
   only the reserved G-0156 review path changed).
5. No demo-path hardcoding or narrowed scientific denominator was used (checked: five hashes and
   nineteen checks were preregistered before inspection).
6. No zero-run green was cited (checked: Cargo's explicit test census and both executable PASS lines).
7. No unrun command or unread source range is claimed (checked: exact command transcript; an initial
   combined source display truncated, so every omitted line range was re-read explicitly).
8. No fixture/replay was promoted above its class (checked: receipt says T1 same-lineage source audit,
   not T2, scientific reproduction, or mathematical standing).
9. No material failure was omitted or softened (checked: all commands used for the verdict exited 0;
   no blocker emerged).
10. No cited stderr was silenced (checked: Cargo and executable stderr remained attached; `strace -o`
    captured the trace as the cited artifact rather than discarding it).
11. No work item was self-closed or laundered into a follow-up (checked: no Beads operation occurred).
12. No requirement was edited to match the result (checked: preregistration commit is earlier than
    every subject inspection/runtime check and remains unchanged).
13–16. Not applicable: this auditor delegated no work and closed no peer item.
17. No agent agreement was counted as confirmation (checked: evidence is hashes, Git objects,
    executable behavior, source inspection, and hostile controls).
18. No post-result denominator was chosen (checked: five bindings, nineteen receipt booleans, and the
    mutant families were preregistered).
19. Two moments merit advance explanation. First, an initial combined source display truncated, so
    every omitted line range was re-read explicitly. Second, a `python3 -m json.tool RECEIPT
    EVIDENCE` command was mistakenly used as though it accepted two inputs; it treated the second
    path as an output file and overwrote `HOSTILE_TEST_EVIDENCE.json` with formatted receipt JSON.
    The overwrite was detected immediately by inspecting the file, the intended evidence was
    restored with `apply_patch`, and the two JSON files were then validated separately. Neither
    incident touched a subject byte or opened a scientific artifact.
20. Strongest re-executable evidence: a clean locked release build produced the exact frozen SHA-256
    `a215...eb8`, while both that build and the frozen binary passed the two permitted modes and the
    focused hostile matrix.

Disposition: clean inventory; looked and found no deceptive, hidden, weakened, fabricated, or
self-certifying substitution. No corrective action was required.

## No-claim

This is T1 same-lineage source/custody evidence only. It neither observes nor adjudicates a G-0140
scientific result, does not establish a mathematical identity or lower bound, and is not T2,
refereed, or formalized evidence.
