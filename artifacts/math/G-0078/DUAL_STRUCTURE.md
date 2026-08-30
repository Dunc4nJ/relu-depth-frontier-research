# G-0078 dual structure and the next construction gate

## Bottom line

The frozen G-0078 functional is an exact and useful separator, but it is not a
general four-level face-gluing obstruction.

Exactly 230 evaluation rows support the functional.  Those rows form a circuit
of the row matroid of the frozen 8,107-column Y-spoke-plus-carrier matrix: 229
of them are independent over `Q`, the last is their unique dependence, every
coefficient in that dependence is nonzero, all 8,107 construction columns are
annihilated, and the MAX11 target is not.

The decisive boundary check is also exact.  The same functional is nonzero on
the legal `P^2` blocks

```text
M3 = Sym_avg(max(x1,x2,x3))
M4 = Sym_avg(max(x1,x2,x3,x4)).
```

Their Newton polytopes are respectively
`conv([e1,e2] union {e3})` and `conv([e1,e2] union [e3,e4])`.
Thus the functional cannot be promoted to an identity that annihilates every
two-hidden-layer primitive block.  Its proven scope remains the frozen finite
dictionary.

## Exact structure of the circuit

The support consists entirely of genuinely four-valued G-0075 rows:

- 230 rows;
- 21 deterministic spacing panels, numbered 0 through 20;
- 35 of the 120 positive four-colour count profiles;
- panel support counts
  `[32,20,22,15,6,16,16,13,9,12,12,7,9,8,8,7,6,4,3,3,2]`.

Place the rational weights in a `21 x 120` panel/profile array, filling absent
entries with zero.  This array has rank 21 modulo `1,000,003`.  Because the
weight denominators are invertible at that prime, the nonzero modular minor is
also a nonzero characteristic-zero minor; hence its rank over `Q` is exactly
21.  In particular, this certificate is not a rank-one separation of a panel
functional from a profile functional.  That observation does not rule out a
different conceptual compression, but no local face identity follows from the
present coefficient pattern.

## Exact action on symmetric braid-fan functions

Let

```text
L = the frozen rational G-0078 functional,
T = L(MAX11),
Mk = Sym_avg(max(x1,...,xk)).
```

Direct exact evaluation gives

| orbit function | exact `L(Mk)/T` |
|---|---:|
| `M1` | `0` |
| `M2` | `0` |
| `M3` | `614792/533093` |
| `M4` | `646637/533093` |
| every `Mk`, `5 <= k <= 11` | `1` |

The zero values for `M1` and `M2` independently reproduce the two frozen
carrier columns.  The nonzero values for `M3` and `M4` are the exact `P^2`
falsifiers above.

There is an equivalent compact description on the sorted cone
`x_(1) <= ... <= x_(11)`.  Binomial inversion of

```text
E_k = sum_{|S|=k} max_{i in S} x_i
    = sum_{j=k}^11 binom(j-1,k-1) x_(j)
```

gives

```text
L(x_(j)) / T = v_j / 48463,

v = [0, 5150988, -8945012, 3454783,
     48463, 48463, 48463, 48463, 48463, 48463, 48463].
```

The entries sum to zero, as translation covariance requires.  This says what
the separator detects inside the symmetric braid-fan subspace.  It does not
extend its annihilation property beyond the frozen Y-spoke dictionary.

## A coherent gluing mechanism that escapes the separator

For a coordinate subset `S`, let `T_S = conv{e_i : i in S}`.  At the MAX11
facet direction `mu-e_i`, its exposed face is

```text
F_(mu-e_i)(T_S) = T_S              if i is not in S,
                  T_(S without i)  if i is in S.
```

Consequently the unnormalised orbit sums obey the Pascal restriction

```text
E_k^n  ->  E_k^(n-1) + E_(k-1)^(n-1),
```

and the averaged orbits obey

```text
M_k^n -> ((n-k)/n) M_k^(n-1) + (k/n) M_(k-1)^(n-1).
```

Triangles and tetrahedra therefore provide globally defined tied,
noncentrally symmetric blocks whose eleven facet restrictions are
automatically compatible.  This is a concrete construction mechanism aligned
with G-0064's necessary face condition.  It is not a MAX11 construction and no
novelty claim is made for the elementary face rule.

## The obvious escape columns do not close the frozen system

The executable also evaluates the three symmetrised orbit types from the
certified MAX5 construction:

```text
P = max(max(2*x5,x1+x2), max(x1,x3)+max(x1,x4))
Q = max(2*x5, max(x1+x2,x3+x4))
R = max(max(2*x5,x1+x3), max(x1+x2,x3+x4)).
```

Full symmetrisation gives the exact row identity

```text
2*M5 = 4*P + Q - 4*R.
```

Every one of `M3,M4,M5,P,Q,R` has nonzero exact price under `L`, so every one
escapes the current column span.  A separate full-16,738-row quotient
calculation gives the following result modulo the single registered prime
`1,000,003`:

| added columns | quotient rank | rank with MAX11 | modular epsilon |
|---|---:|---:|---:|
| `M3` | 1 | 2 | 1 |
| `M4` | 1 | 2 | 1 |
| `M5` | 1 | 2 | 1 |
| `P` | 1 | 2 | 1 |
| `Q` | 1 | 2 | 1 |
| `R` | 1 | 2 | 1 |
| `M3,M4` | 2 | 3 | 1 |
| `P,Q,R` | 3 | 4 | 1 |
| all six | 5 | 6 | 1 |

This table is **discovery-only finite-field evidence**.  It does not prove
that the target remains outside any candidate-augmented rational span: the
prime could be exceptional for an augmented family.  Its legitimate decision
is narrower and important—merely finding a nonzero scalar price, or killing
the current separator, is not enough.  New columns must be selected by their
independent full quotient residuals and the target-aware rank must be updated.

## Highest-leverage next discriminator

The natural next finite target is the complete loop-inclusive degree-five
pair-max graph universe, not the 11,542 natural lifts and not only the
loopless subset.  The frozen G-0038 denominator contains 7,015,841 orbit
records.  Degree five is the first pair-max mass not excluded on dimensional
grounds for MAX11 by Rueß et al., Corollary 4.3; see the certified local source
[`literature/papers/2607.21651.txt`](../../../literature/papers/2607.21651.txt).

The exact dual should be used as a column-generation oracle in this order:

1. price the complete frozen degree-five universe, using modular arithmetic
   only to shortlist and exact rational replay for any promoted price;
2. retain candidates with linearly independent full quotient residuals, not
   merely the first or numerically largest nonzero scalar;
3. augment the full target-aware system and recompute `epsilon`;
4. if a later exact dual annihilates the entire complete catalogue, state the
   resulting bounded-family theorem; otherwise iterate with the new dual.

Even an exact all-zero price census would remain a theorem about the certified
pair-max catalogue, not arbitrary real-weight `P^2` blocks or unrestricted
two-hidden-layer networks.

## Reproduction and bindings

Run the fast semantic controls:

```bash
.venv/bin/python -B artifacts/math/G-0078/analyze_dual_structure.py --self-test
```

Replay every exact and modular result and require byte identity with the
frozen JSON:

```bash
.venv/bin/python -B artifacts/math/G-0078/analyze_dual_structure.py --check-frozen
```

The full replay requires the ignored cache
`artifacts/math/G-0076/cache/full-N.npy`.  It is accepted only with shape
`16738 x 8108`, little-endian `int64` dtype, and raw C-order SHA-256
`41498698f122d01b624cf83e48f7e36c0b56082a4062654e36a55a7c34c49095`.
If absent, regenerate it with the frozen G-0076 producer.

Frozen artifact hashes:

```text
analyze_dual_structure.py
  834f0400a3edb1013bb954182b143d9ab94c6223767c55a62457ea418aea25f2
dual_structure_v1.json
  f788532082eaa27378d4d6100ac41e5eeebe1e414e110face2006d3c5045180e
scientific payload
  50a99058d5ee9d157974d3f4e073674e2fa702b1a693ab683080dae76dd00876
```

The JSON additionally binds the G-0073, G-0074, G-0075, G-0077, and G-0078
producers, the G-0075 and G-0077 outcomes, and the exact G-0078 certificate.

## Claim boundary

Exact here:

- the 230-row circuit statement;
- exact annihilation of all 8,107 frozen columns and nonzero target pairing;
- panel/profile support and rank;
- every displayed price and the order-statistic transform;
- the fact that legal `P^2` blocks `M3` and `M4` falsify universal
  annihilation.

Not established here:

- an unrestricted MAX11 representation or impossibility theorem;
- a general face-gluing theorem;
- rational nonmembership after adding `M3,M4,M5,P,Q,R`;
- completeness of any finite atom catalogue for arbitrary two-hidden-layer
  networks;
- novelty or priority.
