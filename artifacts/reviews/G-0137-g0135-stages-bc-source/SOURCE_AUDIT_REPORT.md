# G-0137 outcome-blind source audit — G-0135 Stages B/C

## Verdict

**PASS**, at T1 source-clearance strength, for the exact committed subjects below.  The audit observed no G-0135 scientific manifest or output and did not run Stage A, Stage B production, or Stage C production.  This verdict authorizes only a later preregistered run of these exact bytes; it is not a mathematical result.

| Subject | Git commit | SHA-256 |
|---|---|---|
| Stage B source | `0291920fde55fd9cf6f2429fe64bb52cc83326b8` | `c591504757815ff63c46d29cfcc2ac10568bea92212ade32490def93b5d862b2` |
| Stage B `Cargo.toml` | `73ec8f6d29f7308b18be4d49f990bf3b29a400d0` | `a4057885f58199feb18e733ca01c7ec2a00dc05d8f2700a6dcb04f56825af11d` |
| Stage B `Cargo.lock` | `73ec8f6d29f7308b18be4d49f990bf3b29a400d0` | `72315f7a541bf34fe135a25e651d2d85a885652944bdcac6862fb770d29669d3` |
| Stage B release executable | `0291920fde55fd9cf6f2429fe64bb52cc83326b8` | `e2e84801749bc0f2ca7bf18a149895531038ee0eab68f964b01ad25f1a3de7ef` |
| Stage C source | `ff579acd4dcad838a582cd6c8411fdec5650d94e` | `c84f259d393756c9ff658aab9a1488b145b9607a939dbccfce47069168b40a1a` |
| Stage C wrapper | `0291920fde55fd9cf6f2429fe64bb52cc83326b8` | `b125566098be17edc0a572b776e1887813758afc7412324c29408592275ab508` |

## What was checked

Stage B fail-closes on the exact Stage-A/shared-manifest schemas, strict signed-`i8` direction order, canonical nonzero BigInt residuals, digests, fixed 163,740-record census, direction-major 5,239,680-coordinate census, arbitrary-precision dots, entry/exit custody, and atomic no-overwrite publication.  Its shared manifest now denies unknown fields and its planned outputs are typed and exact.

Stage C preserves the 380-row prefix, appends 32 rows in receipt order, uses the unscaled old target followed by 32 zeros, replays the 176-column warm start, reopens all 163,740 columns, requires exact rank changes, and admits only exact member or exact all-column separator terminals.  Both terminals replay their certificates.  Its manifest key sets and planned outputs are exact, and its fixed-input path rehashes snapshots before publication.

The final runtime hardening verifies CPython 3.13.7 under the repository `.venv`, `python-flint` 0.9.0 metadata, the pinned RECORD hash, all 139 RECORD rows, and every one of 114 hash-bearing installed files **before** importing the native `flint` module.  The independent probe repeats that ordering in a separate process.

The fresh probe did not import either producer.  For Stage B it compared literal injection enumeration, an independently transcribed subset DP, and the frozen G-0117 kernel on two planted active-four records and eight directions; all prices agreed.  It rejected coordinate, census, coefficient, direction-order, and residual mutants and exercised a dot exceeding signed 128-bit range.  For Stage C it independently solved exact rational member and nonmember fixtures and rejected target-scale, omitted-column, row-order, coefficient, separator-sign, separator-coordinate, and separator-pairing mutants.

Production-facing checks passed: Rust format, locked release clippy, 3/3 locked release tests, locked release rebuild with identical executable hash, Stage B self-test/static preflight, Python AST parse, Ruff 0.16.5, wrapper shell syntax, Stage C self-test with 15 hostile controls and both exact branches, toolchain known answers, Lean smoke, and skill-ledger quick verification.  Unpinned system Python and out-of-scope Stage B/C output paths were rejected.  All four prohibited scientific paths were absent before and after.

## Audit history and residual risk

The first review found two blocking defects: permissive shared-manifest fields/planned outputs and an inadequately pinned Stage C invocation.  No receipt was issued.  The author corrected them in committed subjects.  A later review found that native `flint` was imported before installed-byte verification; commit `ff579acd4dcad838a582cd6c8411fdec5650d94e` reversed that order.  Every provisional green run was invalidated when subject bytes changed; the receipts bind only the final hashes above.

Residual risk remains bounded: RECORD verification is local hash attestation, not a signed software-supply-chain proof; this is a same-lineage T1 source audit, not T2 independence; and no future scientific manifest, selected Batch32, coordinate pack, member, or separator has been examined.  Any actual output still requires its preregistered clean-room result audit.

## No-claim

This audit does not establish a residual, coordinate pack, exact member, separator, global identity, unrestricted MAX11 statement, lower bound, minimality result, or Lean theorem.  It certifies only that the exact frozen B/C sources passed the preregistered outcome-blind source checks.

## Honesty inventory

Session/window reviewed: the complete G-0137 audit, its diffs, command outputs, parent hash handoffs, and the delegated G-0138 setup.

1. No (checked: the reviewer changed no subject test/CI/config; Stage B ran 3/3 tests).
2. No (checked: planted fixtures compare three independent arithmetic routes and both exact Stage C branches; no subject mock replaces behavior).
3. No (checked: no golden or snapshot was regenerated).
4. No (checked: reviewer edits are confined to this audit directory; subject hardening was separately committed before rebinding).
5. No (checked: fixed preregistered 163,740/32/5,239,680 censuses and all-column semantics were preserved; no scientific run was narrowed).
6. No (checked: Rust reported 3 tests; Stage C reported 15 rejected controls plus two positive branches; the probe executed planted routes).
7. No (checked: every reported command appears in the observed command log or the final independent receipt).
8. No (checked: fixtures are labelled fixtures and the verdict is explicitly T1, never a scientific result).
9. No (checked: initial blockers, invalidated provisional runs, and the final import-order correction are disclosed above).
10. No (checked: cited final commands exposed exit status/output; redirected exploratory probe output was not used as the final receipt).
11. No (checked: only this preregistered audit is closed, after all required artifacts and checks).
12. No (checked: `PREREGISTRATION.md` remained byte-identical at `e2bda629...`).
13. No (checked: the G-0138 child did not close this audit or its own task during this review).
14. No (checked: the child prompt required positive fixtures, hostile mutants, exact bindings, and a no-claim line).
15. No (checked: parent-provided B/C hashes were recomputed; no child report was accepted as B/C evidence).
16. No (checked: the G-0138 child fail-closed twice on incorrect/stale commit identifiers and then resumed the positive audit).
17. No (checked: same-lineage agreement is expressly capped at T1).
18. No (checked: all denominators/censuses were preregistered before this audit).
19. No undisclosed moment (checked: both premature hash handoffs and every subject-byte invalidation were immediately reported and rerun).
20. Strongest evidence: the re-executable `independent_probe.py` and its hash-bound receipt, which compare independent exact routes and fail hostile mutants against the exact committed subjects.

The required CASS sweep used the five suggested phrases plus `scientific output observed`; inspected hits were prior research/protocol discussions, not evidence of a hidden G-0137 gate change.  Disposition: looked, found no uncorrected honesty issue.  The only encountered defects were corrected in the subject by separate commits, disclosed, rebound, and rerun before PASS.
