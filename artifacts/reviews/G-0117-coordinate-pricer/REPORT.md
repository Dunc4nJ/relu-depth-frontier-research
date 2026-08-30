MATERIAL_INCREMENT

# G-0117 coordinate-pricer clean-room review

## Verdict

Bounded PASS for the subset-coordinate recurrence, the enriched three-state
linear recurrence, and the current post-fix public implementation at
`src/lib.rs` SHA-256
`84b37ea50f012bfe8310de84b1ca27a7c1b77de90978635dd483798759d4c6aa`.

The clean-room checker found one exact bug in the initially inspected public
implementation: `scale * coordinate` was evaluated in `i8`.  The author fixed
it during review by promoting both sides of the comparison to `i16`; the
hostile replay now returns the mathematically required zero.  This was an
implementation counterexample, not a counterexample to the DP formula.

This is not a family-wide price replay, a MAX11 result, a T2 review, or a
campaign-level promotion.

## Independent derivation

Let `A` be the `k` active vertices and

```text
q(v,S) = W[v,v] + sum_(u in S) W[v,u]
```

for an unplaced active vertex `v` and the set `S` of active vertices already
placed.  For target word `t=s d`, let `C(r,S)` count active-rank injections
matching `t_0,...,t_(r-1)`.  The exact transitions are

```text
C(r+1,S)       += C(r,S)  if t_r=0 and r-|S| < 11-k,
C(r+1,S union {v}) += C(r,S)  if v notin S and q(v,S)=t_r.
```

Thus `C(11,A)` counts injections with indistinguishable inactive vertices.
Every injection lifts to exactly `(11-k)!` permutations of the labelled
inactive vertices.  Since `w=s d` has primitive scale `gcd(w)=|s|`,

```text
h_d(W) = (11-k)! sum_(s=-5,s!=0)^5 |s| C_s(11,A).
```

The fixed range is complete here: the input census has signed mass at most
five, so every raw increment is in `[-5,5]` and any nonzero primitive scale is
at most five.  Parallel edges are accumulated in `W`; they do not change the
recurrence.

For a primitive first-positive zero-sum `d`, write
`P_j=sum_(i=0)^j d_i`.  On the ordered cone,

```text
d.x = -sum_(j=0)^9 P_j (x_(j+1)-x_j).
```

The first nonzero `P_j` is positive.  Therefore `rho(d.x)` is genuinely
nonlinear on the cone exactly when some proper prefix sum is negative.  If no
prefix is negative, `d.x <= 0` throughout the cone and the hinge must be
omitted.

For orientation, a first-negative raw word has `w=-g d`, hence

```text
rho(w.x) = g rho(d.x) + w.x.
```

The entire raw word, with its original negative orientation, is the linear
correction.  A first-positive word contributes no correction.

## Three-state linear DP

The sign state is `0/+/-`, recording the sign of the first nonzero increment.
A correct implementation needs more than the three path counts.  One valid
form carries, for every `(rank,S,sign)`, both the prefix count and the sum of
the accepted prefix-coordinate vectors.  On a transition with increment `q`
at rank `r`, carry the old vector sum and add `count*q*e_r` exactly when the
new sign is negative.  Multiply the final negative-state vector by `(11-k)!`.

The current Rust implementation uses the equivalent suffix-weight form.  For
an active transition to `S'` at rank `r`, it weights `q` by

```text
(10-r)! / (10-r-(k-|S'|))!,
```

the exact number of completions of the remaining active-rank injection, and
then restores `(11-k)!` labelled-inactive permutations at the end.  Inactive
transitions have increment zero.  This is algebraically identical to carrying
the vector payload.

A bare count-only three-state implementation that adds `q` at transition time
without either payload propagation or suffix weighting is wrong: it omits the
multiplicity of future completions.

## Literal evidence

`checker.py` visited all `11! = 39,916,800` labelled permutations once in
factoradic order.  The G-0113 input was bound at SHA-256
`093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8`.

- Active-3 sequences `5341`, `152715`, and `160213` matched the full linear
  correction.  Their raw directions are chamber-inactive; explicit nonzero
  raw coordinates (`1,451,520` or `2,903,040`) were correctly filtered to
  zero hinge coefficients.
- Active-4 multiedge sequence `73165` had 120 active hinge directions.  Every
  literal coefficient matched the subset DP, and the full linear vector
  matched the three-state DP.
- Literal signatures occurred exactly `8!` times for active three and `7!`
  times for active four, directly testing the inactive factorial.
- Active-11 cyclic sequence `3` had identity raw word
  `(0,-1,-1,-1,-1,1,1,2,0,1,-1)`.  For
  `d=(0,1,1,1,1,-1,-1,-2,0,-1,1)`, literal enumeration found exactly 128
  occurrences at signed scale `-1` and none at the other nine scales, giving
  `h_d(W)=128`, exactly matching the subset DP.
- Its literal and three-state orientation corrections both equalled
  `(0,-3628800,-5564160,-4878720,-2324160,240960,1724928,2780256,3390976,3862576,4396144)`.
- The active outside-support direction
  `(0,1,-6,5,0,0,0,0,0,0,0)` priced to exact zero.
- Branch swap and vertex relabelling preserved every checked hinge and linear
  vector.
- Two distinct loopless common paddings for sequence `5341`, including one
  using a residual-inactive vertex, both gave the literal orbit value
  `1,721,986,560`, equal to the normal form.  Omitting the orientation
  correction failed this control.
- A valid sign-swap mutant of active-11 sequence `3` changed the supported
  coordinate from `128` to `32` and changed the linear correction.
- The complete G-0113 census contained 163,740 loopless records, 52,483 with a
  multiedge in at least one sign branch, and no opposite-sign edge left
  uncancelled.

Full machine-readable values are in `results.json`.

## Exact implementation counterexample and post-fix replay

The initially inspected implementation formed the target coordinate as an
`i8` product.  The direction

```text
d = (0,1,-26,25,0,0,0,0,0,0,0)
```

is primitive, first-positive, zero-sum, and active (proper prefixes include
`1` and `-25`), so validation accepted it.  At scale `-5`, the old code
evaluated `(-5_i8)*(-26_i8)=130`, which panicked in debug and wrapped in
release.  Mathematically its coefficient is zero because no raw increment can
have magnitude 26.

The corrected kernel evaluates the product in `i16`.  `overflow_panel.json`
and `overflow_query.json` replay this case against a one-record copy of the
real sequence-5341 signed graph.  `overflow_output.json` binds the corrected
kernel hash and reports zero nonzero coefficients and maximum coefficient
zero.  An independent post-fix `cargo test --lib` run passed all four tests,
including the hostile-direction regression.

## Residual doubts

- The checker validates the formula and selected real records; it does not
  price every direction of every record.
- The current implementation was inspected only after the independent
  recurrence and literal results were fixed.
- Correctness still depends on retaining the suffix-completion weight (or an
  equivalent vector payload) and the final inactive factorial in future
  rewrites.

## Reproduction

```text
python3 -u artifacts/reviews/G-0117-coordinate-pricer/checker.py \
  --batch-size 500000 \
  --result artifacts/reviews/G-0117-coordinate-pricer/results.replay.json
```

Checker SHA-256:
`a20d99c617b8f5f57fc14a4cfe114933f1da0c693a1c35ae987100dc73086502`.
Result SHA-256:
`5ed2d7cdfe677cd1144d62b56fea132741cb192eb8cd059c3a3946f7e75e378a`.
