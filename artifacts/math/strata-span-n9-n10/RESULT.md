# gmp.7 — natural W-strata spans at n=9 and n=10

## Outcome

In the quotient by the cancelled signed graph `W=B-A`, the smallest tested
natural rule that reaches the full saved-system rank at **both of 2/2 primes**
is

```text
s in {3,4}.
```

It has 6,175/6,197 W-orbits at n=9 and rank 1,506/1,506 at each prime.  It has
7,181/7,203 W-orbits at n=10 and rank 2,166/2,166 at each prime.  Its augmented
ranks are also 1,506/1,506 and 2,166/2,166, respectively, so it contains the
MAX target modulo each of the 2/2 primes.

The literal same n=11 rule has 18,254/754,017 records (2.4209% of the census,
a 41.31x column-count reduction).  This is a bounded low-arity signal, not an
n=11 rank result.  There is an important translation caveat: `s in {3,4}` at
degree four is the top-two-mass rule, while the top-two-mass rule at degree five
would be `s in {4,5}`, containing 753,444/754,017 records.  The latter was not
tested at n=9 or n=10 because `s=5` is absent there.  Thus the cheap 18,254-column
literal experiment deliberately omits the dominant n=11 `s=5` stratum.

Two other degree-stable readings are less aggressive:

- `max_multiplicity=1` reaches full rank at both low arities: 6,196/6,197 W-orbits
  at n=9 and 7,202/7,203 at n=10.  It has 243,467/754,017 n=11 records (32.2893%,
  a 3.10x reduction).
- `components=1` does **not** span everything: its rank is 978/1,506 at n=9 and
  978/2,166 at n=10.  It is a modular MEMBER at n=9 (augmented rank 978/1,506)
  but a modular NON-MEMBER at n=10 (augmented rank 979/2,166).  The literal n=11
  connected stratum has 485,632/754,017 records (64.4060%, a 1.55x reduction).

The largest mass stratum alone is one dimension short of the full span but
already contains the target at both arities: `s=4` has rank=augmented rank
1,505/1,506 on 5,894/6,197 n=9 W-orbits and 2,165/2,166 on 6,892/7,203 n=10
W-orbits.  Adding `s=3` contributes exactly 1/1 missing rank dimension at each
arity.

All ranks and memberships in this report are finite-field statements at
`p=1,000,003` and `p=1,000,033`.  I did not compute an exact-Q rank or recover an
exact rational identity for any stratum.

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

For a transparent, order-conditional heuristic, the output uses the
**low-to-high** order.  For invariant value `v`, its empirical growth rate is

```text
(delta_rank_n9(v) + delta_rank_n10(v))
------------------------------------------------
(added_columns_n9(v) + added_columns_n10(v)).
```

The denominator is therefore the pooled number of added W-orbits at the two
known arities.  The predicted n=11 increment is this rate times the n=11 stratum
count, rounded to the nearest integer.  For cancelled mass the data are:

| s | pooled rank-growth numerator / pooled-column denominator | n=11 stratum count / 754,017 | rounded predicted increment |
|---:|---:|---:|---:|
| 0 | 2/2 | 1/754,017 | 1 |
| 1 | 4/4 | 2/754,017 | 2 |
| 2 | 26/38 | 28/754,017 | 19 |
| 3 | 302/570 | 542/754,017 | 287 |
| 4 | 3,338/12,786 | 17,712/754,017 | 4,624 |
| 5 | no low-arity numerator/denominator | 735,732/754,017 | not predicted |

This extrapolation is neither a rank bound nor a probability model.  It cannot
predict the dominant `s=5` increment because the denominator has 0/0 observations
there.  The JSON gives the same explicitly-denominated calculation for beta,
components, and maximum multiplicity.

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

OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /usr/bin/time -v python artifacts/math/strata-span-n9-n10/verify_outputs.py \
  2>&1 | tee artifacts/math/strata-span-n9-n10/verify.log
```

The outcome run used 6/6 permitted FLINT threads, 16m23.30s wall time, and
2,256,108 KiB maximum RSS (2,256,108/16,777,216 KiB bead memory allowance).
The audit used 1 thread, 2m01.35s wall time, and 1,290,444 KiB maximum RSS.
Toolchain: Python 3.13.7, python-flint 0.9.0 over FLINT 3.6.0, pynauty 2.8.8.1.

## Input and output hashes

Inputs:

```text
729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991  handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz
bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18  handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz
8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8  artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz
```

Outcome artifacts before this RESULT/manifest was added:

```text
86dd3103140e132dd90eb7728cded72541ff00ec847ba470c62494dccb3a1fbb  strata_span.py
d68d8a9488fcd63652c3ebda4d87a1635210e36dedf0769877630806e3811a26  verify_outputs.py
08bee21c50297d91ed8d9f3e931ef502618e7c7ba21a2eaaa313705ec5a5d1b6  strata_span_results.json
29a0fb281caaffd495126b57de9ed0eb86695b56f7da0c40ba9e12cf1bb35950  verification.json
d8bd907803c16b33950cf229411ae2af44d23855ad939a57983fc482e4c6052b  run.log
035fbbb4b2bb4ad019e2536dea983ed5857a6360f2e1b501deb7ea2522b05976  verify.log
```

## No-claim boundary

This is a bounded two-prime computation on n=9 and n=10 saved simple-pair
systems plus a combinatorial recount of n=11 strata.  It does **not** compute a
single n=11 column, does **not** test any n=11 rank or target membership, does
**not** prove that the n<=10 spanning behavior persists, does **not** establish
an exact rational identity, and does **not** imply an unrestricted depth lower
bound.  In particular, the literal 18,254/754,017 n=11 candidate is only a first
experiment whose modular rank and MAX11 membership remain open.
