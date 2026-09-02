# RESULT — `relu-depth-frontier-research-max11-root-gmp.3`

## Outcome

Implemented `tools/streamrank/`, a streaming sparse-row-sketch modular rank
engine for saved systems and arbitrary ordered ranges of the G-0027 universe.
It generates exact integer columns in bounded batches, applies two recorded
SplitMix64 one-bucket signed sketches, reduces batches against a dense modular
echelon basis with delayed reduction and blocked OpenBLAS `dgemm`, emits ordered
pivot source indices/buckets, and emits a bucket-space left separator for
NON_MEMBER observations. It also implements saturation, rank, resident-RSS and
process-high-water-RSS gates, plus explicit 5L synthesis.

CPU implementation commits are `4b056ce`, `fdaaa01`, `667c662`, `3ab93e4`,
`e1b2248`, `e05ae76`, and `675e92b`. The CPU Stage A executable SHA-256 is
`6cb1afeb84fb6a514c34b83d9eeec52a285827bd2318d1b15cc5c77133b549a6`.
The interchange contract is `tools/streamrank/FORMAT.md`.

Final static checks on the CPU/default feature set:

```bash
cd /data/projects/relu-depth-frontier-research/tools/streamrank
cargo fmt --check
OPENBLAS_NUM_THREADS=6 cargo test --release
OPENBLAS_NUM_THREADS=6 cargo clippy --all-targets -- -D warnings
```

Result: PASS, 6/6 unit tests and 0/0 doc tests. Tests cover scalar-versus-
blocked rank, deterministic distinct sketches, exact modular separator checks,
unsafe binary64 block rejection, Barrett reduction, and the exact 5L carrier.

## Known-answer controls in both directions

The final CPU control command shape was:

```bash
OPENBLAS_NUM_THREADS=6 tools/streamrank/target/release/max11-streamrank run-saved \
  --input INPUT --n N --modulus PRIME --buckets M \
  --seeds 2026090201,2026090202 --batch-size 1024 \
  --gemm-block 8192 --rank-panel 64 --threads 6 --filter FILTER \
  --expected-source-columns DENOM --expected-rank-a R \
  --expected-rank-augmented RA --expected-verdict VERDICT --output OUTPUT
```

The n=10 MEMBER input SHA-256 is
`bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18`.
At each of primes 1,000,003 and 1,000,033, both sketches processed
12,248/12,248 columns and returned rank(A) = rank([A|b]) = 2,166, MEMBER,
unsaturated at 6,498 buckets. All four ordered pivot hashes equal
`13ef82302f2e50e9f9555cd77eab1881bd3ef87f33677badd2b9fe079e39a87d`.
Reports and SHA-256 values:

- `n10-m6498-p1000003-panel64-v6.json`:
  `f362b19fb1ba2ef2352a96c1762659f64d525d0cf10ff11a4db07e39406783ed`.
- `n10-m6498-p1000033-panel64-v6.json`:
  `8977f138d5c6a722f208d28415ba0aa21e00d831c3a9c781ce8fefd4b1976068`.

The n=9 saved-system input SHA-256 is
`729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991`.
On its union-tree filter, at each of primes 1,000,003 and 1,000,033, both
sketches processed 739/739 selected columns and returned rank(A) = 360,
rank([A|b]) = 361, NON_MEMBER, unsaturated at 1,080 buckets. All four ordered
pivot hashes equal
`3885bf4223184e19c9d6cfdc1632d24d33c47c7cbc4a859f4208257af0933cdd`.
Reports and SHA-256 values:

- `n9-trees-m1080-p1000003-panel64-v6.json`:
  `1322b9a2630b32753b3922b466868212624cb959fa630420139bdb937c750a3d`.
- `n9-trees-m1080-p1000033-panel64-v6.json`:
  `e86348675e180f9223015e3f111aa945c7d2567f3ab311e8e8e274118a183772`.

The deliberately undersized n=9 control used 128 buckets and returned
SATURATED for both sketches after 739/739 selected columns; it did not launder
equal augmented rank into MEMBER. Report `n9-trees-saturated-panel64-v6.json`
has SHA-256
`b984832d0d1b388307fab7b02d0f972389e28ff3f132f0ea1af31c018b50a457`.
The rank-abort and process-high-water-RSS controls each stopped after 1/2
requested columns and emitted `ABORTED_GATE` without a verdict. Their report
SHA-256 values are respectively
`d57d5e6249658f78a6368e33f5b182ffbd42887c6ccb9f2f8d3c727ed8aab6ca`
and `19d172d229e734d7b1ecede7e4c094fa6b8db0097dcd326c9a9d84813625b8e2`.

## FFLAS-style reducer measurements

All rates below divide the exact `gemm_scalar_products_numerator` by the
measured `gemm_seconds`. An arithmetic-op rate counts one multiply and one add
per scalar product; it is therefore exactly twice the products/s convention.

- n=10, 12,248/12,248 columns, p=1,000,003: seed 2,026,090,201 performed
  119,269,126,512 products in 6.204172649 s = 19,224,017,973 products/s
  (38,448,035,946 arithmetic ops/s). Seed 2,026,090,202 used the same product
  numerator in 6.462202233 s = 18,456,421,234 products/s
  (36,912,842,468 arithmetic ops/s). These small ranks do not fill the GEMM.
- Production-shaped n=11 slice, 5,000/5,000 columns, p=1,000,003, one
  96,000-bucket sketch: 1,410,355,968,000 products / 26.042954261 s =
  54,154,991,552 products/s (108,309,983,104 arithmetic ops/s). The run
  generated 156,574,896 exact real nonzeros / 5,000 columns, took
  460.844476989 s wall and 3,958,052 KiB high-water RSS, and returned
  rank(A)=5,000, rank([A|b])=5,001. Report SHA-256:
  `55b15ef9b0e6bf5fae005ddc222555dba87361943b20894099becfe348b96b56`.
- The 20,000/20,000 ordered sample used two 96,000-bucket sketches at
  p=1,000,003. Both returned rank(A)=16,767 and rank([A|b])=16,768. Reducer
  times were 1,148.664723615 s and 1,171.609305558 s; each used
  13,690,094,496,000 GEMM products. The corresponding measured GEMM rates were
  72,832,086,862 and 72,208,167,831 products/s. Wall time was
  3,786.939359381 s and high-water RSS 14,713,316 KiB. Report SHA-256:
  `cee792745cc0c62c8f2cffc58d477705a452f408a2970a78e0bb825ed2acae3a`.

The 20k rank curve at denominators 1,024, 5,120, 10,240, 15,360 and 20,000
was respectively 805, 3,416, 7,007, 12,127 and 16,767 for both sketches. The
sample indices were sorted into universe order, so this curve is not a random-
order estimate of complete-universe rank. Its NON_MEMBER result is only a null
for this finite 20,000-column sample.

## CPU Stage A observation and CUDA cross-check

Exact CPU command:

```bash
OPENBLAS_NUM_THREADS=6 tools/streamrank/target/release/max11-streamrank run-universe \
  --input artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --order-file artifacts/math/stream-rank-engine/stageA-order-s5-beta-le1.json \
  --n 11 --branch-edges 5 --modulus 1000003 --buckets 64000 \
  --seeds 2026090201 --batch-size 1024 --gemm-block 1024 \
  --rank-panel 64 --threads 6 --include-five-l true \
  --abort-rank-above 45000 --abort-rss-kib-above 18874368 \
  --output artifacts/math/stream-rank-engine/stageA-s5-beta-le1-plus5L-m64000-p1000003-s1.json
```

Universe SHA-256:
`8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8`.
The order file contains 120,947/120,947 distinct source indices and has
SHA-256
`42cbef6ff5ef2652995b5d3b434c4672f71e622738649613808726b0ccf36c5f`.
The explicit 5L column is the 120,948th subject column; it has eleven exact
linear coefficients 18,144,000 and zero hinges. Stage A generated
4,502,404,876 exact real nonzeros / 120,948 columns.

The one CPU sketch at p=1,000,003 and seed 2,026,090,201 returned
rank(A)=rank([A|b])=21,222, MEMBER and unsaturated at 64,000 buckets. Wall time
was 11,445.674417151 s, of which column generation was 7,630.200908279015 s
and reducer time was 2,360.2515585529995 s. High-water RSS was 7,319,616 KiB.
The reducer used 96,843,191,424,000 GEMM products / 1,448.135184860002 s =
66,874,413,685 products/s (133,748,827,370 arithmetic ops/s). Report SHA-256:
`08726b35086ed255d166a5d6ba8e68fbf80060e32ec63ebddd8d510270ec4f88`.

The CPU ordered pivot-list SHA-256 is
`2ac8d1227fb3a66e61f2292a861ec9bdb3fb132c970fcd9e1d7da4c2334b744b`.
The separately implemented CUDA path processed the identical 120,948-column
subject at the same prime/seed and produced the same rank, augmented rank,
verdict and pivot digest. Canonical serialization of the complete 21,222-
element ordered pivot arrays compared byte-for-byte with `cmp` and passed;
both canonical arrays have SHA-256
`2ed3a0e3cf1396f0cb00e70c3a40766d6fafa908f06c15f095659d175fac8ea7`.
The CUDA report is in `../cuda-reducer/` and is not counted as a second CPU
sketch or second-prime Stage A observation.

## Trials, aborts, and scope

- Early scalar, division-reduction, Barrett, first blocked, streaming and
  final-contract artifacts are retained with their versioned names. Final-code
  results above use the `panel64-v6` controls and the named Stage A artifact.
- The first n=11 prefix benchmark processed 1,000/1,000 low-mass prefix
  columns and returned rank 241, not a representative performance or rank
  sample. It was superseded by the recorded 5k and 20k ordered samples; the
  prefix artifacts remain in this directory.
- A preregistered Stage A launch at 96,000 buckets was stopped before its first
  completed batch when amendment 2 changed the frozen bucket count to 64,000
  and added explicit abort gates. It produced no decision artifact and supplies
  no rank numerator.
- Stage A stayed below both abort gates. Only one CPU sketch at one prime was
  run here; the orchestrator moved the remaining Stage A arms and full-universe
  work to bead `.12` on the rented H100.

What was not verified: this bead did not compute the full 754,017-record
universe rank, did not run both Stage A sketches at both primes on the CPU, did
not lift any modular pivot solution to rationals, and did not verify an exact
identity on real rows. The 5k and 20k NON_MEMBER observations are bounded
finite-sample nulls. The Stage A MEMBER observation is a modular sketched
observation, not an exact rational certificate.

**NO-CLAIM:** These controls and observations validate the named finite modular
stream-rank computations. They do not prove that MAX11 is or is not in the
loopless k=5 span and do not prove anything about unrestricted exact
two-hidden-layer ReLU representability.
