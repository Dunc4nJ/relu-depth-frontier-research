# G-0162 outcome-blind source/custody preregistration

Date: 2026-09-01

Receipt schema: `max11-g0162-g0140-stage-d-master-final4-source-audit-v1`

## Scope and blindness contract

This is an independent T1 source/custody audit of the frozen G-0140 Stage-D
final4 program. Before this preregistration was committed and pushed, the
auditor did not open or read the subject source, any G-0140 scientific
manifest, or any Stage-A through Stage-E scientific output. Earlier scientific
audit outcomes will not be consulted. The audit will make no scientific
observations, will perform no full preflight or scientific run, and will not
create scientific output.

The source and runtime inspection will occur only in a fresh sanitized isolated
copy/worktree in which the G-0140 scientific manifest and all Stage-A through
Stage-E scientific-output paths are absent. Repository-path discovery may use
Git metadata, but prohibited files will not be opened or copied into the audit
environment.

This audit is valid only for the exact bytes pinned below. Any mismatch is
fail-closed and yields no PASS receipt.

## Frozen identities supplied before inspection

- Subject: `artifacts/math/G-0140/stage_d_master/rank_aware_master_v1.py`
- Last subject-changing commit: `19107c5eed2cad00d48eff3dd9bea0c015ecce89`
- Subject SHA-256: `1f4e7f3a141bfbfb7a090ee681bab649ba0cebc191021b112db0368fe2256581`
- Intended delta: align Stage-D snapshot-digest encoding with the imported
  Stage-C selector's TAB separator and add an explicit regression equality.
- Intended mathematical-algorithm delta: none.

## Fail-closed audit gates

A PASS receipt will be emitted only if all of the following are established
against the frozen bytes, independently of scientific outputs:

1. Commit, blob, checked-out, and working-tree subject identities agree with
   the supplied SHA-256; Git ancestry and `origin/master` custody are verified.
2. The subject compiles with `py_compile`, its source-only self-test passes,
   and sanitized static preflight passes without running full preflight or any
   scientific mode.
3. Imported Stage-C selector and core dependencies resolve to the intended
   source files and their exact hashes are recorded and checked.
4. The Stage-C snapshot-digest contract is tested with an independent positive
   TAB-separated fixture, an independent negative NUL-separated fixture, and
   an explicit equality to the imported selector implementation.
5. Independent member and separator fixtures cover ordering, encoding, and
   boundary sensitivity rather than relying only on self-comparison.
6. Source-audit receipt schema checks and hostile controls fail closed for
   malformed schema, status, check names/types, identities, and claim fields.
7. The receipt required-check set equals the frozen source's
   `SOURCE_AUDIT_CHECKS` exactly, including
   `stage_c_snapshot_digest_contract_verified`, with neither omissions nor
   additions.
8. The receipt schema is exactly
   `max11-g0162-g0140-stage-d-master-final4-source-audit-v1`; frozen claim and
   no-claim constants are copied exactly from the subject and enforced.
9. The receipt records that scientific outputs were not inspected, scientific
   code was not run, and no scientific claim or observation was made.

Any failed or indeterminate gate terminates the audit without a PASS receipt.
