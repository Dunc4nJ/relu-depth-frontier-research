# verify11 checked `ExactInt::add_mul` promotion

Date: 2026-09-03 (Europe/Berlin)  
Bead/thread: `relu-depth-frontier-research-u0j`  
Agent: `IndigoCarp`

## Result

Fixed the single T2-referee finding in `ExactInt::add_mul`: when the accumulator target is `BigInt` but the scaled coefficient is `i128`, the coefficient/factor product now uses `checked_mul`. A product that fits remains on the `i128` fast path; overflow promotes the multiplication operands to `BigInt` before the exact addition.

No other verify11 behavior or source file was changed. `tools/verify11/src/main.rs` remained byte-identical.

## Binary and source bindings

| object | before SHA-256 | after SHA-256 |
|---|---|---|
| `tools/verify11/target/release/max11-verify11` | `bab4ab22fa0acaa2c49c5c91bc6fa5fb006afd7ed843f6a008049bc65d4d1eb9` | `85af29b2ca8deddf5ab03ea55e3ca0853e90f1be9aa517d27932202e6574e33e` |
| `tools/verify11/src/lib.rs` | `5bc9a14f1df11fd027ff9f0e4bf3ac005e7f0d16364bd1f2c83cd1663a1667c5` | `5d700da8b96f2bc1cfd227ab2261e906663f72e3eae2c860c5c1d564048a1764` |
| `tools/verify11/src/main.rs` | `5d0299374c39288c21393f964a40ef42f26b408dd784cf270eec5b7ae627c203` | `5d0299374c39288c21393f964a40ef42f26b408dd784cf270eec5b7ae627c203` |

The before binary is the frozen binary used for both n=11 T1 candidate protocols immediately before this bead. The after binary was produced by the locked release build shown below.

## Boundary-straddling regression: red then green

The final regression constructs a genuine two-term n=5 certificate fixture using the existing loop/repeat/common-edge atom. Denominator clearing produces scaled coefficients `i128::MAX + 1` (stored as `BigInt`) and `i128::MAX` (stored as `i128`). Adding the first term makes the retained-hinge accumulator `BigInt`; adding the second term with a genuine hinge multiplicity greater than 1 enters the formerly unchecked `(Big target, Small coefficient)` branch. The test asserts the exact `BigInt` accumulator, not a float or residue modulo a prime.

Final old-code red command:

```text
source scripts/activate-toolchain.sh && CARGO_BUILD_JOBS=4 cargo test --manifest-path tools/verify11/Cargo.toml --release --locked tests::boundary_straddling_certificate_promotes_big_target_small_product -- --exact
```

Old-code result: `0/1` tests passed, exit status 101/101 expected Rust test-failure status. The release-mode wrapped accumulator was
`340282366920938463463374607431768211454/1`; the exact expected accumulator was
`680564733841876926926749214863536422910/1`.

After the checked multiply/promotion change, the identical command returned `1/1` tests passed and exit status 0/1 possible pass status.

Two earlier fixture trials are recorded and are not counted as the red control:

1. The first command omitted the module-qualified test name while also using `--exact`; it selected 0/6 library tests and therefore established nothing.
2. The first n=2 fixture then selected 1/6 tests but failed its fixture assertion because it produced 0/1 retained hinge rows. That failure occurred before the overflow branch and established nothing. The final n=5 fixture above is the branch-exercising red/green control.

## Build and unit controls

Exact command:

```text
source scripts/activate-toolchain.sh && cargo fmt --manifest-path tools/verify11/Cargo.toml -- --check && CARGO_BUILD_JOBS=4 cargo test --manifest-path tools/verify11/Cargo.toml --release --locked && CARGO_BUILD_JOBS=4 cargo clippy --manifest-path tools/verify11/Cargo.toml --release --locked --all-targets --all-features -- -D warnings && CARGO_BUILD_JOBS=4 cargo build --manifest-path tools/verify11/Cargo.toml --release --locked
```

Results: formatting passed; release unit tests passed 6/6 and failed 0/6; doc tests passed 0/0 (none defined); clippy passed with warnings denied; locked release build passed. Host build parallelism was bounded at 4 jobs/command.

## Pinned n=5..10 positive controls

No modular primes were used (`0/0` primes); each row below used exact denominator clearing and exact integer accumulation. n=5..8 additionally ran complete literal enumeration.

| pinned certificate | input SHA-256 | verdict | DP terms | literal/DP matches | permutations/term | common denominator | bad linear rows | bad hinge rows |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| n=5 `certificate_5_2.json` | `698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694` | OK | 3/3 | 3/3 | 120/120 | 240 | 0/5 | 0/1 |
| n=6 `certificate_6_2.json` | `026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83` | OK | 4/4 | 4/4 | 720/720 | 1,440 | 0/6 | 0/7 |
| n=7 `certificate_7_3.json` | `b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be` | OK | 57/57 | 57/57 | 5,040/5,040 | 30,240 | 0/7 | 0/287 |
| n=8 `certificate_8_3.json` | `68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3` | OK | 69/69 | 69/69 | 40,320/40,320 | 1,209,600 | 0/8 | 0/818 |
| n=9 `certificate_9_4.json` | `4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88` | OK | 337/337 | not run, 0/0 | not run, 0/0 | 21,772,800 | 0/9 | 0/4,713 |
| n=10 `certificate_10_4.json` | `10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4` | OK | 402/402 | not run, 0/0 | not run, 0/0 | 304,819,200 | 0/10 | 0/13,834 |

Totals: 872/872 pinned positive terms passed DP. For n=5..8, literal and DP matched on 133/133 terms over 3,072,600/3,072,600 complete term-permutations.

Exact commands (n=5..8 were concurrent at 1 thread/process, then n=9..10 were concurrent at 1 thread/process; aggregate requested verifier threads never exceeded 4):

```text
tools/verify11/target/release/max11-verify11 verify --certificate literature/repos/max-relu-certificates/certificates/certificate_5_2.json --threads 1 --literal-check --output artifacts/math/verify11-add-mul-overflow/pinned_n5_literal_dp.json
tools/verify11/target/release/max11-verify11 verify --certificate literature/repos/max-relu-certificates/certificates/certificate_6_2.json --threads 1 --literal-check --output artifacts/math/verify11-add-mul-overflow/pinned_n6_literal_dp.json
tools/verify11/target/release/max11-verify11 verify --certificate literature/repos/max-relu-certificates/certificates/certificate_7_3.json --threads 1 --literal-check --output artifacts/math/verify11-add-mul-overflow/pinned_n7_literal_dp.json
tools/verify11/target/release/max11-verify11 verify --certificate literature/repos/max-relu-certificates/certificates/certificate_8_3.json --threads 1 --literal-check --output artifacts/math/verify11-add-mul-overflow/pinned_n8_literal_dp.json
tools/verify11/target/release/max11-verify11 verify --certificate literature/repos/max-relu-certificates/certificates/certificate_9_4.json --threads 1 --output artifacts/math/verify11-add-mul-overflow/pinned_n9_dp.json
tools/verify11/target/release/max11-verify11 verify --certificate literature/repos/max-relu-certificates/certificates/certificate_10_4.json --threads 1 --output artifacts/math/verify11-add-mul-overflow/pinned_n10_dp.json
```

Report SHA-256 values, in n order:

- n=5: `613a9bbafa5cf87c29a5f9e53e0905c65392409b2ec8c1402fccccc2210ca1d8`.
- n=6: `7bd21e3d9e2c2dc54fca2b3ac5e8f9d080a72faa9a9b7f72b5aa531556c73bf4`.
- n=7: `5d1b59e2599f9711d0f555e79ad85c23b5b2b70c778cba9e4899e8dc4e899902`.
- n=8: `6b85b061bda2926e88f45864f42e322a006923d4394e9ebbc0fd3006ae4eaa5c`.
- n=9: `244b20f1e40f9c756c20d4e2032041be96478c329ad76c5b11ad5fa7c00b3e9a`.
- n=10: `009c4d22bc4b6897ece1e0dbcf975b0bb19c4cdc36999152336acde8f2392cc4`.

## Pinned negative controls

The already-pinned n=8 mutants were rerun concurrently at 2 threads/process (4 requested threads total):

```text
tools/verify11/target/release/max11-verify11 verify --certificate artifacts/math/verify11/pinned_n8_coefficient_plus_one.json --threads 2 --literal-check --output artifacts/math/verify11-add-mul-overflow/pinned_n8_coefficient_plus_one_report.json
tools/verify11/target/release/max11-verify11 verify --certificate artifacts/math/verify11/pinned_n8_endpoint_changed.json --threads 2 --literal-check --output artifacts/math/verify11-add-mul-overflow/pinned_n8_endpoint_changed_report.json
```

| mutant | input SHA-256 | expected/observed | process exit | DP terms | literal/DP matches | permutations/term | common denominator | first exact residual | bad rows |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| coefficient +`1/1` | `101d1642b7a537f4012ef59384aa0a139b83413c587e277f8ace732fce3d241a` | FAIL/FAIL | 1/1 | 69/69 | 69/69 | 40,320/40,320 | 1,209,600 | linear rank 1: `15120/1` | 8/8 linear, 0/818 hinge |
| one endpoint changed | `94d3d91d8233b81226139bd9985e115c6f0c35cfcab6fe10377abc7694006100` | FAIL/FAIL | 1/1 | 69/69 | 69/69 | 40,320/40,320 | 1,209,600 | linear rank 1: `3/16` | 8/8 linear, 0/818 hinge |

- Coefficient-mutant report SHA-256: `72a67e15de0c0e49c4cb3648374442a567fb1ddc57a004e282c156f4091407c0`.
- Endpoint-mutant report SHA-256: `857c19a7cdfef4e21dec5341f17f04d8048888229b16303f40d0a3dbbe759ce5`.

No control was weakened to obtain a passing result.

## What was not verified / no-claim

The T2 referee established that this branch was unreachable for the run7 and F2 inputs because all their denominator-cleared coefficients were `BigInt`; this bead did not rerun either long n=11 candidate after the fix. The work verifies one arithmetic branch and the finite pinned n=5..10/control suite. It does not add a new identity, prove a lower bound, generalize beyond the verifier's pinned semantics, or independently re-referee the n=11 certificates.
