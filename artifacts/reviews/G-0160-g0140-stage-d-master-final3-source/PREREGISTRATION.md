# G-0160 T1 source-custody audit preregistration

## Seal and independence

- Audit ID: `G-0160`.
- Audit tier: `T1`.
- Scope: fresh, outcome-blind, source-only custody and fail-closed audit of the frozen G-0140 Stage-D master source.
- Subject: `artifacts/math/G-0140/stage_d_master/rank_aware_master_v1.py`.
- Expected subject SHA-256: `d5b5d96ccf36cf4b76ec851480b8097fb6d95e38d96e635fda60250e71835732`.
- Expected last-modifying commit: `2aed47a3b359c0a6625a8f8fd58225069d6c1498`.
- Expected repaired selector SHA-256: `f6cbb7b83f25ce88b6448ab363eb73bcb7bc4cb8427c167009c98ae0a06a60d3`.
- Expected selector last-modifying commit: `f56b92ab8e13401ccd8a63d8c24137e16450d5ef`.
- Expected rejected stale selector digest: `9c5e0e7e40c7f12b8d299148fa7f9a942207eacdc26aa6662c59bb86f481b9b0`.

This preregistration is sealed before opening or reading the Stage-D subject source, the current G-0140 manifest, the Stage-A result, or any Stage A--E scientific output. Before this seal, the auditor used only the task brief, repository status metadata, and Agent Mail coordination metadata. No scientific input or scientific output has been opened, parsed, imported, executed, or observed.

The audit and any eventual receipt bind the exact audited bytes. Any change to the subject or selector bytes, even if semantically immaterial, invalidates this audit permanently for the changed bytes. This audit and receipt must never be reused, amended, or represented as covering changed bytes; a fresh preregistered audit is required.

## Permitted evidence and forbidden operations

After this seal, the auditor may inspect only source and source-custody evidence needed for the checks below: the frozen subject, its selector dependency, relevant Git objects/history, and non-scientific source-audit artifacts. Known scientific manifests, Stage-A results, and Stage A--E scientific outputs remain forbidden and will not be opened or read.

Permitted execution is limited to:

1. `py_compile` of source in a sanitized isolated tree;
2. the source-only `--self-test` mode in that tree;
3. the source-only `--static-preflight` mode in that tree;
4. deliberately hostile source mutants in separate isolated copies, only to establish fail-closed source validation.

The isolated tree must omit known scientific manifest and output paths. Scientific `--preflight`, default/scientific execution, imports that trigger scientific work, and creation or observation of scientific outputs are forbidden.

## Preregistered decision rule

Verdict is PASS only if every check below passes. Any missing, ambiguous, skipped, or non-fail-closed check is a FAIL. `SOURCE_AUDIT_RECEIPT.json` may be created only on PASS; on FAIL, no receipt bearing PASS or the requested result token may exist.

Required checks:

1. **Exact subject bytes:** independently compute SHA-256 and require the expected subject digest.
2. **Exact selector bytes:** resolve the selector dependency from source without importing it, independently compute SHA-256, and require the expected repaired selector digest.
3. **Git/blob custody:** require each worktree file to equal the corresponding committed blob, require the expected blob-derived SHA-256, require the stated last-modifying commit, and verify commit/object reachability and path custody with exact Git plumbing/diff evidence.
4. **Selector pin and generic dependency binding:** require the subject to pin the repaired selector digest, reject the stale digest, and consume the selector's generic `STAGE_C_SOURCE_AUDIT_PATH` binding for G-0159 rather than a hard-coded scientific result path.
5. **Fresh audit binding:** require the subject to bind its own G-0160 audit path and schema `max11-g0160-g0140-stage-d-master-final3-source-audit-v1`, with no acceptance of an earlier source audit.
6. **Exact terminal invariants:** require the core/full scientific terminal contract to remain exactly 163,740 columns and require the terminal scientific logic to be unchanged under an exact source/AST or Git-diff comparison to its pinned predecessor. This is a source comparison only; no scientific data may be read.
7. **Strict receipt contract:** extract the subject's exact claim, no-claim, required-check set, named binding `master_source`, verdict/result requirements, and scientific-observation/replay requirements from source; require exact correspondence in any G-0160 receipt.
8. **Source-only modes:** in a sanitized isolated tree with known scientific paths absent, require `py_compile`, `--self-test`, and `--static-preflight` to succeed without creating scientific outputs.
9. **Hostile stale-pin mutant:** mutate only the selector pin from the repaired digest to `9c5e0e7e40c7f12b8d299148fa7f9a942207eacdc26aa6662c59bb86f481b9b0`; require source-only validation to fail closed.
10. **Strict Boolean mutants:** for every security-relevant Boolean predicate/check implicated by the source-audit gate, create targeted source mutants that would weaken, invert, bypass, or default-open the predicate; require source-only validation to reject each mutant.
11. **Structural audit mutants:** create targeted mutants that remove, rename, redirect, duplicate, or otherwise corrupt required audit bindings/fields/paths/schema/check structure; require source-only validation to reject each mutant.
12. **No scientific contact:** require recorded scientific observation and scientific replay flags to remain `false`, and verify no known scientific manifest/output path was present in the isolated execution tree or created by any permitted command.

## Receipt policy

If and only if all preregistered checks pass, emit exactly one strict JSON receipt at `artifacts/reviews/G-0160-g0140-stage-d-master-final3-source/SOURCE_AUDIT_RECEIPT.json` with:

- schema `max11-g0160-g0140-stage-d-master-final3-source-audit-v1`;
- verdict `PASS`;
- result `SOURCE_CUSTODY_AUDIT_PASS_T1`;
- exact subject/selector digests and Git custody identifiers;
- the exact source-derived claim, no-claim, and required-check set;
- named binding `master_source`;
- scientific observation and replay flags both `false`;
- explicit results for every preregistered check and hostile mutant.

The receipt asserts source custody and fail-closed source validation only. It makes no scientific claim, reports no scientific observation, and is not a scientific replay.
