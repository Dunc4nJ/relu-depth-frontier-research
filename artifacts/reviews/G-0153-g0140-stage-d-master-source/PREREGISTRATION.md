# G-0153 Stage-D master source/custody audit preregistration

## Frozen object and decision

- Review handle: `G-0153-g0140-stage-d-master-source`
- Reviewer: Agent Mail identity `GentlePine` (`codex`, `gpt-5`)
- Review mode: fresh-context, outcome-blind, read-only source/custody audit; T1 only
- Frozen Git commit: `5b9fb81168d1a1f964b123b31edc3763439ecd7b`
- Sole subject source: `artifacts/math/G-0140/stage_d_master/rank_aware_master_v1.py`
- Required source SHA-256: `aa7ea5ca9174667ecae0c5e2d28d50e616b2da24d57f62d2026150c67f244935`
- Decision rule: PASS only if every check below is supported at the frozen binding. Any failed, unavailable, ambiguous, or underpowered required check yields FAIL with the smallest reproducible counterexample. The source will not be patched.

This preregistration is committed and pushed before the reviewer opens or executes the subject source. It fixes the tests and claim boundary without knowledge of any subject result.

## Access and execution boundary

- Permitted source executions are exactly `.venv/bin/python <subject> --self-test` and `.venv/bin/python <subject> --static-preflight`, plus argument/data variants that retain one of those two explicit modes.
- Forbidden source executions include default mode, `--preflight`, or any mode that launches the scientific computation.
- The reviewer will not open any future G-0140 manifest or any scientific Stage A/B/C/D output.
- Read-only Git/blob/object inspection, source reading, independent static analysis, and minimal hostile-input fixtures are permitted.
- Temporary hostile inputs must be synthetic and must not stand in for live scientific evidence.

## Predeclared audit battery

1. **Exact custody.** Verify repository HEAD and the bound commit, hash the working-tree source bytes, resolve the path's blob at the frozen commit, hash the exact Git blob payload independently, and require working tree, Git object, frozen path, commit, and required SHA-256 to agree. Detect replacement, symlink, submodule, or worktree/index drift.
2. **One-binding source-audit contract.** Determine the source-audit JSON contract from the frozen source and require one and only one binding to the frozen commit, subject path, source SHA-256, and expected audit identity. Reject duplicate, missing, additional, mistyped, relative/aliased, or mismatched bindings. Hostile JSON cases include duplicate keys, duplicate bindings, unknown keys, wrong scalar types (including Boolean-as-integer), malformed JSON, trailing data, non-finite numbers, path aliases/traversal, and hash/commit case or length mutations.
3. **Import safety.** Statistically enumerate imports and top-level effects; require imports to be available in the pinned environment and require importing/loading for static inspection not to execute scientific work, read forbidden future artifacts, mutate repository state, or bypass explicit mode gates.
4. **Future-artifact gates.** Require fail-closed refusal of future manifests, post-frozen parameters, future scientific outputs, or alternate source/audit bindings. Exercise the smallest synthetic admissible/mutated pairs without opening a real future artifact.
5. **Live Stage-C lineage replay.** From only admissible live Stage-C inputs named by the frozen source, independently recompute and compare the basis, minors, and selection lineage. Require exact identity/order/digest/count agreement; no embedded copy, cached future result, or self-reported equality is accepted.
6. **Selected loader and zero target.** Exercise the selected-member loader against exact live inputs and hostile omissions, duplicates, reordering, type mutations, and path substitutions. Independently require the target vector/quantity asserted to be zero to be exactly zero under the declared exact arithmetic, not merely within a tolerance.
7. **Seed binding.** Require the unique random/control seed to be exactly integer `204`, reject coercions and alternate seeds, and verify every seeded branch is derived from that binding.
8. **Reopened universe.** Independently enumerate the declared reopened population and require exactly `163740` distinct members with complete partition/reconciliation, no skipped or unclassified members, no duplicate counting, and no truncation. Mutants remove, duplicate, reorder, and truncate terminal shards/members.
9. **Exact member replay.** Independently replay each required member from live antecedents and compare exact normalized certificates/verdicts, not only aggregate counts or digests. A single member mismatch is a FAIL counterexample.
10. **Terminal separator replay and potency.** Independently reconstruct and verify the terminal separator from live antecedents. Run at least one preserving replay and planted destructive mutants that alter a load-bearing coefficient/member/ordering and require rejection. A constant-success or digest-only checker fails.
11. **Claim boundaries.** The audit may establish only source identity/custody, static contract enforcement, and exact replay/control behavior within the frozen finite protocol. It does not establish any Stage-D scientific result, proof, separation theorem, completeness outside the `163740` reopened universe, novelty, or correctness of unopened future outputs.

## Receipt rule

On PASS, emit one minimal source-audit receipt bound exactly to the frozen commit/path/SHA above. Every scientific-result flag must be Boolean `false`; the receipt must make no scientific claim and must identify T1 only. On FAIL, emit no PASS receipt: report a minimal reproducible counterexample and the unmet preregistered item.

## Anti-gaming and no-claim

- No test, assertion, schema, or expected constant will be weakened after inspection.
- No fixture, mock, self-test, cached digest, or source-authored PASS is accepted as live proof of a scientific result.
- No audit-tooling expansion is credited as research yield; only the smallest machinery needed to apply this fixed battery may be created.
- Agreement with the source is not independence. Independent recomputation must use separately written logic at every load-bearing replay.
- PASS would mean this exact frozen source cleared this source/custody battery. It would not promote G-0140, validate any Stage-D output, or discharge a mathematics evidence gate.
