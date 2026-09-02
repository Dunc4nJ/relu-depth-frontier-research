# RESULT — `relu-depth-frontier-research-max11-root-gmp.1`

## Outcome

Implemented `tools/colgen/`, a checked-integer Rust generator for the full
ordered-cone sparse column of a loopless signed-`W` record.  It supports exact
integer and single-prime modular output, ordered JSONL and a documented compact
binary format, bounded-batch parallel emission, support scans, deterministic
benchmarks, exact saved-template comparison, literal-permutation comparison,
and frozen modular-dual price-vector comparison.

Code checkpoint: Git commit `c71ce0d`.

Final producer bindings:

| object | SHA-256 |
|---|---|
| `tools/colgen/src/lib.rs` | `81f6618d57c09fb1694f0b97a4e493853193f48249ddde5a7b612e795a850eb5` |
| `tools/colgen/src/main.rs` | `cadc4d79cef6bfc9fe7a06a0207a60f79333d34da193355b382873a74f36cca1` |
| `tools/colgen/Cargo.toml` | `20b752caf1c4f1ccede5f1f686ebdb3199236b975ae573fc6f190b6141b6c15b` |
| `tools/colgen/Cargo.lock` | `a8551b0e564293bc4ebe0a8fba37afc08abed6d68ed0bd40bb42dbbeb8792a1d` |
| release executable (not committed) | `32620edca7e14874c5065f421ae2fbe906339bcccdd67bdd0167223bd49e319f` |

## Exact convention

For `W=B-A`, the raw word for permutation `pi` is
`w_r=sum_{t<r} W[pi_r,pi_t]`.  A nonzero word contributes its gcd to the
primitive first-nonzero-positive direction.  Directions nonpositive on the
sorted cone are omitted.  When the first nonzero raw entry is negative, `w`
is added to the linear coordinates using `ReLU(-z)=ReLU(z)-z`.  The fixed
loopless branch base is `2*k*r*(n-2)!`.

This equals the Python reference convention exactly: its lexicographically
smaller branch word is `A` when the first nonzero entry of `w` is positive and
`B=A+w` otherwise.  No floating arithmetic or sampled evaluation is used in
the comparison.

## Commands and results

Build and static checks (final source):

```bash
cd /data/projects/relu-depth-frontier-research/tools/colgen
cargo fmt --check
cargo test --release
cargo clippy --all-targets --all-features -- -D warnings
cargo build --release
```

Result: PASS; 5/5 unit tests passed, including dynamic-program versus literal
permutations, branch-swap invariance, fixed-base zero signed graph, branch
cancellation, and the one-sign schema mutant.

The n=5,6,7 template files were generated with the existing independent
Python/pynauty implementation (two workers each):

```bash
source /data/projects/relu-depth-frontier-research/.venv/bin/activate
python /data/projects/relu-depth-frontier-research/handoff/2026-09-02-amberbluff/probes/loopless_probe_par.py N --workers 2 --prime 1000003
```

The exact commands were run for `N=5`, `N=6`, and `N=7` from
`artifacts/math/colgen-rust/controls/`.  Input/output hashes:

| n | templates (denominator) | template SHA-256 | literal orderings per template | exact sparse matches | literal matches |
|---:|---:|---|---:|---:|---:|
| 5 | 19 | `a890399bd499382a878490f1df348e94804796e77bfe791ffe73abf6e67b0e6b` | 120 | 19/19 | 19/19 |
| 6 | 25 | `a72e814b310bda3bfe03badcc87e247853f35c86aec2ff19328c5d8c0375eed0` | 720 | 25/25 | 25/25 |
| 7 | 357 | `de45563dc8a8ddce410a6a97a1ac538669741db4e98e4fb806d519bdc51b5b62` | 5,040 | 357/357 | 357/357 |

Final validation command shape, with `N,K` set to `(5,2)`, `(6,2)`, and
`(7,3)` and two threads per concurrently run command:

```bash
tools/colgen/target/release/max11-colgen validate-templates \
  --input artifacts/math/colgen-rust/controls/loopless_system_nN.jsonl \
  --n N --branch-edges K --threads 2 \
  --output artifacts/math/colgen-rust/controls/nN_literal_validation_v2.json \
  --bruteforce
```

Complete saved-system comparisons on final code:

```bash
tools/colgen/target/release/max11-colgen validate-templates \
  --input handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --n 9 --branch-edges 4 --threads 3 \
  --output artifacts/math/colgen-rust/n9_saved_system_validation_v2.json

tools/colgen/target/release/max11-colgen validate-templates \
  --input handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --n 10 --branch-edges 4 --threads 3 \
  --output artifacts/math/colgen-rust/n10_saved_system_validation_v2.json
```

Results: exact integer equality of every linear coordinate and every sparse
hinge coefficient for 10,976/10,976 n=9 templates (input SHA-256
`729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991`)
and 12,248/12,248 n=10 templates (input SHA-256
`bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18`).

Planted negative on final code:

```bash
tools/colgen/target/release/max11-colgen validate-templates \
  --input artifacts/math/colgen-rust/controls/loopless_system_n5.jsonl \
  --n 5 --branch-edges 2 --threads 1 \
  --output artifacts/math/colgen-rust/controls/sign_mutant_must_not_exist.json \
  --mutate-one-sign
```

Expected exit 1 at template 1: `signed edge counts do not equal signed_mass`.
No output report was written.  This flips one signed occurrence and is caught
before it can be laundered into a zero-sum hinge column.  The initial version
of this control stopped on the zero signed graph at template 0; that was not a
potent sign mutation, so the harness was corrected to leave zero records alone
and attack the first nonzero record.  The acceptance condition was not
weakened.

Exact/modular stream round-trip:

```bash
tools/colgen/target/release/max11-colgen emit-universe \
  --universe artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --threads 3 --start 0 --limit 3 --format jsonl \
  --output artifacts/math/colgen-rust/emit_first3_exact_v1.jsonl

tools/colgen/target/release/max11-colgen emit-universe \
  --universe artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --threads 3 --start 0 --limit 3 --format binary --modulus 1000003 \
  --output artifacts/math/colgen-rust/emit_first3_p1000003_v1.bin
```

An independent Python `struct` parser read the documented binary schema and
compared every coefficient to the exact JSONL coefficient reduced modulo
1,000,003: `EMIT_ROUNDTRIP_PASS records=3/3 modulus=1000003`.  Exact JSONL
SHA-256: `0f24b4efea4926c48e4edc98fde4932d6c3baccfa5600c6f58794bd156358ad2`;
binary SHA-256: `7b00800679544e73957af0c58bb078c458da6ee2878fbd83959df5c46ba0bc7f`.

G-0028 full registered price-vector control on final code:

```bash
tools/colgen/target/release/max11-colgen validate-prices \
  --universe artifacts/math/G-0028/g0025_registered_loopless_signed_records_v1.json.gz \
  --dual artifacts/math/G-0028/g0025_rank_one_sparse_modular_dual_v1.json \
  --expected-report artifacts/math/G-0028/g0025_registered_delta_replay_v1.json \
  --threads 6 \
  --output artifacts/math/colgen-rust/g0028_registered_price_validation_v2.json
```

Subject denominator: 13,419 records.  Input SHA-256 values: records
`e13d166767719d545ac43e0ebdad3a227e6c7b714029a8a952afdd7b9f3c1b59`,
dual `862667d464fe842b17baebd1a3c9933fc27012ea1129a94631d75cadfed5143c`,
and frozen expected report
`a72ce51b3925af36a9644734f9212fae56b77b28b95df8754e50398d9e2b4db8`.

Final run: PASS in 598.153213566 s for 13,419/13,419 records
(22.4340515033 records/s).  Report SHA-256:
`96db103dc4e1708663875d01b648ca56e2e628df69ae924690e0a5a76f3b469f`.

| prime | nonzero / denominator | zero / denominator | recomputed residue-vector SHA-256 | frozen SHA-256 | match |
|---:|---:|---:|---|---|---|
| 1,000,003 | 2,323 / 13,419 | 11,096 / 13,419 | `eb9a0a786881a003d04de1e10edf5fc93616d39763c7baf6be76bfcf219a0bf2` | same | yes |
| 1,000,033 | 2,323 / 13,419 | 11,096 / 13,419 | `9f7a56f1aa125da35f5e6e9202658ebca5f9338d0440cc13725f3013d9cea149` | same | yes |

Final validation-report SHA-256 values: n=9
`63f3c23f0cf2371c08716d5c8aee02c9227c455f5f027b331b58dc9a088edf16`;
n=10 `fedde284731bb9a4580a5126bf09ca05a9f5fc86156dc2f2529db4c7cd6e5cec`;
n=5 literal `914552b8ee65522de08ecb150376d367227adadbfb488ac2509d2dc941857131`;
n=6 literal `37438175dd37a7f7ee50624f6f7513fb1aebf83b13034a7e4751dc1dd0682a36`;
n=7 literal `408937b05dcaf31bdf74dcf845e18da57118106d01a0b32f7bca2cf7a58d744f`.

## n=11 benchmark

Final command:

```bash
tools/colgen/target/release/max11-colgen benchmark \
  --universe artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --sample-size 1000 --seed 20260902 --threads 6 \
  --output artifacts/math/colgen-rust/n11_benchmark_1000_v3.json
```

Universe SHA-256:
`8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8`.
Benchmark-report SHA-256:
`56d5bce8255aa8ee5e3d83f127d6a6aba39ef498f476e2c3282bea73ceac74c7`.
The sample is 1,000 records drawn without replacement by SplitMix64 and then
sorted; its u64-little-endian index-vector SHA-256 is
`7fe5c07cbdb4c0487e53c33b2c9b421a19b4de133964b041893a3c9164f505c2`.

| measurement | value |
|---|---:|
| sample denominator | 1,000 records |
| wall time at 6 threads | 46.794442297 s |
| throughput | 21.3700591547 records/s |
| measured CPU-seconds/column | 0.280766653782 |
| retained hinges min / p50 / p90 / p99 / max | 1,042 / 29,308 / 53,465 / 87,920 / 103,341 |
| sampled nnz | 31,715,543 / 1,000 records |
| extrapolated complete nnz | 23,914,058,586,231 / 1,000 |
| extrapolated complete wall time at 6 threads | 35,283.80499745705 s |

The extrapolated nnz is the exact product of the sample numerator and 754,017
universe records divided by the 1,000-record sample denominator.  It is not a
completed total.

## Trial log, including aborts and superseded runs

- The first three n=5/6/7 validator launches failed with exit 127 because
  `cargo test --release` had not emitted the standalone binary.  `cargo build
  --release` fixed the launch condition; no mathematical comparison ran in
  those three attempts.
- Early compile/lint trials caught an inferred `HashMap` type, an ambiguous
  integer type, and three lint violations.  All were fixed before any final
  control artifact.
- Benchmark v1 (standard hash maps): 63.414084943 s for 1,000/1,000 records;
  benchmark v2 (Fx state map): 48.446 s for the same 1,000/1,000 records;
  benchmark v3 (Fx state and hinge maps, final): 46.794442297 s for the same
  1,000/1,000 records.  All three report the identical sampled nnz numerator
  31,715,543 and identical support quantiles.
- Pre-final n=5/6/7 and n=9/10 reports are retained as v1; final-code reruns are
  v2 and are the results cited above.
- A pre-final G-0028 replay passed 13,419/13,419 records in 677.635145422 s at
  both primes.  Because the hinge accumulator implementation then changed
  from ordered to Fx hashing, the complete control was rerun on final code;
  only the final v2 result is cited as binding.
- An exhaustive support scan was started, then explicitly redirected by
  orchestrator AmberBluff because the same 754,017-record pass belongs inside
  the downstream rank engine.  It was interrupted after 3,000/754,017 records
  at 46.533 s, with 8,910,371 nnz and 22,272 support-union directions over that
  incomplete prefix.  No final report file was written, and these prefix
  counts are not a census.

## What was not verified

- The complete 754,017-record support union and exact total nnz were not
  computed; the orchestrator moved that one-time pass into the streaming rank
  engine.  Only the named 1,000-record benchmark numerator supports the
  extrapolation.
- Loop records and the separate `5E`/`5L` carriers are not emitted by this
  loopless generator.  The API isolates the relevant matrix/base code, but a
  later extension still owes G-0040's diagonal and padding controls.
- No rational coefficient vector, exact MAX11 identity, modular span result,
  separator, or completeness bridge was produced or checked.
- The G-0028 control checks scalar prices modulo exactly 1,000,003 and
  1,000,033; matching those residues does not constitute exact-rational
  verification.

**NO-CLAIM:** This bead implements and validates column generation for named
finite loopless signed-`W` subjects.  It does not show that MAX11 is or is not
in their span, does not cover the complete loop-inclusive family or `5E/5L`,
and does not prove anything about unrestricted two-hidden-layer ReLU
representability.
