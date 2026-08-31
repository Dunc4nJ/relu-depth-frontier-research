# G-0158 preregistration — G-0140 Stage-B final3 source-custody audit (T1)

- Registered: `2026-08-31T23:49:56Z`
- Reviewer: `NavyBrook` (`codex`, `GPT-5`; fresh context, same model family / T1)
- Mode: outcome-blind, source-only, adversarial custody audit
- Subject commit: `bbb4ffaa3a8d653e14dba8879dabbf5dd5e21794`
- Planned receipt schema: `max11-g0158-g0140-stage-b-final3-source-audit-v1`

## Blindness and immutable scope

This preregistration was written before opening or reading the Stage-B subject source, its binary,
its scientific manifest, the G-0140 Stage-A result, the frozen G-0139 receipt, or any current or
future G-0140 scientific output. Only repository operating instructions and generic campaign
epistemics were read first. The audit is source-only: it may establish source custody and fail-closed
gate behavior, but it may not inspect, interpret, generate, or validate a scientific result.

The following are prohibited throughout this audit:

- the current or any future G-0140 scientific manifest;
- every G-0140 scientific A–E output, including copies, aliases, displaced lookalikes, or derived
  summaries;
- the G-0140 Stage-A scientific result;
- full `--preflight`, scientific mode, or any command that reads or creates scientific outputs;
- edits to the frozen subject or creation of scientific artifacts.

Permitted after this preregistration is remotely committed are only: the exact frozen subject
source and Cargo metadata named below; the exact frozen release executable; the frozen G-0139
receipt solely to audit the repaired exact gate; static historical inputs strictly required by that
gate; isolated temporary mutants/copies outside scientific-output paths; and this review directory.

Custody is byte-specific. If any subject source, Cargo metadata, executable, G-0139 receipt, or
other bound input changes by even one byte, this audit and its receipt can never be reused; a new
outcome-blind preregistration and audit are required.

## Frozen identities supplied before inspection

| Object | Expected SHA-256 |
|---|---|
| `artifacts/math/G-0140/stage_b_pricer/src/main.rs` | `5c5cb1eb29eabe103373266b5d4c12f238ff49e1fae5d5861b602947319db484` |
| `artifacts/math/G-0140/stage_b_pricer/Cargo.toml` | `425d82de4e6d5902e2d3d7b005c5473225c4d6f197752590e89d7be670b2685c` |
| `artifacts/math/G-0140/stage_b_pricer/Cargo.lock` | `8875e1375a361873ac13bbcdf9e14c8ca7b34afa1438dfae9a6800f31325365a` |
| frozen release executable | `60bba95df068910daeb2e2ff763c750717238ca144f104cc59e9459b1eecb504` |

Commit-object bytes and working-tree bytes must match each other and these identities before any
behavioral result can count.

## Preregistered audit battery

The audit will fail closed unless every applicable item passes:

1. Verify the frozen commit exists, its named source/Cargo objects hash exactly, and the working
   bytes are identical to the commit objects.
2. Run `cargo fmt --check`, all three tests, `cargo clippy -- -D warnings`, a locked release build,
   the executable self-test, and `--preflight-static` only. Never run full `--preflight` or a
   scientific mode.
3. Rebuild from a clean isolated copy with `--locked --release` and require byte identity with the
   frozen executable.
4. Verify the exact named source-audit binding contract. Reject displaced recursive lookalikes and
   a correct decoy whose required named binding is missing.
5. Require fail-closed parsing for duplicate paths, unknown fields, audit self-reference, duplicate
   JSON keys, and trailing JSON data.
6. Verify the required nullable and mutation schemas, with positive controls and targeted malformed
   mutants.
7. Audit the repaired G-0139 exact gate: exact receipt SHA and commit plus evidence, claim, subject,
   source-audit, ancestry, entry/exit, counts, candidate fixed-map, and Stage-D fixed-map bindings.
   For each load-bearing binding, require missing, wrong, and displaced mutants to be rejected.
8. Verify compiled bindings for source, Cargo manifest, Cargo lockfile, G-0139 receipt, candidate,
   and kernel against independently computed hashes.
9. Verify overwrite refusal and end-of-run rehash/refusal behavior.
10. Exercise BigInt parsing/arithmetic paths, including values beyond native fixed-width integer
    ranges and malformed or sign-invalid variants as applicable.
11. Record an access log/diff demonstrating that prohibited future/scientific outputs were neither
    opened nor created.

Mutants will be constructed only in isolated temporary directories and will not modify the frozen
subject. A positive control is insufficient where a must-fail counterpart is specified.

## Decision rule and claim boundary

`PASS` / `SOURCE_CUSTODY_AUDIT_PASS_T1` may be emitted only if every preregistered check passes and
the receipt's `required_checks` key set exactly equals the Rust typed receipt struct discovered in
the frozen source, including `g0139_subject_and_exact_fixed_inputs_gate_verified`. The final receipt
must use the exact `claim_boundary` and `no_claim` constants compiled into that source. Any identity
mismatch, ambiguous executable location, inaccessible required static input, unexpected scientific
read, incomplete must-fail battery, or gate discrepancy forces a non-pass result with the defect
reported; no repair is in scope.
