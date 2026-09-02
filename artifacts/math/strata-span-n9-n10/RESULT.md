# gmp.7 — natural W-strata spans at n=9 and n=10

## Outcome

Mass rules must be expressed relative to branch degree `k`.  In the quotient by
the cancelled signed graph `W=B-A`, the smallest rule in the finite relative
grid that reaches the full saved-system rank **and** contains the target at both
of 2/2 primes is

```text
k-s <= 1  AND  maximum multiplicity <= 1.
```

Because every nonzero W in the saved simple-pair systems already has maximum
multiplicity one, this predicate selects the same 6,175/6,197 n=9 and
7,181/7,203 n=10 W-orbits as `k-s<=1`.  Its ranks and augmented ranks are
1,506/1,506 at n=9 and 2,166/2,166 at n=10 at each prime.  At n=11 the relative
predicate selects 243,155/754,017 records (32.2479%, a 3.10x column-count
reduction).  The multiplicity cap is uncalibrated rather than validated at low
arity: the saved systems contain 0/6,197 and 0/7,203 multi-edge W-orbits.

There is therefore **no 5–10x relative full-span family in the tested grid**.
The interesting 5–10x target-aware family is `s=k AND beta<=1`: it has
120,946/754,017 n=11 records (a 6.23x reduction) and is a modular MEMBER at both
low arities, but it does not carry their full spans.  At n=9 it has
3,496/6,197 columns and rank=augmented rank 1,152/1,506; at n=10 it has
4,484/7,203 columns and rank=augmented rank 1,807/2,166.  Thus it is a plausible
cheap target probe, not a full-span known-answer check.

The requested boundary cases are:

- `s=k` is modular MEMBER but full-rank-minus-one at both arities:
  5,894/6,197 columns and rank=augmented rank 1,505/1,506 at n=9;
  6,892/7,203 columns and 2,165/2,166 at n=10.  Its relative n=11 size is
  735,732/754,017.
- Within `s=k`, `beta<=2` is also MEMBER but not full: 5,442/6,197 columns and
  rank=augmented rank 1,446/1,506 at n=9; 6,440/7,203 columns and
  2,106/2,166 at n=10.  Its n=11 size is 355,166/754,017.
- `max_multiplicity=1` reaches full rank at both low arities: 6,196/6,197
  W-orbits at n=9 and 7,202/7,203 at n=10.  It has 243,467/754,017 n=11
  records (32.2893%, a 3.10x reduction).
- `components=1` does **not** span everything: its rank is 978/1,506 at n=9
  and 978/2,166 at n=10.  It is a modular MEMBER at n=9 (augmented rank
  978/1,506) but a modular NON-MEMBER at n=10 (augmented rank 979/2,166).
  The n=11 connected stratum has 485,632/754,017 records.

The earlier literal rule `s in {3,4}` has 18,254/754,017 n=11 records, but it is
**not transferable**: at `k=4` it means `k-s<=1`, which becomes `s in {4,5}` and
753,444/754,017 records at `k=5`.  Literal counts are retained in the JSON only
as descriptive census slices, not as the recommended experiment.

All ranks and memberships in this report are finite-field statements at
`p=1,000,003` and `p=1,000,033`.  I did not compute an exact-Q rank or recover an
exact rational identity for any stratum.

## Degree-relative rule table

`r/R` and `a/R` are rank and augmented rank over the full-rank denominator.
Every entry agrees at 2/2 primes.  This table includes the requested full-mass
beta ladder and the smallest full-rank relative candidates.

| relative predicate | n=9 count / 6,197 | n=9 r/R; a/R | n=10 count / 7,203 | n=10 r/R; a/R | n=11 count / 754,017 |
|---|---:|---:|---:|---:|---:|
| `s=k, beta<=0` | 739 | 360/1,506; 361/1,506 | 1,387 | 808/2,166; 809/2,166 | 12,459 |
| `s=k, beta<=1` | 3,496 | 1,152/1,506; 1,152/1,506 | 4,484 | 1,807/2,166; 1,807/2,166 | 120,946 |
| `s=k, beta<=2` | 5,442 | 1,446/1,506; 1,446/1,506 | 6,440 | 2,106/2,166; 2,106/2,166 | 355,166 |
| `s=k, beta<=3` | 5,874 | 1,502/1,506; 1,502/1,506 | 6,872 | 2,162/2,166; 2,162/2,166 | 584,034 |
| `s=k, beta<=4` | 5,894 | 1,505/1,506; 1,505/1,506 | 6,892 | 2,165/2,166; 2,165/2,166 | 701,382 |
| `s=k` | 5,894 | 1,505/1,506; 1,505/1,506 | 6,892 | 2,165/2,166; 2,165/2,166 | 735,732 |
| `k-s<=1, beta<=3` | 6,155 | 1,503/1,506; 1,503/1,506 | 7,161 | 2,163/2,166; 2,163/2,166 | 600,796 |
| `k-s<=1, beta<=4` | 6,175 | 1,506/1,506; 1,506/1,506 | 7,181 | 2,166/2,166; 2,166/2,166 | 719,001 |
| `k-s<=1, components<=4` | 6,175 | 1,506/1,506; 1,506/1,506 | 7,181 | 2,166/2,166; 2,166/2,166 | 753,354 |
| `k-s<=1` | 6,175 | 1,506/1,506; 1,506/1,506 | 7,181 | 2,166/2,166; 2,166/2,166 | 753,444 |
| `k-s<=1, max multiplicity<=1` | 6,175 | 1,506/1,506; 1,506/1,506 | 7,181 | 2,166/2,166; 2,166/2,166 | 243,155 |
| `max multiplicity=1` | 6,196 | 1,506/1,506; 1,506/1,506 | 7,202 | 2,166/2,166; 2,166/2,166 | 243,467 |
| `components=1` | 4,389 | 978/1,506; 978/1,506 | 4,389 | 978/2,166; 979/2,166 | 485,632 |

The finite relative grid comprises standalone thresholds in `k-s`, beta,
components and maximum multiplicity, plus intersections of the `k-s=0` and
`k-s<=1` families with each topology/multiplicity threshold.  “Smallest” above
means smallest n=11 census count within these 43/43 predicates, not among all
possible graph-defined subfamilies.

## Quotient and census

The saved n=9 file contains 10,976/10,976 raw simple-pair templates and collapses
to 6,197 distinct W-orbits; 4,779/4,779 collapsed duplicates were compared as
complete sparse integer columns and were exactly equal.  The n=10 file contains
12,248/12,248 raw templates and collapses to 7,203 W-orbits; 5,045/5,045 collapsed
duplicates passed the same exact comparison.  Sparse-map equality covers every
stored hinge and linear row; absent sparse keys are zero on both sides.

The stratum counts are:

| invariant | n=9 counts / 6,197 W | n=10 counts / 7,203 W | n=11 counts / 754,017 W |
|---|---:|---:|---:|
| `s` | 0:1, 1:2, 2:19, 3:281, 4:5,894 | 0:1, 1:2, 2:19, 3:289, 4:6,892 | 0:1, 1:2, 2:28, 3:542, 4:17,712, 5:735,732 |
| `beta` | 0:879, 1:2,887, 2:1,977, 3:434, 4:20 | 0:1,535, 1:3,227, 2:1,987, 3:434, 4:20 | 0:14,303, 1:114,069, 2:240,674, 3:232,320, 4:118,208, 5:30,617, 6:3,646, 7:176, 8:4 |
| components | 0:1, 1:4,389, 2:1,675, 3:129, 4:3 | 0:1, 1:4,389, 2:2,323, 3:469, 4:21 | 0:1, 1:485,632, 2:219,265, 3:45,335, 4:3,691, 5:93 |
| max multiplicity | 0:1, 1:6,196 | 0:1, 1:7,202 | 0:1, 1:243,467, 2:436,335, 3:67,265, 4:6,457, 5:492 |

Each row above sums to its named family denominator.  The n=11 counts were
recomputed record-by-record from the frozen G-0027 file, including independent
recomputation of `s`, `beta`, component count, active vertices, and maximum edge
multiplicity.

## Cumulative unions, smallest strata first

The tables below give the requested size-ordered cumulative unions.  `r/R` is
candidate rank over the named full-rank denominator; `a/R` is augmented rank over
the same denominator.  Every entry was identical at 2/2 primes.  `M` means
`r=a` modulo both primes.

### n=9 (full-rank denominator R=1,506; family denominator 6,197 W-orbits)

| invariant | added value | added count / 6,197 | cumulative allowed values | cumulative count / 6,197 | r/R | a/R | MAX |
|---|---:|---:|---|---:|---:|---:|:---:|
| s | 0 | 1 | {0} | 1 | 1/1,506 | 2/1,506 | N |
| s | 1 | 2 | {0,1} | 3 | 3/1,506 | 4/1,506 | N |
| s | 2 | 19 | {0,1,2} | 22 | 16/1,506 | 17/1,506 | N |
| s | 3 | 281 | {0,1,2,3} | 303 | 163/1,506 | 164/1,506 | N |
| s | 4 | 5,894 | {0,1,2,3,4} | 6,197 | 1,506/1,506 | 1,506/1,506 | M |
| beta | 4 | 20 | {4} | 20 | 14/1,506 | 15/1,506 | N |
| beta | 3 | 434 | {3,4} | 454 | 130/1,506 | 131/1,506 | N |
| beta | 0 | 879 | {0,3,4} | 1,333 | 523/1,506 | 523/1,506 | M |
| beta | 2 | 1,977 | {0,2,3,4} | 3,310 | 903/1,506 | 903/1,506 | M |
| beta | 1 | 2,887 | {0,1,2,3,4} | 6,197 | 1,506/1,506 | 1,506/1,506 | M |
| components | 0 | 1 | {0} | 1 | 1/1,506 | 2/1,506 | N |
| components | 4 | 3 | {0,4} | 4 | 4/1,506 | 5/1,506 | N |
| components | 3 | 129 | {0,3,4} | 133 | 93/1,506 | 94/1,506 | N |
| components | 2 | 1,675 | {0,2,3,4} | 1,808 | 818/1,506 | 819/1,506 | N |
| components | 1 | 4,389 | {0,1,2,3,4} | 6,197 | 1,506/1,506 | 1,506/1,506 | M |
| multiplicity | 0 | 1 | {0} | 1 | 1/1,506 | 2/1,506 | N |
| multiplicity | 1 | 6,196 | {0,1} | 6,197 | 1,506/1,506 | 1,506/1,506 | M |

### n=10 (full-rank denominator R=2,166; family denominator 7,203 W-orbits)

| invariant | added value | added count / 7,203 | cumulative allowed values | cumulative count / 7,203 | r/R | a/R | MAX |
|---|---:|---:|---|---:|---:|---:|:---:|
| s | 0 | 1 | {0} | 1 | 1/2,166 | 2/2,166 | N |
| s | 1 | 2 | {0,1} | 3 | 3/2,166 | 4/2,166 | N |
| s | 2 | 19 | {0,1,2} | 22 | 16/2,166 | 17/2,166 | N |
| s | 3 | 289 | {0,1,2,3} | 311 | 171/2,166 | 172/2,166 | N |
| s | 4 | 6,892 | {0,1,2,3,4} | 7,203 | 2,166/2,166 | 2,166/2,166 | M |
| beta | 4 | 20 | {4} | 20 | 14/2,166 | 15/2,166 | N |
| beta | 3 | 434 | {3,4} | 454 | 130/2,166 | 131/2,166 | N |
| beta | 0 | 1,535 | {0,3,4} | 1,989 | 974/2,166 | 975/2,166 | N |
| beta | 2 | 1,987 | {0,2,3,4} | 3,976 | 1,363/2,166 | 1,364/2,166 | N |
| beta | 1 | 3,227 | {0,1,2,3,4} | 7,203 | 2,166/2,166 | 2,166/2,166 | M |
| components | 0 | 1 | {0} | 1 | 1/2,166 | 2/2,166 | N |
| components | 4 | 21 | {0,4} | 22 | 21/2,166 | 22/2,166 | N |
| components | 3 | 469 | {0,3,4} | 491 | 327/2,166 | 328/2,166 | N |
| components | 2 | 2,323 | {0,2,3,4} | 2,814 | 1,478/2,166 | 1,478/2,166 | M |
| components | 1 | 4,389 | {0,1,2,3,4} | 7,203 | 2,166/2,166 | 2,166/2,166 | M |
| multiplicity | 0 | 1 | {0} | 1 | 1/2,166 | 2/2,166 | N |
| multiplicity | 1 | 7,202 | {0,1} | 7,203 | 2,166/2,166 | 2,166/2,166 | M |

The JSON also contains the low-to-high and high-to-low cumulative tables,
all atomic strata, their exact modular target-membership tests, and literal n=11
counts for every predicate.  The smallest-strata-first order is not monotone in
the numeric invariant; rank growth is therefore conditional on the displayed
order.

## Rank-growth extrapolation

For a degree-relative, order-conditional heuristic, fix `s=k` and add beta
strata in the order `0,1,...`.  For beta value `b`, the empirical growth rate is

```text
(delta_rank_n9(b) + delta_rank_n10(b))
------------------------------------------------
(added_columns_n9(b) + added_columns_n10(b)).
```

The denominator is therefore the pooled number of added W-orbits at the two
known arities.  The predicted n=11 increment is this rate times the n=11 stratum
count, rounded to the nearest integer.

| beta added within `s=k` | n=9 added columns / 6,197; rank growth / 1,506 | n=10 added columns / 7,203; rank growth / 2,166 | pooled growth numerator / column denominator | n=11 `s=5` stratum / 735,732 | rounded predicted increment |
|---:|---:|---:|---:|---:|---:|
| 0 | 739; 360 | 1,387; 808 | 1,168/2,126 | 12,459 | 6,845 |
| 1 | 2,757; 792 | 3,097; 999 | 1,791/5,854 | 108,487 | 33,191 |
| 2 | 1,946; 294 | 1,956; 299 | 593/3,902 | 234,220 | 35,595 |
| 3 | 432; 56 | 432; 56 | 112/864 | 228,868 | 29,668 |
| 4 | 20; 3 | 20; 3 | 6/40 | 117,348 | 17,602 |
| 5 | no observation | no observation | no numerator/denominator | 30,528 | not predicted |
| 6 | no observation | no observation | no numerator/denominator | 3,642 | not predicted |
| 7 | no observation | no observation | no numerator/denominator | 176 | not predicted |
| 8 | no observation | no observation | no numerator/denominator | 4 | not predicted |

The n=9 growth column sums to 1,505/1,506 and the n=10 column sums to
2,165/2,166, matching the observed `s=k` ranks.  This extrapolation is neither a
rank bound nor a probability model.  It has no denominator for beta 5–8 because
those strata have 0/0 low-arity observations.  The JSON also retains analogous
descriptive low-to-high calculations for the unconditioned invariants; those
literal mass calculations are not degree-transfer rules.

## Known-answer and negative controls

- Positive full-family gates, passed at 2/2 primes: n=9 rank=augmented rank
  1,506/1,506 on 6,197/6,197 W-orbits; n=10 rank=augmented rank 2,166/2,166
  on 7,203/7,203 W-orbits.
- Negative tree gate, passed at 2/2 primes: the 739/6,197 n=9 full-support
  balanced tree W-orbits have rank 360 and augmented rank 361 (denominator:
  739 tree columns; ambient full-rank denominator: 1,506), hence NON-MEMBER.
- Partition consistency: the W records were a disjoint exhaustive partition for
  each of 4/4 invariants.  A deliberately duplicated record placed in a false
  bucket was rejected for each of 4/4 invariants.
- Collapse consistency: 4,779/4,779 n=9 and 5,045/5,045 n=10 same-W duplicate
  templates had byte-identical canonical sparse integer columns.
- The audit reran both W quotients and the 754,017/754,017-record G-0027 census,
  rechecked table telescoping, and required agreement across 2/2 primes.  It
  passed.  It did not replay modular elimination; the full producer command is
  the rank replay.

## Exact commands and resource envelope

From repository root:

```bash
source .venv/bin/activate
OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=6 \
  /usr/bin/time -v python artifacts/math/strata-span-n9-n10/strata_span.py \
  --threads 6 2>&1 | tee artifacts/math/strata-span-n9-n10/run.log

# The steering correction added degree-relative census/growth views without
# rerunning the already-frozen modular eliminations:
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python artifacts/math/strata-span-n9-n10/strata_span.py \
  --threads 1 --postprocess-existing \
  2>&1 | tee artifacts/math/strata-span-n9-n10/postprocess.log

OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /usr/bin/time -v python artifacts/math/strata-span-n9-n10/verify_outputs.py \
  2>&1 | tee artifacts/math/strata-span-n9-n10/verify.log
```

The corrected outcome run used 6/6 permitted FLINT threads, 18m34.40s wall time,
and 2,232,288 KiB maximum RSS (2,232,288/16,777,216 KiB bead memory allowance).
The final audit used 1 thread, 2m12.19s wall time, and 1,295,296 KiB maximum RSS.
Toolchain: Python 3.13.7, python-flint 0.9.0 over FLINT 3.6.0, pynauty 2.8.8.1.

## Input and output hashes

Inputs:

```text
729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991  handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz
bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18  handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz
8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8  artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz
```

Outcome artifact hashes are frozen in `MANIFEST.sha256`, generated after this
report.  The input receipts above are also embedded in the JSON and rechecked by
the verifier.

## No-claim boundary

This is a bounded two-prime computation on n=9 and n=10 saved simple-pair
systems plus a combinatorial recount of n=11 strata.  It does **not** compute a
single n=11 column, does **not** test any n=11 rank or target membership, does
**not** prove that the n<=10 spanning behavior persists, does **not** establish
an exact rational identity, and does **not** imply an unrestricted depth lower
bound.  In particular, neither the 243,155/754,017 relative full-span candidate
nor the 120,946/754,017 target-aware candidate has a computed n=11 column, rank,
or MAX11 membership result.
