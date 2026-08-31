# G-0155 source/custody audit evidence

- Completed UTC: `2026-08-31T22:16:31Z`
- Frozen subject commit: `69a3449c7bc291f283c10c669e5d39f2a1212782`
- Frozen subject SHA-256: `6112c55f943c20acd80402a9800db581c1ee6d5caf35c2f418d2a52cf09ad03e`
- Preregistration commit: `317b4af809c154a18ddc402bc838fb9d2e4d93ff`
- Preregistration SHA-256: `240d471362dabf1a183ae25b11c85fd8f3dfce7594987f3ab87f1bdd70ddad44`
- Scope: exact frozen source/custody only; no future G-0140 scientific manifest, input, or output bytes were read; no scientific preflight, replay, column-generation run, or default producer run was invoked.

## Byte custody and imported bindings

The frozen Git blob and live working bytes were byte-identical for every audited binding. The frozen subject's three direct pins matched, and the exact helper pin shared by the imported selector/core matched:

| Binding | SHA-256 |
|---|---|
| `artifacts/math/G-0140/stage_d_master/rank_aware_master_v1.py` | `6112c55f943c20acd80402a9800db581c1ee6d5caf35c2f418d2a52cf09ad03e` |
| `artifacts/math/G-0140/stage_c_selector/complete_matrix_rank_selector_v1.py` | `9c5e0e7e40c7f12b8d299148fa7f9a942207eacdc26aa6662c59bb86f481b9b0` |
| `artifacts/math/G-0135/stage_c_master/full_family_master_v3.py` | `c84f259d393756c9ff658aab9a1488b145b9607a939dbccfce47069168b40a1a` |
| `artifacts/math/G-0135/full_family_master_result_v3.json` | `ef1cbdf3abfd32326c35e511057a3450b4942ae9aa901ead8e8b86133c564db8` |
| `artifacts/math/G-0117/fresh_q_cegis_exact.py` | `ee422e6e36085e26ddd83a75f8901c6a6efbe3fd2a99e80e280f9449d0ed8281` |

The preregistration commit was remotely visible before source inspection and runtime checks. The frozen subject commit is an ancestor of the preregistration commit, and the pushed branch contains the preregistration commit.

## Permitted execution evidence

`source_audit_tests.py` ran under the pinned Python 3.13.7 toolchain and exited 0. It accepted the exact positive receipt fixture and the actual receipt, verified all frozen/live byte identities and imported pins, and rejected 177/177 hostile cases:

- 20 expected-`true` fields × 7 non-exact substitutes (`1`, `1.0`, `"true"`, `null`, array, object, opposite boolean) = 140 rejections;
- 4 expected-`false` fields × 7 non-exact substitutes (`0`, `0.0`, `"false"`, `null`, array, object, opposite boolean) = 28 rejections;
- 9 structural/JSON cases = 9 rejections: unknown envelope, forbidden `audit_git_commit`, missing check, unknown check, wrong subject commit, displaced binding lookalike, correct decoy with missing named binding, duplicate JSON key, and trailing JSON data.

The positive control is the countermetric: the exact receipt fixture was accepted before mutations, so the result is not reject-all green.

The exact frozen producer was also materialized into a source-only temporary Git fixture containing only the subject and the four declared/source-test core bindings above. No future G-0140 scientific artifact was present.

Observed commands and results:

```text
python .../rank_aware_master_v1.py --self-test
g0140-rank-aware-master-self-test: PASS (member and separator routes)
exit 0

python .../rank_aware_master_v1.py --static-preflight
g0140-rank-aware-master-self-test: PASS (member and separator routes)
result = G0140_RANK_AWARE_MASTER_STATIC_PREFLIGHT_PASS
all_future_inputs_present = false
scientific_column_generation_run = false
scientific_result_written = false
exit 0
```

Static inspection confirmed that `--static-preflight` has no call edge to `prepare`, `preflight`, `run`, `with_column_loader`, `load_validated_future_inputs`, or `exact_column_generation`; the scientific path remains behind the exact future-input and source-audit gates. The frozen run path calls the pinned G-0135 exact-Q core with `record_count = 163740`; the core's terminal separator path replays the full record range and checks the complete scan count. This is source-contract evidence only, not a scientific execution or mathematical adjudication.

## Deviations and corrections

The first run of the new external audit harness stopped before a verdict because a textual forbidden-call check matched `preflight(` inside the function name `static_preflight`. This was a harness-only false positive, not a subject failure. The check was replaced by AST call-node inspection, the subject remained untouched, and the complete battery was rerun successfully. The failed run is disclosed rather than omitted.

A later presentation-only attempt to pipe the already-green harness JSON through a one-line summary command had a quoting error; the summarizer exited with a syntax error and the producer side of the pipe reported `BrokenPipeError`. The harness was immediately rerun directly with native stdout/stderr and exited 0 with all nine audit checks true and 177 rejected mutants. No subject code or acceptance condition changed.

The preregistration's provisional process-artifact worksheet said runtime did not branch on the preregistration. Post-preregistration source inspection showed that the producer validates its path, digest, Git commit, and ancestry, so the more accurate final classification is `ENABLER`/runtime gate. The frozen preregistration was not rewritten after outcome exposure; this correction is recorded here.

## Real-work audit worksheet

- Window: this G-0155 session and its two review commits (preregistration plus final review handoff).
- Bounded purpose: independently adjudicate the frozen Stage-D producer's source/custody contract without observing or replaying future science.
- Inventory classification: USER `0`; ENABLER `2` (runtime-consumed preregistration and receipt); PROCESS `1` (re-executable hostile-control harness); UNKNOWN `0`.
- Most demonstrable deliverable: the exact receipt plus a re-executable 177-mutant suite and isolated producer self/static tests.
- Without the process item: the primitive-type fail-open claims would lack reproducible adversarial evidence; the harness directly gates the receipt.
- Speculative infrastructure: none; the frozen selector accepts the receipt shape, and the producer consumes the preregistration/receipt in its future gate.
- Older user-visible item displaced: none; this was the specifically assigned bounded audit.
- Delegation/closure farming: none; no subagent was spawned and no tracker item was self-closed.
- Plan/spec substitution or follow-up laundering: none; the frozen subject and preregistration were not edited after inspection.
- Verdict: `HEALTHY` for this audit-shaped work item; the verification process is bounded and directly gates the requested runtime-consumed receipt.

## Honesty inventory

1. No (checked: review-path diff, bounded Git history, and reflog; no subject test was weakened, deleted, skipped, or ignored).
2. No (checked: the source-only fixture is explicitly labeled synthetic isolation and supports only source/self-test standing, never live scientific proof).
3. No (checked: no golden or snapshot file was created or regenerated).
4. No subject gate was edited (checked: only the external review harness and receipt are new; no suppression, bypass flag, tolerance, timeout, or retry widening was introduced). The harness's false-positive string test was corrected to inspect AST calls and is disclosed above.
5. No (checked: no environment sniffing, demo hardcoding, narrowed scientific claim, or cherry-picked denominator; the denominator is 177 = 140 + 28 + 9 and the positive countercontrol ran).
6. No (checked: the hostile harness executed 177 named rejects plus an accepted positive fixture; the isolated producer printed its member/separator self-test before static PASS).
7. No (checked: every command cited above was executed and its exit/output observed).
8. No (checked: all fixture evidence is labeled source-only; the receipt remains same-lineage T1 and makes no scientific claim).
9. No omission (checked: the initial harness false positive, the later summary-wrapper quoting error, and both exact corrections are recorded above; no subject failure occurred).
10. No (checked: stderr was retained for every cited audit/test command; only the uncited background `cass` index refresh was redirected to its own log).
11. No (checked: no item was closed or declared scientifically complete).
12. No (checked: the frozen task boundary, subject, and preregistration were not softened after results).
13–16. Not applicable (checked: no subagent/swarm delegation or tracker closure occurred in this reviewer session).
17. No (checked: same-lineage status is explicit and the receipt is capped at T1; agreement was not promoted to independent evidence).
18. No (checked: the mutation denominator is the complete declared boolean-field/type cross-product plus the nine named structural cases; the accepted positive fixture is the preregistered countermetric).
19. Three moments merit advance explanation and are disclosed above: the harness-only false positive, the later summary-wrapper quoting error, and the preregistration worksheet's provisional boundary misclassification.
20. Strongest re-executable evidence: `source_audit_tests.py` at the final review commit, followed by the frozen producer's isolated `--self-test` and `--static-preflight` runs.

Older-session `cass` sweep: bounded lexical searches for `weaken the test`, `make the test pass`, `skip this test`, `regenerate the golden`, `mark it done`, and the session-derived `source audit integer boolean` returned zero hits in this workspace's available index. The index was stale, so this is a bounded negative, not a claim about unindexed history; current-session Git/diff/reflog evidence was checked directly.

Disposition: looked, found no deceptive close, gate weakening, proof-class inflation, or hidden subject failure. The two non-subject corrections are recorded plainly and were corrected without altering the frozen subject or preregistration.
