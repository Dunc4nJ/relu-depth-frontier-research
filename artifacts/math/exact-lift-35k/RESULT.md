# RESULT — bounded-memory exact lift at r≈35,000

Bead: `relu-depth-frontier-research-max11-root-gmp.10`
Agent: `AzureAspen`
Date: 2026-09-02

## Outcome

`lift-large` is implemented as a Python exact-column consumer plus a Rust
bounded-memory solver. The Rust path performs one panel-pivoted dense modular
LU in `u32` storage, sparse-CSC Dixon residual steps, periodic rational
reconstruction with exact early termination, and a one-factor-at-a-time
multi-prime CRT fallback. A separate arbitrary-precision reconstruction mode
handles separators whose rational coefficients are not small.

The required non-block-diagonal dense r=20,000 control passed. Its 20,000 by
20,000 modular minor was genuinely factored; the complete exact CSC had
600,000,000/600,000,000 structural entries across 30,000 union rows. The
500/20,000 planted rational solution was recovered after 4 p-adic digits and
verified on 30,000/30,000 rows. Peak RSS was 4,000,036 KiB and LU time was
586.143479937 seconds.

The n=10 known answer passed through the new path and emitted the byte-identical
upstream certificate SHA-256
`4bcb155a416188d479f20a2009f077003e828f1f09d65476117523a3bb6644e9`.
The forced CRT fallback independently emitted the same certificate. The exact
separator path reproduced the `.8` n=9 bucket separator exactly and checked
739/739 tree columns.

## Implementation and exact modular arithmetic

- `tools/exactlift/lift_large.py` consumes the shared
  `max11-streamrank-pivots-v1` source indices and saved-system or exact
  arbitrary-index `MCOLGEN1` columns. It writes a transient `ELIFTQ01` CSC
  problem, invokes Rust, emits a sparse witness, and calls the independent
  all-row Python verifier.
- `tools/exactlift/lift_large_rs` stores exactly one dense modular factor in a
  row-major `u32` array. Global panel row pivoting makes echelon-ordered but
  invertible minors usable. Independent row/column permutations are exact
  preconditioning and source indices undo the column order in the certificate.
- Block updates use OpenBLAS `dgemm`, but this is not floating discovery. With
  prime 65,521 and block inner dimension 128, every accumulated nonnegative
  product is at most 549,487,411,200, below the exact binary64 integer limit
  4,503,599,627,370,496. Every block result is rounded to that already-exact
  integer and reduced modulo the named prime.
- Dixon keeps the exact CSC resident. Each iteration solves one modular RHS,
  computes the integer residual by CSC matvec, divides only after checking
  rowwise divisibility by the prime, and tries vector rational reconstruction.
  A candidate is accepted only after an exact check on every union row.
- If early Dixon is insufficient, the original factor is freed. CRT materializes
  and frees one named prime factor at a time. `solve-big` uses arbitrary-size
  integers for residues/reconstruction/final verification while retaining the
  same bounded modular factor and integer residual path.

The solver also implements and unit-tests the transpose modular solve used by
the dual leg. `large_separator.py` forms the exact left-separator equations,
solves them through `solve-big`, composes the bucket vector with the signed
one-bucket sketch, and invokes the independent exact all-column verifier.

## Inputs and hashes

- n=10 system: SHA-256
  `bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18`;
  12,248/12,248 source columns.
- n=10 `.8` pivot report: SHA-256
  `fdba23baaa66ac08c84a96a2a7026b8ad5be30f8654e842d395940b1ad5a99de`;
  rank 2,166 over 12,248 source columns.
- Hash-bound n=10 upstream verification report: SHA-256
  `31de498d2435f1676b1855b94c2ae26059026fe1e3950678a7396d656a86ef70`;
  pinned verifier SHA-256
  `d6da3030b719735b10a197dc79d7e311ecc90f70314ed748de81087f94f039a7`.
- n=9 system: SHA-256
  `729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991`.
- n=9 tree pivot report at prime 1,000,003: SHA-256
  `f611558ade3ef2fabe5f5e637104cbc90b306f838169271fe2f526ca0941b7f5`;
  739/739 tree columns, ranks 360/361.
- Dense r=20,000 report: SHA-256
  `e6348b9fe6b0d87c0349bad64964a1f47e2c52fd98906de47664157a381baa94`.

The transient n=10 `ELIFTQ01` problem was 71,898,340 bytes, contained
8,965,154 CSC nonzeros, and had SHA-256
`9a66d3fdffc5c8782b8a2a675a4de2e5b394025d773e1c12a688c49b13fc5849`.
It was not committed because it exceeds 50 MB; it is deterministically
regenerated from the named pivot report, selected-row artifact, and system.

Implementation SHA-256 values are:

- `lift_large.py`: `d7ca52f3f7814abbc1cd9483398a2ec243c25352e6c8009036c2284f6c272577`.
- `large_separator.py`: `90c80dc601ee6010d093232da74a9053a255967c7562051a3458159b47695777`.
- Rust `Cargo.toml` / `Cargo.lock`: `f87f0b69a25911775175e7608e21aaba211f17e0ff25169b1f6fd4c45588eebc` /
  `5e1f5f5a137cf646bd6ed5560f515d776b743ddbb1f647cffa981e26fe4111b0`.
- Rust `src/{big,crt,main,modular,problem,rational,synthetic}.rs`, in that
  order: `b8f2e1c7a2ef02941bad4d24bf39e7487829bf559bcfecadd8c6c458aa3aa053`,
  `251e5ba9977f0e5b0fa03ffc760c93ac8f606290b0f6465c6628214db4bf052b`,
  `0f60a915a697222a297e05a91d86ecbdb91a3a4ead0fee7f5fa417beeeb58fd5`,
  `f4bde64d89f0eb62f805d749d8b663e09ba39a97839814461c7e9b56355eba76`,
  `d1925ed1469c8b87a4fb8b9a60d977ed33df0a8a2b12b7bad5d18c9bb51b30ef`,
  `3b7a24c9c5eec48504cb2d2a9e49fbf4927a462ebcfc724cb07b659d977ddbe5`,
  and `53fc8de0256efeb5cb1494cd598fefd0615362460cab96f65efd77710d9031a9`.

## Exact commands

All commands used at most 6 threads.

```bash
source .venv/bin/activate
cargo build --release --manifest-path tools/exactlift/lift_large_rs/Cargo.toml

python tools/exactlift/lift_large.py \
  --pivot-report artifacts/math/exact-leg-at-scale/n10-sketch-m6498-p1000003.json \
  --sketch-index 0 \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --selected-rows artifacts/math/exact-lift-35k/n10_selected_rows.json \
  --binary tools/exactlift/lift_large_rs/target/release/max11-lift-large \
  --prime 65521 --lu-block 128 --row-tile 256 --threads 6 \
  --max-steps 6 --reconstruct-every 1 --candidate-support-limit 1000 \
  --precondition-seed 20260902 \
  --output artifacts/math/exact-lift-35k/n10_large_witness.json \
  --report artifacts/math/exact-lift-35k/n10_large_report.json \
  --upstream-output artifacts/math/exact-lift-35k/n10_large_upstream.json \
  --expected-upstream-sha256 4bcb155a416188d479f20a2009f077003e828f1f09d65476117523a3bb6644e9

# Force the CRT fallback by allowing only one insufficient Dixon digit.
python tools/exactlift/lift_large.py \
  --pivot-report artifacts/math/exact-leg-at-scale/n10-sketch-m6498-p1000003.json \
  --sketch-index 0 \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --selected-rows artifacts/math/exact-lift-35k/n10_selected_rows.json \
  --binary tools/exactlift/lift_large_rs/target/release/max11-lift-large \
  --prime 65521 --lu-block 128 --row-tile 256 --threads 6 \
  --max-steps 1 --reconstruct-every 1 --candidate-support-limit 1000 \
  --precondition-seed 20260902 \
  --crt-primes 65519,65497,65479,65449,65447,65437 \
  --output artifacts/math/exact-lift-35k/n10_crt_fallback_witness.json \
  --report artifacts/math/exact-lift-35k/n10_crt_fallback_report.json \
  --upstream-output artifacts/math/exact-lift-35k/n10_crt_fallback_upstream.json \
  --expected-upstream-sha256 4bcb155a416188d479f20a2009f077003e828f1f09d65476117523a3bb6644e9

tools/exactlift/lift_large_rs/target/release/max11-lift-large synthetic \
  --rank 20000 --union-rows 30000 --support 500 \
  --denominator-block 25 --prime 65521 --lu-block 128 --row-tile 256 \
  --threads 6 --seed 20260902 --max-steps 6 --reconstruct-every 1 \
  --output artifacts/math/exact-lift-35k/synthetic_dense_r20000.json

python tools/exactlift/large_separator.py \
  --pivot-report artifacts/math/stream-rank-engine/n9-trees-p1000003-barrett-v2.json \
  --sketch-index 0 \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --binary tools/exactlift/lift_large_rs/target/release/max11-lift-large \
  --threads 6 \
  --output artifacts/math/exact-lift-35k/n9_large_separator.json \
  --report artifacts/math/exact-lift-35k/n9_large_separator_report.json

python tools/exactlift/sketch_separator.py mutate \
  --separator artifacts/math/exact-lift-35k/n9_large_separator.json --delta 1 \
  --output artifacts/math/exact-lift-35k/n9_large_separator_mutated_plus1.json
python tools/exactlift/sketch_separator.py verify \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --separator artifacts/math/exact-lift-35k/n9_large_separator_mutated_plus1.json \
  --output artifacts/math/exact-lift-35k/n9_large_separator_mutated_verify.json

cargo test --release --manifest-path tools/exactlift/lift_large_rs/Cargo.toml
python -m unittest discover -s tools/exactlift -p 'test_*.py' -v
python -m py_compile tools/exactlift/lift_large.py tools/exactlift/large_separator.py
git diff --check
./skill-runtime verify-quick
```

## n=10 known answer: direct Dixon

The input minor had 2,166/2,166 selected rows and 8,965,154 CSC nonzeros over
16,719 union rows. At prime 65,521, panel-pivoted LU took
3.364000313 seconds and the Rust child peaked at 117,104 KiB. The four modular
solve times were 0.005046742, 0.007307029, 0.00617371, and 0.006789456
seconds; the four complete CSC residual matvec times were 0.028705784,
0.009340193, 0.011702309, and 0.009033762 seconds.

Reconstruction counts were 2,012/2,166 coordinates after digit 1,
2,033/2,166 after digit 2, 2,083/2,166 after digit 3, and 2,166/2,166 after
digit 4. The digit-4 candidate had support 424/2,166 and denominator LCM
304,819,200. It passed 16,709/16,709 hinge rows and 10/10 linear rows. A
`+1/1` mutation at its first nonzero coordinate failed 1,336/16,719 union
rows inside the Rust exact checker.

The upstream output has the required SHA-256
`4bcb155a416188d479f20a2009f077003e828f1f09d65476117523a3bb6644e9`.
The byte-identity/hash-bound upstream binding is PASS; binding artifact
SHA-256 is
`fcc1a33a89a09a722821b8c1543e04964e4ae78f304fe1233e534c511d71870b`.

## Forced multi-prime CRT fallback

With Dixon capped at 1/1 digit, reconstruction was deliberately insufficient.
The fallback then factored primes 65,519, 65,497, 65,479, and 65,449, one at a
time. Their factor times were 3.096985037, 3.485924932, 3.507501487, and
3.275709868 seconds. After 4/4 CRT primes the reconstruction again had
2,166/2,166 coordinates, support 424/2,166, LCM 304,819,200, and passed
16,719/16,719 union rows. Its upstream certificate is byte-identical to the
known certificate. The binding report SHA-256 is
`da1c10da304272c22be9be9c314e5a270dc1836f48d72bc8908a4c00bda4193c`.

## Dense r=20,000 control

The control constructs `A=L*B` without exposing that factorization to the
solver. `L` is a deterministic dense 30,000 by 20,000 random integer mixer;
`B` is invertible with small bidiagonal denominator blocks on the 500 planted
coordinates. Thus the visible 20,000 by 20,000 minor and the extra 10,000
verification rows are non-block-diagonal and dense. Every exact entry is in
`[-900,900]`.

- Structural CSC entries: 600,000,000/600,000,000, exactly 30,000 structural
  row entries per column. Actual nonzeros: 599,015,388/600,000,000.
- Dense modular storage: 1,600,000,000 bytes. Packed synthetic CSC storage:
  2,400,160,008 bytes. No second modular matrix was resident.
- Planted/recovered support: 500/20,000. Planted/recovered denominator LCM:
  33,554,432. Exact verification: 30,000/30,000 rows, PASS.
- Reconstruction terminated after 4/4 p-adic digits. The modular solve times
  were 1.657752408, 0.237023869, 0.244951981, and 0.234722434 seconds. The CSC
  residual matvec times were 0.191066564, 0.0418428, 0.05801579, and
  0.046031423 seconds.
- LU time: 586.143479937 seconds, comprising 171.866768813 seconds of panel
  pivot/diagonal inverse, 12.098277926 seconds of lower block solves, and
  402.174762224 seconds of Schur updates. Total time: 591.423927363 seconds.
- Peak RSS: 4,000,036 KiB = 3.8147315979003906 GiB, below both the temporary
  12 GiB concurrency cap and the 40 GiB box denominator.
- The exact `+1/1` mutation failed 29,938/30,000 checked rows.

## r=35,000 and r=60,000 projections

These are projections from the single measured r=20,000 denominator, not
measurements. Panel/diagonal and lower-solve time are scaled quadratically;
Schur time is scaled cubically. CSC scan time is scaled linearly at the n=11
planning denominator of 31,700 structural nonzeros per column.

| rank denominator | projected LU time | projected warm modular solve | projected warm CSC matvec |
|---:|---:|---:|---:|
| 35,000 | 2,718.798321932438 s = 0.7552217560923439 h | 0.73162949825 s | 0.08510250758333333 s |
| 60,000 | 12,514.404000699 s = 3.4762233335275 h | 2.150094852 s | 0.14589001299999999 s |

Memory uses one `u32` dense factor plus the CSC. The conservative production
projection charges 8 bytes per CSC nonzero (`u32` row plus `i32` value) and
the measured 95,876,856-byte non-matrix overhead:

| rank denominator | dense u32 factor | production CSC at 31,700 nnz/column | projected peak | fits 40 GiB? |
|---:|---:|---:|---:|:---:|
| 35,000 | 4.563480615615845 GiB | 8.266419172286987 GiB | 12.91919206827879 GiB | yes |
| 60,000 | 13.41104507446289 GiB | 14.171004295349121 GiB | 27.67134165018797 GiB | yes |

The packed `u16`/`i16` representation used by the synthetic control would
project to 8.785982482135296 GiB and 20.58583950251341 GiB respectively, but
the conservative table is the planning result. The r=35,000 projection fits
40 GiB but is slightly above the temporary 12 GiB cap used while WildWillow's
pilot was resident. The measured r=20,000 run itself respected that cap.

## Exact separator control

The n=9 beta-zero tree separator square had 361/361 equations and 86,765 CSC
nonzeros. Its modular LU took 0.058588341 seconds. Because the exact solution
has numerator bit length up to 705 and denominator bit length up to 691, small
reconstruction correctly did not succeed; arbitrary-precision reconstruction
terminated after 89 p-adic digits. The recovered denominator LCM is exactly
the `.8` value
97364603919803580258999820726850424198374075481730015590022192032000190525263857818256419814883341618118281361505947077011539873831487543592990587085504321910697890637689380372169009647347232743227946520019600.

All 361/361 bucket weights, all composed linear weights, all composed hinge
weights, and the LCM are exactly equal to the `.8` separator. Independent
rational replay annihilated 739/739 tree columns and paired with the target as
1/1. The composed `+1/1` mutation annihilated 0/739 columns and therefore
failed. This is a bounded null for that finite family only.

## Controls and validation

- Rust: 4/4 unit tests pass, covering normal and transpose solves, forced
  global panel pivoting, rational reconstruction, and CRT combination.
- Python: 7/7 existing exactlift controls pass in both directions.
- Direct Dixon n=10, forced CRT n=10, r=20,000 dense synthetic, and n=9 exact
  separator are real end-to-end known-answer controls; none is a mocked solver.
- `./skill-runtime verify-quick` completed with only the campaign's known
  pre-existing SE-10 finding on G-0015; this bead did not edit that object.
- No committed file exceeds 50 MB. The 71,898,340-byte transient n=10 CSC is
  hash-recorded above rather than committed.

## No claim

No n=11 pivot set, minor, witness, or separator was processed in this bead.
The r=20,000 matrix is synthetic, although dense and non-block-diagonal. The
r=35,000 and r=60,000 figures are model-based projections, not runs. The n=10
result is a known-answer positive and the n=9 tree separator is only a finite
739-column bounded null. Nothing here establishes membership or nonmembership
of MAX11. An actual n=11 run still must gather the exact pivot columns, supply
or select an independent real-row minor, execute this solver, and verify every
row/column required by its branch.
