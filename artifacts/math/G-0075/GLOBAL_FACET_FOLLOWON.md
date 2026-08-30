# Positive-path follow-on: canonical gated facets without a terabyte matrix

This is the frozen design target if the four-level gate remains deficient.  It
records two independent planning results: the mathematically sound coordinate
system and a bounded performance benchmark.  It is not a preregistered outcome
and asserts no MAX11 identity.

## Canonical complete coordinates on the ordered cone

On `x_1 < ... < x_11`, each permutation summand is

```text
L(x) + max_{u in U} u*x,
```

with `U={0,p,q}` or `U={0,p,p+q}`.  Here `p=A-B` and
`q=x_l+x_11-2*x_k`.

For each summand:

1. Deduplicate the three branch gradients.
2. If their affine hull is collinear, discard every middle gradient and keep
   only the two extremes.  In particular, `p=q`, `q=2p`, and `q=-p` are one
   dimensional hinges with different curvature magnitudes; emitting three raw
   facets would be wrong.
3. For a genuine triangle, each hull edge `{a,b}`, with third vertex `c`, has
   support `d=b-a` and is active on the half of `d*x=0` where
   `(c-a)*x <= 0`.  Its integer curvature magnitude is the gcd of the entries
   of `d`.

Normalize a nonzero support `d` to a primitive vector with first nonzero entry
positive.  In ordered-gap coordinates `z_i=x_{i+1}-x_i>0`, write

```text
D_i = -sum_{r<=i} d_r.
```

The support meets the cone interior exactly when `min(D)<0<max(D)`.

For a gate covector `g`, define `G` by the same prefix rule.  On the compact
section

```text
z >= 0, sum(z)=1, D*z=0,
```

the extrema of `G*z` occur at

```text
G_i                                      when D_i=0,
(D_j*G_i-D_i*G_j)/(D_j-D_i)             when D_i<0<D_j.
```

These exact rational values classify the gate as full, empty almost
everywhere, or genuinely cutting.  For a cutting gate, the projective
Pluecker vector `D wedge G` identifies its boundary inside the support.
Canonical orientation matters: reversing it replaces a halfspace indicator by
its complement, so the coordinate rewrite is

```text
1_{-g <= 0} = 1 - 1_{g <= 0}.
```

The complete curvature coordinates are therefore a full-density coordinate
for each support and oriented projective gate-boundary coordinates beneath
that support.  Raw syntactic `(support,gate)` keys are not sound.

Distinct cutting indicators under one support are linearly independent: cross
one boundary at a generic point avoiding every other boundary.  Generic points
on distinct supports separate the supports.  After all curvature cancels, the
difference is affine on the connected ordered cone.  Eleven gradient
coordinates at

```text
x_* = (1,13,13^2,...,13^10)
```

determine that affine gradient.  Candidate branch-difference coefficients are
bounded by six, so the superincreasing point lies on no candidate wall;
positive homogeneity removes the remaining constant.

Thus the unsketched canonical curvature coordinates plus eleven gradients are
equivalent to global equality on the ordered cone, and symmetry transports the
result globally.

## Exact sorted-merge joint-state DP

For a low-to-high label order `v_0,...,v_10`, let `s_uv=+1` for a left edge,
`-1` for a right edge, and zero otherwise.  The emitted rank word is

```text
p_i = sum_{j<i} s_{v_i,v_j},
q(v) = -2 at the anchor, +1 at the auxiliary and new labels, 0 otherwise.
```

For every label subset `T`, store sorted unique packed words and their
multiplicities.  Build the state for `T` by a k-way merge of the streams for
`T\{v}`, appending the constant suffix emitted by final label `v` and summing
equal words.  The final label partitions permutations uniquely, so this is an
exact, hash-free recurrence.

A collision-free 59-bit word uses:

- 44 bits for eleven `p_i+4` nibbles (`p_i` lies in `[-4,4]`);
- 4 bits for the anchor position plus one;
- 11 bits for the two leaf positions.

Counts fit `uint32` because they are at most `11! = 39,916,800`.

The 8,104 representatives form exactly 4,052 pairs differing only by outer
orientation.  Their raw joint census is identical.  Enumerate once per pair;
map it to `(p,q)` for orientation zero and `(p,p+q)` for orientation one.  The
two orientations share their `p=0` facet, so five distinct facet geometries
replace six per paired word.

## Bounded benchmark and remaining wall

On 128 deterministic topology-by-orientation-stratified representatives, the
C++20 sorted-vector kernel had:

| measure | median | p95 | maximum |
|---|---:|---:|---:|
| final joint words | 1,004,291 | 1,787,781 | 2,642,900 |
| peak merge entries | 2,783,870 | 4,056,446 | 5,782,479 |
| kernel time | 0.293 s | 0.562 s | 0.685 s |

Eight workers achieved 93.1% efficiency on that sample.  Naive extrapolation
to all columns is about 5.7 wall minutes, or about 2.9 minutes after exact
orientation pairing.  These are bounded-sample projections, not certified
universe maxima.

The joint DP is no longer the bottleneck.  A typical 1,011,570-word column
produced 3,034,710 facet occurrences and 3,011,686 distinct complete
`(primitive support, oriented Pluecker gate)` keys.  A hard sampled column
produced 7,646,419 distinct keys.  Materializing all keys would approach
terabyte scale.

The implementable path is therefore:

1. enumerate once per orientation pair with sorted merge;
2. canonicalize each facet immediately, including complement rewrites and
   collinear collapse;
3. stream it directly into a preregistered signed integer CountSketch;
4. retain the eleven gradient coordinates exactly;
5. never retain the global key-by-column incidence matrix;
6. treat sketch deficiency as inconclusive;
7. promote only a full augmented-rank integer minor or an exact rational dual
   replayed against every streamed column and the target.

If both direction-level and full gated sketches survive, brute-force
materialization is the wrong escalation.  The remaining routes are a symbolic
quotient of the gate complex or row-on-demand exact CEGIS.
