# G-0050 exact-Q bridge adversarial audit

## Hard verdict

**PASS** for the frozen bounded claim.

The integer hinge matrix for the 3,310 frozen signed-mass-`1..3` orbit
records has exact characteristic-zero ranks

```text
rank(proper 3,307 columns) = 488
rank(proper columns + three full-core seeds) = 491.
```

Consequently the three seed cosets are independent modulo the proper-core
span.  Every hinge-free combination of these columns has zero aggregate
coefficient on each seed coset, hence zero eleventh binary finite difference;
it cannot equal a nonzero normalization of `MAX11`.

This is a bounded no-go theorem, not a MAX11 solution or an unrestricted
network lower bound.

## Independent replay

The audit script does not call `exact_q_bridge.run`.  It independently:

1. regenerates the 10,065 primitive degree-three directions using a
   stars-and-bars construction;
2. regenerates every one of the 3,310 columns and fails immediately if any
   emitted hinge is absent from that universe;
3. reconstructs the modular solve-row pivots with a separate NumPy Gaussian
   elimination routine;
4. solves and replays all 3,307 proper columns exactly over `Q` on all 10,065
   rows; and
5. reconstructs the three exact seed residuals and their rational witness
   minor.

Observed controls:

| item | independently observed |
|---|---:|
| frozen records | 3,310 |
| proper-core records | 3,307 |
| full-core seeds | 3 |
| complete primitive hinge rows | 10,065 |
| hinges outside row universe | 0 |
| exact proper basis size | 488 |
| exact proper columns replayed | 3,307 / 3,307 |
| exact rows checked per column | 10,065 |
| seed quotient rank | 3 |
| seed residual nonzero counts | 660, 1,320, 660 |
| witness determinant | `-12230590464` |

The independently rebuilt matrix SHA-256 is
`6c20fc728582ea454f8741eae1b1e81b4f4625d606c7a6b267a9ed7f22fa41ea`,
exactly matching the producer report.  The independently rebuilt proper
coordinate digest is
`3be09668f1eb895bfbf16ec9c32cd9e9f89e45d484e31cec64d1c0da1a41a58f`.
Its maximum numerator/denominator bit lengths are `9` and `6`, with `10,071`
nonunit-denominator entries, also exactly matching.

## Required audit questions

### Pivot extraction and bindings — PASS

- The 488 basis-column indices equal the first-prime discovery record exactly.
- The 489 discovery pivot rows address the same seed-first row ordering: its
  hash is `174f16165606b4fcc61df57ccf3f1ff404873e1b844e3c7aab1c1cfdd91206c2`.
- Independent elimination of the transposed `489 x 488` candidate selects the
  same 488 solve rows as the report.
- The resulting integer minor has rank 488 modulo both `1,000,003` and
  `1,000,033`.  One nonzero modular determinant already implies its integer
  determinant is nonzero, so the exact-Q lower-rank certificate does not rely
  solely on the producer's 4,088-bit determinant computation.
- The report's canonical payload digest and every pinned producer-input digest
  verify.

### Exact proper-span replay — PASS

For each proper column `p_j`, the audit solves the fixed square system

```text
B_solve q_j = (p_j)_solve
```

over `Q`, then checks `B q_j = p_j` on every one of the 10,065 rows.  All
3,307 identities pass exactly.  The invertible basis minor gives
`rank_Q(P) >= 488`; the full replays give `rank_Q(P) <= 488`; therefore the
rank is exactly 488.

### Seed quotient logic — PASS

For each seed `s_i`, let

```text
r_i = s_i - B B_solve^(-1) (s_i)_solve.
```

Each residual vanishes on the 488 solve rows.  A vector in the proper span
that vanishes there must be zero because `B_solve` is invertible.  Thus linear
independence of the residuals is exactly independence of the seed cosets
modulo the proper span—not merely a rank heuristic.

At rows `1276`, `5872`, and `6241`, the independently reconstructed residual
minor is

```text
[-384,   -768,   -768]
[   0,   2304,      0]
[-36864, -52992, -59904]
```

with determinant `-12230590464 != 0`.  Hence the exact seed quotient rank is
three and the full rank is `488 + 3 = 491`.

### Row-universe completeness — PASS for this census

The production worker uses a permissive dictionary lookup and would silently
drop an unexpected hinge.  That is a genuine hardening weakness.  The audit
closes the current false-pass route by independently constructing the full
degree-three universe and requiring membership for every hinge emitted by
every record.  No direction was omitted.

Why degree three suffices: a signed-mass-`s <= 3` rank word is the difference
of two weak compositions of `s`.  Adding the same weak composition of
`3-s` to both sides represents the same difference at degree three; primitive
normalization does not change this coverage.

### Normalization and bounded conclusion — PASS

The exact invariant census is

```text
proper columns:  Delta^11 = 0            (3,307 records)
seed columns:    Delta^11 = 239500800     (3 records)
```

Here `239500800 = 6 * 11!` is nonzero.  Common loop/nonloop padding contributes
only proper subset-max bases and has invariant zero.  `MAX11` itself has
eleventh binary finite difference `1` (or `11!` under the matrix target
normalization), also nonzero.  Therefore there is no missing scalar-factor
or target-normalization escape.

The rank argument is stated over `Q`, but because the matrix is integral its
rank and seed-coset independence are the same over every characteristic-zero
field.  Thus the same bounded no-go also excludes **real output coefficients
on these fixed 3,310 columns**.  It does not extend to arbitrary real inner
weights or atoms outside the frozen combinatorial family.

## Exact scope and remaining assumptions

The result covers exactly the hash-bound 3,310 G-0038 records, signed mass at
most three, full coordinate symmetrization, unit combinatorial edge-max atoms,
and the complete 10,065-row primitive hinge semantics generated for those
records.

It does not cover signed mass at least four, a different orbit enumeration,
continuous/arbitrary inner weights, nonsymmetric constructions, or arbitrary
two-hidden-layer networks.  Exhaustiveness of the upstream G-0038 orbit stream
as a classification is an upstream assumption; this audit verifies every
record in the frozen stream but does not independently re-enumerate graph
isomorphism classes from scratch.

The producer also checks input hashes only before the long computation, not
again afterward.  That is a time-of-check/time-of-use hardening gap, but it
does not affect this frozen report: the post hoc independent replay pins the
current inputs and reproduces every semantic and algebraic digest.

## Reproduction

```bash
.venv/bin/python -B artifacts/cleanroom/G-0050-exact-q-audit/independent_exact_audit.py
```

Pinned producer script SHA-256:
`b82fbb6df487b0e76a4bbefc695960b9f1a87ef25a9e8e33b26f07d02433f27b`.

Pinned producer report SHA-256:
`64d49d39595842187d90caf114d7940f830cb5287e518adbb52110a983dce73b`.
