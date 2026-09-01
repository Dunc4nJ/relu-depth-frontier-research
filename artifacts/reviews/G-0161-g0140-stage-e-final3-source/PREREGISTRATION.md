# G-0161 outcome-blind source-custody preregistration

Date: 2026-09-01

Receipt schema: `max11-g0161-g0140-stage-e-final3-source-audit-v1`

## Scope and blindness contract

This is a source-only custody and implementation audit of the frozen G-0140 Stage-E final3 program. Before this preregistration was committed and pushed, the auditor did not open or read the Stage-E subjects, the current G-0140 manifest, the Stage-A result, or any Stage A-E scientific output. The audit will make no scientific observations, will perform no scientific replay, and will not run full-preflight or scientific mode. It will not create scientific outputs.

This audit is valid only for the exact bytes pinned below. If any audited source, dependency lockfile, engine, or binary byte changes, this audit is permanently inapplicable to the changed bytes and may never be reused for them.

## Frozen identities supplied before inspection

- Last subject-changing commit: `c5294749d13d907a9c7d50408baa679ea7cc302c`
- Main source SHA-256: `2088d854981e02fbd6c3d12ad0e4a3e9dd50b2e1d0e6d072fe5c8eb28876d023`
- Engine SHA-256: `b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c`
- `Cargo.toml` SHA-256: `a701d142aeb88cae15d30997dcc3039b5fee105cb3c26621fec9ddcca552f5c9`
- `Cargo.lock` SHA-256: `eaaa98ae381bed0f1b48f27e5ca7c3841c2e6e1b8fa6b07e09cff11d172ef2d0`
- Release binary SHA-256: `da98a55b10369b5845bb9197b652bf1eaea156e80363e7d60b8eeb0a1aa74919`
- Stage-D source pin SHA-256: `d5b5d96ccf36cf4b76ec851480b8097fb6d95e38d96e635fda60250e71835732`
- Stage-D source-pin commit: `2aed47a3b359c0a6625a8f8fd58225069d6c1498`

## Fail-closed audit gates

The receipt will be `PASS` only if every item below is verified against the frozen bytes:

1. The five supplied Stage-E identities match, the subject-changing commit is exact, and a clean `--locked` release rebuild is byte-identical to the supplied binary.
2. The Stage-D source pin and commit are exact; the fresh G-0160 receipt path and schema are required; and the generic typed check key is exactly `stage_d_source_audit_gate_verified` (the retired G-0155-specific key is forbidden).
3. The Stage-D typed gate accepts an exact positive fixture and rejects negative fixtures, fail-closed.
4. All ten direct and transitive future-output exclusions are present and enforced.
5. Source-to-preregistration-to-audit provenance is enforced without scientific-output dependence.
6. Engine identity, compiled bindings, the exact claim/no-claim constants, and all five named bindings are checked.
7. BigInt handling and complete-replay paths are checked statically and by source-only tests.
8. `cargo fmt --check`, the complete two-test suite, `cargo clippy --locked -- -D warnings`, the program self-test, and static preflight pass only in a sanitized isolated tree in which the current manifest and all five scientific outputs are absent.
9. The receipt records all scientific/replay/execution flags as false and contains no scientific claims or observations.

Any mismatch or inability to establish an item above yields no PASS receipt.
