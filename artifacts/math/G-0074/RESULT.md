# G-0074 registered result: an exact continuum survivor

The preregistered Y-spoke family **survives every input with at most three
distinct coordinate values**.  This is an infinite-locus theorem for the
frozen family, not a global MAX11 construction.

| quantity | registered value |
|---|---:|
| frozen columns | 8,107 |
| baseline rows | 364 |
| Farey-F6 rows | 1,014 |
| combined rows | 1,378 |
| modular rank at each of three primes | 460 |
| exact selected-minor rank lower bound | 460 |
| emitted witness support | 443 |
| independently replayed midpoint rows | 936 |

The combined integer matrix has SHA-256
`2521811babdf42205cc6ba49d7315666b6e7c8414a45e3ff0949b2445774f5c0`;
the target has SHA-256
`4aed6fcf1f8a41b9e5919f418e0ad887af4516cd4056b6dbb5181c415e5af301`.
At each of `1,000,003`, `1,000,033`, and `1,000,037`, the column and
augmented ranks are both 460 with identical pivot hashes.  A selected 460 by
460 rational minor is nonsingular, and its exact FLINT solution replays with
zero stdlib-`Fraction` residual on all 1,378 original rows.  This proves rank
at least 460 over Q; the modular rank values are not asserted as an exact
characteristic-zero rank upper bound.

The basic solution has 443 nonzero terms: 442 Y-spoke orbit columns and
`C_E` with coefficient one.  Its sparse coefficient digest is
`f40be381b1ab2c8bc406c10a387719e07ebf0bafe07bffb065065048a8388d63`.
The registered producer additionally replays that same vector at one rational
midpoint in each of the twelve open intervals between consecutive Farey-F6
nodes, with exact zero residual on all 936 rows.

The registered outcome is
`artifacts/math/G-0074/farey_three_level_gate_v1.json.gz`, byte SHA-256
`5de36fa1cf39d8524577cdc681b68220c9e807670aef7b14595e8b380bcd4fcb`
and scientific-payload SHA-256
`1d56ed5afb9cf9dfcc602c43b34a215790066ebb3041087957db955a5476741c`.

## Why the finite nodes certify a continuum

After translation and positive scaling, any input with exactly three distinct
coordinate values has levels `(0,t,1)`.  On each fixed labelled assignment a
Y-spoke atom is

```text
B + 2*x_k + max(0,p,q)
```

or

```text
B + 2*x_k + max(0,p,p+q),
```

where the affine switch forms `p`, `q`, `p-q`, and `p+q` have coefficient
bound six.  Their possible roots in `[0,1]` are therefore exactly the thirteen
Farey-order-six nodes used by the gate.  Between adjacent nodes every column
and the target are affine in `t`; equality at both endpoints implies equality
throughout the interval.  The registered shift-degree and homogeneity controls
then restore arbitrary real level locations and scales.

## Independent replay

A fresh-context implementation did not import or execute the producer.  It
independently reconstructed the 252 MAX10 bases, all 18,400 labelled seeds,
and all 442 selected Y-spoke descriptors; materialized the selected columns by
a typed-forest affine dynamic program; and replayed the same rational vector.
It found zero exact residual on all 1,378 registered rows and all 936 midpoint
rows.  The standalone artifacts are:

- `artifacts/cleanroom/G-0074/replay_cleanroom.py`, SHA-256
  `29142b4d905527082efcd0f8001feeec1c93e76e2dada768ee97c7ebbcad0de3`;
- `artifacts/cleanroom/G-0074/AUDIT.md`, SHA-256
  `4baae77f8190d388c88a64f6552da544b61add9561ccc695b4d3bb0231d95706`.

The independent implementation proves the 443 support columns are independent
at three primes and that adding `C_L` raises its rank floor to 444.  It does
not reproduce the producer's 460-column minor because the sparse outcome does
not expose the seventeen zero-coefficient pivot descriptors.  No independent
rank-460 claim is made.

## Exact boundary and next discriminator

The at-most-three-valued locus is lower-dimensional inside `R^11`.  The result
does not establish equality at a genuinely four-valued point, a global CPWL
identity, a compiled two-hidden-layer network, or an unrestricted depth
theorem.  The modular rank 460 also leaves thousands of coefficient directions
unconstrained.

The next gate therefore uses only genuinely four-valued profiles.  A frozen
64/128-panel CountSketch can either produce a full 8,108-column augmented
minor—an exact Q/R obstruction for this entire family—or materially shrink the
survivor space before the complete gated-facet verifier.

