# G-0147 final source/custody audit — FAIL/ABORT

## Decision

No source/custody clearance is granted for frozen Stage-B commit
`f55df23361382a9b99b5ca3c07794611a7253c6c`.

The terminal blocker is deterministic and upstream: the frozen producer hard-codes the G-0146
Stage-A source-audit path and schema and requires verdict `PASS` with result
`SOURCE_CUSTODY_AUDIT_PASS_T1`. The immutable receipt at that exact path is instead:

- commit: `495d36c5d403bc678493dd823776d97ea03041b3`;
- SHA-256: `dc01ef4b4dcfaf8fa03662350b7cd5544c317599e7c640f29d71ad3c74d68e8d`;
- schema: `max11-g0146-g0140-stage-a-final-source-audit-v1`;
- verdict: `FAIL`;
- result: `SOURCE_CUSTODY_AUDIT_FAIL_RECURSIVE_BINDING_LOOKALIKE`.

Working and committed G-0146 receipt bytes are equal. A fresh audit cannot overwrite or inherit
that failed immutable identity. A repaired Stage-A producer needs a new audit identity, and these
frozen Stage-B bytes cannot consume a new path/schema. Therefore both lineages must be refrozen
before another Stage-B audit.

## Exact Stage-B custody

Before the upstream stop, all four subject files were independently extracted from the frozen Git
commit into an isolated temporary custody root and compared with the working tree. Initial and end
rehashes agreed:

| Binding | SHA-256 |
|---|---|
| `src/main.rs` | `f6c4c4b210a32c8453626fd9a63bfde8a3083f6fb083dce56646a3361289390a` |
| `Cargo.toml` | `425d82de4e6d5902e2d3d7b005c5473225c4d6f197752590e89d7be670b2685c` |
| `Cargo.lock` | `8875e1375a361873ac13bbcdf9e14c8ca7b34afa1438dfae9a6800f31325365a` |
| release executable | `0dcb50e154797ee8104457a93ce172a46054d9a5836c499cf31796134ccb5050` |

The frozen executable contains the exact source, Cargo manifest, and lockfile bytes and passed its
self-test and outcome-blind static preflight. Those facts do not overcome the upstream FAIL.

## Work stopped on notice

The broad checker had already completed before the upstream stop notice. Its result is preserved
in `CHECK_RESULTS.json` as partial evidence, not as the terminal decision. It found three additional
blocking source-level paths:

1. a missing `first_nonzero_linear` field is conflated with explicit JSON `null` by Serde `Option`;
2. nine Stage-A mutation/control payloads are admitted as opaque `Value`/`Vec<Value>` and are not
   structurally validated; and
3. source-audit subject bindings are collected recursively from arbitrary unknown decoy content.

The final verdict does not depend on those findings, and this report does not claim the broader
audit was exhaustive after the stop directive.

## Evidence class and boundary

This is fresh-context, same-lineage T1 evidence only. No future G-0140 scientific manifest,
Stage-A scientific result, candidate contents, or Stage-B scientific output was opened by the
reviewer. The candidate and public panel were supplied only as opaque paths to the explicitly
allowed static-preflight mode. No science or replay mode ran. No mathematical claim is promoted.

The machine-readable terminal decision is `SOURCE_AUDIT_RECEIPT.json`. It deliberately uses
verdict `FAIL` and a non-PASS result, so the frozen producer cannot consume it as clearance.
