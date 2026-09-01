# G-0163 Stage-E final4 source/custody evidence

Date: 2026-09-01

Verdict: `PASS` for source/custody only.

## Outcome-blind isolation

Inspection and runtime checks used the detached sparse worktree
`/tmp/g0163-stage-e-final4-audit.iG9IfD`. Before subject inspection, the
G-0140 scientific manifest, all five Stage-A through Stage-E scientific-output
paths, and the prospective G-0163 receipt were absent. None was opened or
generated. Full preflight and scientific mode were not run.

Canonical-path build and static-preflight checks mounted that same sanitized
tree read-only at `/data/projects/relu-depth-frontier-research` inside an
isolated container. This is necessary because the frozen program deliberately
embeds `CARGO_MANIFEST_DIR`; it does not weaken the absence boundary.

## Frozen identity and ancestry results

- Main source: `be4852b63ff2118182cdd07ead85708f0b4ef0785445f0f873ebd4367c9e866a`
- Engine: `b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c`
- `Cargo.toml`: `a701d142aeb88cae15d30997dcc3039b5fee105cb3c26621fec9ddcca552f5c9`
- `Cargo.lock`: `eaaa98ae381bed0f1b48f27e5ca7c3841c2e6e1b8fa6b07e09cff11d172ef2d0`
- Frozen/rebuilt release binary: `99ba4017c42ab08043b9aacaef554192ce50beff37a41df07ba8d4f7e4ba7179`
- Repaired Stage-D source: `1f4e7f3a141bfbfb7a090ee681bab649ba0cebc191021b112db0368fe2256581`
- Exact G-0162 receipt: `2e09106c38cdb366b7cf2ef62aa43b61c28a41eeb42587ec83ea808d39fca2d0`
- Subject last-changing commit: `4944a58e0816fcf8e62dbdd134448daffce10738`
- Stage-D last-changing commit: `19107c5eed2cad00d48eff3dd9bea0c015ecce89`
- G-0162 receipt commit: `e93afa3abb8128f955792f95150e889433100f3b`
- G-0163 preregistration commit: `24fc630c083649772df3933172e2263199b46f6d`

Commit-object, checked-out, and working bytes agreed. Verified ancestry is
Stage-D source -> G-0162 preregistration -> Stage-E source -> G-0162 receipt ->
G-0163 preregistration. The receipt commit is checked as a descendant of the
preregistration after publication.

## Bounded checks

- `cargo fmt --check`: pass.
- `cargo test --locked`: pass, 2 passed / 0 failed.
- `cargo clippy --locked -- -D warnings`: pass.
- Two independent clean canonical-path `cargo build --release --locked
  --offline` builds: mutually byte-identical and byte-identical to the frozen
  executable at the hash above.
- Frozen executable `--self-test`: pass.
- Frozen executable, sanitized canonical-path `--preflight-static`: pass.
- Stage-E engine and Stage-A engine: byte-identical at the pinned engine hash.
- Independent typed-contract harness: pass; 16 exact G-0162 required checks,
  69 G-0162 negative controls (including false, missing, and non-boolean
  `stage_c_snapshot_digest_contract_verified`), 20 exact G-0163 required
  checks, 85 G-0163 negative controls, and all 10 direct/transitive future-
  output exclusion controls.

The committed harness is `source_audit_tests.py`. The strict receipt contains
the frozen claim/no-claim strings verbatim and records every scientific flag
as false.
