# Independent-semantics exact certificate verifier

Bead: `relu-depth-frontier-research-max11-root-gmp.14`

Agent: `IndigoCarp`

Initial implementation checkpoint: `3f4ed4d`

Initial evidence checkpoint: `aa1039e`

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
terms across the eight files were checked by DP. The original `4/4` Rust unit tests
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

## n=11 literal-mode preflight

After EXP-0036 stage A returned MEMBER on its bounded sketch, literal mode was
extended from n=8 through n=11 and a deterministic, source-hashed sampling
command was added. A one-term preflight selected zero-based term `432/2,000`
from the synthetic timing input with seed `20,260,902`. DP and literal columns
agreed on `1/1` term after the literal path enumerated all
`39,916,800/39,916,800` permutations. With `1/1` thread, exact compute wall was
`19.327432549` seconds / `1` term (`0.491386240` DP worker seconds and
`18.799231377` literal worker seconds); `/usr/bin/time -v` reported peak RSS
`54,572` KiB. The random one-term identity verdict was FAIL, as expected:
`9/11` linear rows and `41,977/41,977` union hinge rows were nonzero. This is a
literal/DP semantic and scale control, not evidence about MAX11.

## Dense huge-coefficient fallback hardening

The verifier now reads certificate JSON with two streaming passes instead of
materializing the complete `terms` array. Pass one validates all terms and
fixes one exact denominator-clearing factor. Pass two holds at most `4` terms
for a four-thread run, computes their structural columns in parallel, and
serially merges them into `1/1` exact accumulator map. If all terms repeat the
same textual denominator, it is parsed once and every second-pass numerator is
already the denominator-cleared integer. Streaming reports record the minimum
and maximum coefficient digit counts over every supplied term.

The expanded `5/5` unit suite includes a new exact positive n=2 identity with
`2/2` terms sharing a 201-digit denominator and numerators beyond `i128`;
streaming DP and literal mode agree on `2/2` columns and the identity is OK.
The post-change pinned n=5 positive remained OK on `3/3` DP and literal
columns, and the coefficient-mutated n=8 negative remained FAIL on `69/69` DP
columns with literal=DP on `69/69` columns. No control was weakened.

### Required 2,000-term big-rational benchmark

The final pool-1 benchmark input contains `2,000/2,000` n=11 loopless,
branch-size-5 terms. Every coefficient has a random signed 100,000-digit
numerator over the same random 100,000-digit denominator; the verifier's census
was numerator digits `[100,000,100,000] / 2,000 terms` and denominator digits
`[100,000,100,000] / 2,000 terms`. The shared denominator's SHA-256 is
`29c13e696e483019d6463a4f360fc1ce8207c84c00c63588b8daec0a15c4a252`.
The input is `400,191,002` bytes, SHA-256
`dc370ec0871dc6d9c2f3f87294a0bc16026c704c449d4a25fb2dc93b77a0b2ae`.

On exactly `4/4` threads, the final-code run checked `2,000/2,000` DP columns
and emitted `6,620,000/6,620,000` exact hinge entries into a
`3,310/3,310`-row union. Compute wall was `204.429998294` seconds / `2,000`
terms, or `0.102214999147` seconds/term with denominator `2,000` terms.
External wall was `206.55` seconds / `2,000` terms and peak RSS was
`209,248` KiB. The report SHA-256 is
`41582e44e21bb6637faca3935f9f4bea415aa77e08b4691a295a2dd043a8a155`.
The random input returned FAIL with `10/11` bad linear rows and `3,310/3,310`
bad hinge rows, as expected; this is a performance control only.

A stronger pool-8 run deliberately expanded the union to
`105,679/105,679` rows, roughly five times the run7 rank scale. Its
`2,000/2,000` coefficients had the same exact 100,000/100,000-digit census;
the `400,194,482`-byte input SHA-256 was
`73bc7a5d3a29c73fb8290708b09e4cf1fa6229613760a1c03bb5197da6c3259a`.
It processed `63,409,000/63,409,000` hinge entries in
`1,126.738737718` compute seconds / `2,000` terms
(`0.563369368859` seconds/term), with `1,129.09` external seconds / `2,000`
terms and peak RSS `4,595,980` KiB on `4/4` threads. This exceeded the 4 GB
host target and is recorded as a failed memory control, not a pass. The report
SHA-256 is
`9848fd3d7ca7a4f6654df66cbf80da78bc22a6e96ac66c64fc07f4bc6fa9bfaf`.
Its random identity verdict was FAIL (`10/11` linear and
`105,679/105,679` hinge rows bad), which has no MAX11 significance.

### 1.2 GB streaming-ingress control

A `6,000/6,000`-term input with the same 100,000-digit numerator and
100,000-digit shared-denominator format occupied `1,200,585,059` bytes and had
SHA-256
`c2ca99d3f5f6e4d2478b09d08a6a4c06e59c01e0f5eb86f181639c0e4f1f6843`.
The streaming sampler hashed it and made two complete JSON passes while
retaining only `20/6,000` terms. External wall was `16.22` seconds / `6,000`
source terms and peak RSS `8,320` KiB. Seed `20,260,903` selected zero-based
indices `42, 106, 1487, 1579, 1632, 1661, 2039, 2176, 3116, 3248, 3566,
3711, 3733, 3756, 4350, 4386, 4647, 4696, 5019, 5387`; the
`4,013,519`-byte sample SHA-256 was
`0ecd7d7d23c9615a9940cba502e6ff6169d93527f338a6143d3a9ec700ae3a9f`.
This controls large-file ingress only: no full DP evaluation of the
`6,000/6,000`-term, 1.2 GB input was run.

Two pool-2 calibration probes used `2/2` terms with 10-digit numerators and
denominators. Seeds `20,260,906` and `20,260,907` produced respectively
`31,994/31,994` and `33,788/33,788` union rows. They were temporary sizing
probes, not performance or identity evidence. One earlier big-input generator
attempt accidentally used a stale release binary and emitted the old
small-coefficient format; that disposable file was deleted before hashing and
is not counted as evidence.

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

target/release/max11-verify11 sample --certificate ../../artifacts/math/verify11/synthetic_n11_2000_seed20260902.json --terms 1 --seed 20260902 --output ../../artifacts/math/verify11/preflight_synthetic_n11_sample1.json
/usr/bin/time -v target/release/max11-verify11 analyze --certificate ../../artifacts/math/verify11/preflight_synthetic_n11_sample1.json --threads 1 --literal-check --output ../../artifacts/math/verify11/preflight_synthetic_n11_sample1_literal_dp.json

# The following dense-fallback commands ran from the repository root.
tools/verify11/target/release/max11-verify11 generate-synthetic --n 11 --terms 2000 --branch-edges 5 --loopless --seed 20260903 --coefficient-digits 100000 --structure-pool 1 --output artifacts/math/verify11/synthetic_n11_2000_bigcoef100k_seed20260903.json
/usr/bin/time -v tools/verify11/target/release/max11-verify11 analyze --certificate artifacts/math/verify11/synthetic_n11_2000_bigcoef100k_seed20260903.json --threads 4 --output artifacts/math/verify11/synthetic_n11_2000_bigcoef100k_seed20260903_report_v2.json

tools/verify11/target/release/max11-verify11 generate-synthetic --n 11 --terms 2000 --branch-edges 5 --loopless --seed 20260905 --coefficient-digits 100000 --structure-pool 8 --output artifacts/math/verify11/synthetic_n11_2000_bigcoef100k_pool8_seed20260905.json
/usr/bin/time -v tools/verify11/target/release/max11-verify11 analyze --certificate artifacts/math/verify11/synthetic_n11_2000_bigcoef100k_pool8_seed20260905.json --threads 4 --output artifacts/math/verify11/synthetic_n11_2000_bigcoef100k_pool8_seed20260905_report.json

tools/verify11/target/release/max11-verify11 generate-synthetic --n 11 --terms 6000 --branch-edges 5 --loopless --seed 20260904 --coefficient-digits 100000 --structure-pool 1 --output artifacts/math/verify11/synthetic_n11_6000_bigcoef100k_ingress_seed20260904.json
/usr/bin/time -v tools/verify11/target/release/max11-verify11 sample --certificate artifacts/math/verify11/synthetic_n11_6000_bigcoef100k_ingress_seed20260904.json --terms 20 --seed 20260903 --output artifacts/math/verify11/synthetic_n11_6000_bigcoef100k_ingress_sample20.json
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
| n=11 literal preflight sample | `97363265e2fa73222f9228a522acb0447f0dd507d9edaf64dbed53983a6747ca` |
| n=11 literal preflight report | `9187b7974229436a7dc6710eea52d9de29dce3421ec18a89b27de771f286fb2b` |
| 2,000-term 100k/100k-digit pool-1 report | `41582e44e21bb6637faca3935f9f4bea415aa77e08b4691a295a2dd043a8a155` |
| 2,000-term 100k/100k-digit pool-8 report | `9848fd3d7ca7a4f6654df66cbf80da78bc22a6e96ac66c64fc07f4bc6fa9bfaf` |
| `tools/verify11/src/lib.rs` | `5bc9a14f1df11fd027ff9f0e4bf3ac005e7f0d16364bd1f2c83cd1663a1667c5` |
| `tools/verify11/src/main.rs` | `5d0299374c39288c21393f964a40ef42f26b408dd784cf270eec5b7ae627c203` |
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
