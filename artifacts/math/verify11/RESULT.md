# Independent-semantics exact certificate verifier

Bead: `relu-depth-frontier-research-max11-root-gmp.14`

Agent: `IndigoCarp`

Implementation checkpoint: `3f4ed4d`

## Result

`tools/verify11` is a Rust implementation of the pinned upstream certificate
semantics. For every term it uses the lexicographically sorted ordered-cone
forms `base, other`, takes `direction = other - base`, drops directions that
are nonpositive on the sorted cone, divides retained directions by their
positive gcd, and checks that the exact rational combination has zero hinge
part and linear part exactly `x_n`.

The fast path is a subset DP over vertex placements. It tracks the complete
back-degree word of `right - left`; the fully symmetrized left-side linear form
is computed analytically. This supports loops, repeated edges, common edges,
and arbitrary equal branch sizes. The independent control path literally
enumerates all `n!` orders, evaluates both sides, and applies the upstream
`base/other` convention directly. Rational coefficients are cleared to one
exact common denominator; accumulation uses checked `i128` with automatic
`BigInt` promotion. No floating tolerance and no modular prime are used.

## Positive known-answer controls

Every numerator below names its denominator. `DP` is exact DP columns checked;
`literal` is exact DP/literal column agreements; `orders/term` is the complete
permutation denominator for every literal column.

| certificate | verdict | DP | literal | orders/term | coefficient common denominator | bad linear rows | bad hinge rows |
|---|---:|---:|---:|---:|---:|---:|---:|
| pinned n=5 | OK | 3/3 | 3/3 | 120/120 | 240 | 0/5 | 0/1 |
| pinned n=6 | OK | 4/4 | 4/4 | 720/720 | 1,440 | 0/6 | 0/7 |
| pinned n=7 | OK | 57/57 | 57/57 | 5,040/5,040 | 30,240 | 0/7 | 0/287 |
| pinned n=8 | OK | 69/69 | 69/69 | 40,320/40,320 | 1,209,600 | 0/8 | 0/818 |
| pinned n=9 | OK | 337/337 | not run (n>8) | not run | 21,772,800 | 0/9 | 0/4,713 |
| pinned n=10 | OK | 402/402 | not run (n>8) | not run | 304,819,200 | 0/10 | 0/13,834 |
| recovered n=9 | OK | 415/415 | not run (n>8) | not run | 326,592,000 | 0/9 | 0/4,780 |
| recovered n=10 | OK | 424/424 | not run (n>8) | not run | 304,819,200 | 0/10 | 0/11,865 |

Thus literal and DP semantics agree on every `133/133` pinned terms across
n=5..8, covering `3*120 + 4*720 + 57*5,040 + 69*40,320 = 3,072,600`
literal term-permutations in total. All `1,711/1,711` positive certificate
terms across the eight files were checked by DP. The `4/4` Rust unit tests
also include a loop/repeated/common-edge DP-vs-literal case, a malformed-input
refusal, a coefficient mutant, and an exact identity whose planted
coefficients exceed `i128`.

After that test-only source addition, the release binary was rebuilt from the
final bound source and the pinned n=5 control again returned OK with `3/3` DP
columns and `3/3` literal matches over `120/120` orders per term; see
`final_source_n5_literal_dp.json`.

## Negative controls in both directions

The two primary mutants use the pinned n=8 certificate so the independent
literal evaluator checks every term as well as the DP.

| mutation | expected/observed | DP | literal | orders/term | first exact residual | bad rows |
|---|---:|---:|---:|---:|---:|---:|
| add exactly `1/1` to term 1 coefficient | FAIL/FAIL | 69/69 | 69/69 | 40,320/40,320 | linear rank 1: `15,120/1` | 8/8 linear, 0/818 hinge |
| change one endpoint in term 1 from `[1,1]` to `[1,2]` | FAIL/FAIL | 69/69 | 69/69 | 40,320/40,320 | linear rank 1: `3/16` | 8/8 linear, 0/818 hinge |

Supplemental n=10 DP-only versions of the same two mutations also failed on
`402/402` terms: the coefficient mutant had `9/10` bad linear rows and first
residual `322,560/1`; the endpoint mutant had `9/10` bad linear rows and first
residual `11/270`. No control was weakened to obtain a passing result.

## n=11 timing control

Input: a deterministic loopless, branch-size-5, certificate-shaped file with
seed `20,260,902` and exactly `2,000/2,000` nonzero terms. Its SHA-256 is
`fc05999d88141d549e51a3aab98d8da83ec26d634e72de0681a326219631ce6d`.

On the shared host with exactly `4/4` requested Rayon threads:

- exact compute wall: `143.584994483` seconds / `2,000` terms;
- effective wall rate: `0.0717924972415` seconds/term, denominator `2,000` terms;
- emitted exact hinge entries: `58,130,351/58,130,351` processed;
- union hinge rows: `242,763/242,763` accumulated;
- peak RSS from `/usr/bin/time -v`: `767,120` KiB;
- linear projection at the measured 4-thread throughput: `358.9624862075`
  seconds / `5,000` terms (about 5.983 minutes), below the 6-hour feasibility
  bar without assuming any 16-thread speedup.

The random input correctly returned `FAIL`: `10/11` linear rows and
`242,436/242,763` union hinge rows were nonzero. This expected failure is only
a timing/control outcome. Per AmberBluff's instruction, no A100 run was made
and AzureAspen's active pricing pass was not overlapped.

## Commands

All commands ran from `tools/verify11` unless a path says otherwise.

```bash
CARGO_BUILD_JOBS=4 cargo build --release
CARGO_BUILD_JOBS=4 cargo test --release
CARGO_BUILD_JOBS=4 cargo clippy --release --all-targets --all-features -- -D warnings

target/release/max11-verify11 verify --certificate ../../literature/repos/max-relu-certificates/certificates/certificate_5_2.json --threads 4 --literal-check --output ../../artifacts/math/verify11/pinned_n5_literal_dp.json
target/release/max11-verify11 verify --certificate ../../literature/repos/max-relu-certificates/certificates/certificate_5_2.json --threads 4 --literal-check --output ../../artifacts/math/verify11/final_source_n5_literal_dp.json
target/release/max11-verify11 verify --certificate ../../literature/repos/max-relu-certificates/certificates/certificate_6_2.json --threads 1 --literal-check --output ../../artifacts/math/verify11/pinned_n6_literal_dp.json
target/release/max11-verify11 verify --certificate ../../literature/repos/max-relu-certificates/certificates/certificate_7_3.json --threads 1 --literal-check --output ../../artifacts/math/verify11/pinned_n7_literal_dp.json
target/release/max11-verify11 verify --certificate ../../literature/repos/max-relu-certificates/certificates/certificate_8_3.json --threads 1 --literal-check --output ../../artifacts/math/verify11/pinned_n8_literal_dp.json

target/release/max11-verify11 verify --certificate ../../literature/repos/max-relu-certificates/certificates/certificate_9_4.json --threads 1 --output ../../artifacts/math/verify11/pinned_n9_dp.json
target/release/max11-verify11 verify --certificate ../../literature/repos/max-relu-certificates/certificates/certificate_10_4.json --threads 1 --output ../../artifacts/math/verify11/pinned_n10_dp.json
target/release/max11-verify11 verify --certificate ../../artifacts/math/exact-witness-n9-n10/recovered_n9_upstream.json --threads 1 --output ../../artifacts/math/verify11/recovered_n9_dp.json
target/release/max11-verify11 verify --certificate ../../artifacts/math/exact-witness-n9-n10/recovered_n10_upstream.json --threads 1 --output ../../artifacts/math/verify11/recovered_n10_dp.json

target/release/max11-verify11 mutate-coefficient --certificate ../../literature/repos/max-relu-certificates/certificates/certificate_8_3.json --output ../../artifacts/math/verify11/pinned_n8_coefficient_plus_one.json
target/release/max11-verify11 mutate-endpoint --certificate ../../literature/repos/max-relu-certificates/certificates/certificate_8_3.json --output ../../artifacts/math/verify11/pinned_n8_endpoint_changed.json
target/release/max11-verify11 verify --certificate ../../artifacts/math/verify11/pinned_n8_coefficient_plus_one.json --threads 2 --literal-check --output ../../artifacts/math/verify11/pinned_n8_coefficient_plus_one_report.json  # expected exit 1
target/release/max11-verify11 verify --certificate ../../artifacts/math/verify11/pinned_n8_endpoint_changed.json --threads 2 --literal-check --output ../../artifacts/math/verify11/pinned_n8_endpoint_changed_report.json  # expected exit 1

target/release/max11-verify11 generate-synthetic --n 11 --terms 2000 --branch-edges 5 --seed 20260902 --loopless --output ../../artifacts/math/verify11/synthetic_n11_2000_seed20260902.json
/usr/bin/time -v target/release/max11-verify11 analyze --certificate ../../artifacts/math/verify11/synthetic_n11_2000_seed20260902.json --threads 4 --output ../../artifacts/math/verify11/synthetic_n11_2000_local4_report.json
```

The n=6,7,8 controls were launched concurrently with one thread each; the four
n=9/n=10 positive controls were launched concurrently with one thread each;
each pair of negative controls used two threads per process. Aggregate host use
therefore remained at or below four threads.

## Bindings

| input or implementation | SHA-256 |
|---|---|
| pinned upstream Python verifier | `d6da3030b719735b10a197dc79d7e311ecc90f70314ed748de81087f94f039a7` |
| pinned n=5 certificate | `698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694` |
| pinned n=6 certificate | `026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83` |
| pinned n=7 certificate | `b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be` |
| pinned n=8 certificate | `68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3` |
| pinned n=9 certificate | `4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88` |
| pinned n=10 certificate | `10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4` |
| recovered n=9 certificate | `d0302e2eecfdd85ca3a3887086b03d1aec86e9e5db7c2ed19666a4d9636c3f28` |
| recovered n=10 certificate | `4bcb155a416188d479f20a2009f077003e828f1f09d65476117523a3bb6644e9` |
| `tools/verify11/src/lib.rs` | `a86c32b1e61f342d8db932009fc104a11961e588cb56f499b6592aa96a0066b2` |
| `tools/verify11/src/main.rs` | `4c7e447d8b117febc8ff9eb2db5fa8a3d8d46e25981d6a4a3c661a6b1caf9b29` |
| `tools/verify11/Cargo.lock` | `e5e66cc67a27970449c516b5193f23a74ac31afb839e5c2e275f78d4ae217288` |

Primes: none (`0/0`); all verifier equalities and residuals above use exact
integer/rational arithmetic.

## No-claim

This work establishes agreement of two exact implementations on the finite
known-answer controls and shows that this implementation can process the named
synthetic n=11 workload within the stated timing/memory bounds. The synthetic
input is not a certificate and its failure proves nothing about MAX11. This
bead did not verify an n=11 identity, did not decide membership in the complete
loopless degree-5 family, did not prove that any finite ansatz is complete, and
did not establish an unrestricted two-hidden-layer lower bound. If EXP-0036
returns MEMBER, its translated rational certificate still must be checked on
every term and every exact normal-form row by this verifier before any identity
claim is made.
