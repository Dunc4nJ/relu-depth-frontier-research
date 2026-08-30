# G-0099 — leaf/bridge incidence compression

## Outcome

The faithful lower-dimensional potency gate **passes exactly**.

For `n=6 -> 7`, let `T` range over balanced two-coloured spanning-tree
orbits on seven vertices and let `F` range over balanced two-coloured
two-component spanning-forest orbits on six vertices.  For a tree `T`, define

```text
r(T,F) = number of (leaf, opposite-colour edge) deletions producing F,
D(F,T) = 7 r(T,F).
```

There are exactly 53 tree orbits and 11 forest orbits.  The complete
loop-inclusive degree-three Rueß dictionary has 3,010 compressed columns.  The
joint system consisting of 630 primitive-hinge rows, 7 linear rows, and 11
incidence rows is `648 x 3010`, has rank 327, and has an exact rational
solution of support 113.  That solution represents `MAX7` globally in the
ascending-chamber normal form and satisfies

```text
D(tree coefficients) = published MAX6 dominant-c2 coefficients.
```

Every one of the 648 rows was replayed in `Fraction` arithmetic.  The
independent verifier instead literally enumerates all `7!` orders for each of
the 113 exported support atoms.

This positive result genuinely needs columns outside the public MAX7
certificate plus tree block: that restricted `305 x 110` system has ranks
87/88 after target augmentation modulo 1,000,003.  This is only a **modular
negative for that restricted subset**, not a rational or complete-family
obstruction.

## Exact combinatorics

If `a_T,a_F` are the stabilizers under vertex relabelling allowing one global
colour swap, and `N_T=7!/a_T`, `N_F=6!/a_F`, a separately enumerated reverse
extension count `q(F,T)` satisfies, entry by entry,

```text
N_T r(T,F) = 7 N_F q(F,T),
a_F r(T,F) = a_T q(F,T).
```

Regrouping the full permutation sums
`F_T=sum_{sigma in S7} Phi_{sigma T}` after all deletion events gives the Rueß
basis coefficient `D(F,T)=7r(T,F)`.  Incrementing one incidence entry by one
breaks the independently enumerated weighted identity and is rejected.

The published MAX7 certificate itself contains exactly zero balanced
full-active tree terms, while the published MAX6 certificate contains three
nonzero dominant-c2 forest terms (`1/360`, `-1/1440`, `-1/360`).  Therefore the
published coefficient vectors do **not** transfer.  Certificate nonuniqueness
matters: the complete constrained solve above finds a different MAX7
coefficient vector that does transfer.

## Scale-up to `n=10 -> 11`

The same purely combinatorial map was built from all 12,459 balanced
bicoloured spanning-tree orbits on eleven vertices.  Their deletions cover
exactly 1,387 balanced full-active c2 forest orbits on ten vertices.  The
sparse incidence has 171,131 nonzeros among 17,280,633 possible entries
(density about 0.9903%).  Independent reverse extensions have the same support
and pass all 171,131 stabilizer-weighted identities.

The `1387 x 12459` matrix `D=11r` has full row rank modulo 1,000,003.  The
selected integer minor is therefore nonsingular over `Q`, an **exact**
characteristic-zero conclusion.  In particular, the 252-term dominant-c2
projection of the public exact MAX10 certificate has a rational tree-vector
preimage.

This surjectivity is important but weak: **at the forest-coefficient level the
incidence constraint is vacuous.**  It does not say that any such preimage has
the right degree-five semantics.  No eleven-variable semantic column is built
by the scale-up producer.

## What is and is not established

| Layer | Result | Claim class |
|---|---|---|
| `n=6 -> 7` orbit/stabilizer/direct-reverse incidence | all exhaustive checks pass | exact positive |
| Published MAX7 tree coefficients transferred to published MAX6 c2 vector | zero maps to a nonzero vector | exact negative, certificate-specific |
| Restricted public-MAX7-atoms + all-tree semantic system | rank 87, augmented rank 88 mod 1,000,003 | modular negative, subset only |
| Complete degree-three semantic + incidence system | 113-term solution, all 648 rows replay | exact positive |
| `n=10 -> 11` combinatorial `D` | full row rank 1,387; MAX10 c2 target is in its image | exact positive, but vacuous as a constraint |
| Joint complete degree-five semantic + `D` system at `n=11` | not run here | no claim |
| Global-wall validity / exact MAX11 identity | not established | no claim |
| Unrestricted two-hidden-layer MAX11 representation or lower bound | not established | no claim |

The next decisive test is therefore a **joint semantic-plus-incidence solve**
on a faithful complete-row/CEGIS system.  A direct `D` preimage failing the
semantic rows would be informative but would not obstruct other preimages;
the full joint affine fibre is the relevant object.

## Relation to the complete degree-five universe

The G-0038 loop-inclusive degree-five stream contains exactly 7,015,841 signed
`W=B-A` orbit records, including 384,425 active-11 records.  The balanced
spanning-tree stratum has 12,459 orbits.  The next active-11,
`components=2,beta=1` stratum has exactly 93,827 orbits:

```text
44,231 loopless + 28,112 positive-loop + 21,484 negative-loop = 93,827.
```

The leaf/bridge construction is not the old STAR extension: the new leaf edge
is incident to vertex 11, while the opposite-colour bridge joins the two old
components entirely among old vertices.  It is also not the G-0073/G-0079
Y-spoke family, whose atoms are non-graphical flattened ternary maxima.

## Artifacts and reproduction

```bash
# Complete lower potency gate
nice -n 10 .venv/bin/python artifacts/math/G-0099/leaf_bridge_n6_n7.py \
  --complete --output artifacts/math/G-0099/leaf_bridge_complete_v1.json

# Restricted diagnostic (modular negative only)
nice -n 10 .venv/bin/python artifacts/math/G-0099/leaf_bridge_n6_n7.py \
  --output artifacts/math/G-0099/leaf_bridge_subset_v1.json

# Purely combinatorial n10 -> n11 scale-up
nice -n 10 .venv/bin/python artifacts/math/G-0099/leaf_bridge_n10_n11.py \
  --output artifacts/math/G-0099/leaf_bridge_n10_n11_v1.json

# Independent literal-permutation / FLINT-minor verifier
nice -n 10 .venv/bin/python artifacts/math/G-0099/verify_leaf_bridge.py \
  --output artifacts/math/G-0099/independent_verification_v1.json
```

`leaf_bridge_complete_v1.json` exports the full direct/reverse lower matrices,
the seven-term exact `D` preimage, and the 113-term joint semantic solution
with ready-to-use Rueß full-permutation-sum coefficients.

`leaf_bridge_n10_n11_v1.json` exports both sparse orientations (`r` by tree
columns and `q` by forest rows), stabilizers, labelled orbit sizes, and the
selected modular-minor witness.  `MANIFEST.json` binds final byte hashes after
all producers and the independent verifier have stopped.
