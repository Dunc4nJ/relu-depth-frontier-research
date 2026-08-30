# G-0080 — exact decision of the surviving three-wall `J_2` arrangement

## Bottom line

The last unresolved arrangement in the bounded G-0035 wall library is not a
`P^2` subdivision.  In fact, every one of its eight full-dimensional cells
is outside `P^2`.

This replaces the old scan of 184 rational type-cone ratios by an exact
symbolic decision over each complete projective type cone.  It closes this
one wall triple; it is not a no-go theorem for `J_2`, arbitrary three-wall
arrangements, `W_2`, virtual `S_2`, or unrestricted `MAX11`.

The walls, in vertex order

```text
(T0,T1,T2,S00,S10,S01,S11),
```

are

```text
(-1,-1, 1 ; -1, 1, 1, 3),
(-1,-1, 1 ;  3, 1, 1,-1),
(-1, 1,-1 ;  1,-1, 3, 1).
```

## The forest-level reduction

For a cell `P`, a Minkowski summand assigns a nonnegative scalar to every
edge of `P`.  The scaled edge vectors close around every polygonal two-face.
Conversely, the two-face boundaries generate the graph cycle space of a
polytope, so such a scaling integrates to the vertex map of a weak Minkowski
summand.  Quotienting translations gives the complete nonnegative
edge-scaling/type cone.

For each of the eight cells, exact rational elimination gives

```text
K(P) = cone(R0,R1),
P     = alpha0 R0 + alpha1 R1,  alpha0,alpha1 > 0.
```

Thus every nonpoint primitive block in any `P^2` expression lies either on
one endpoint ray or at a unique positive projective ratio in the interior.
There is no unsearched real-ratio tail.

The endpoint and interior classification is:

| Chamber | Cell vertices | Ray 0 | Ray 1 | Positive interior |
|---|---:|---|---|---|
| `(-,+,-)` | 12 | cover-`UNSAT` | cover-`UNSAT` | cover-`UNSAT` |
| `(+,-,-)` | 12 | cover-`UNSAT` | cover-`UNSAT` | cover-`UNSAT` |
| `(+,+,-)` | 13 | genuine segment block | cover-`UNSAT` | cover-`UNSAT` |
| `(-,+,+)` | 14 | cover-`UNSAT` | cover-`UNSAT` | cover-`UNSAT` |
| `(+,+,+)` | 14 | genuine `conv(point union segment)` triangle block | cover-`UNSAT` | cover-`UNSAT` |
| `(+,-,+)` | 14 | cover-`UNSAT` | cover-`UNSAT` | cover-`UNSAT` |
| `(-,-,-)` | 15 | cover-`UNSAT` | cover-`UNSAT` | cover-`UNSAT` |
| `(-,-,+)` | 15 | cover-`UNSAT` | cover-`UNSAT` | cover-`UNSAT` |

The segment and triangle endpoint rays have actual zonotope certificates,
not merely a relaxed `SAT` verdict.  Positive homotheties give every
nonzero point on those rays.

## Why the two-center query is enough for a negative decision

The query is a necessary relaxation, not an equivalence.

If

```text
Q = conv(Z0 union Z1)
```

with zonotopes `Zi`, every extreme vertex `v` of `Q` belongs to at least one
`Zi`.  If its assigned zonotope has center `ci`, central symmetry and
containment give

```text
2 ci - v in Zi subset Q.
```

So a genuine primitive block always induces a coloring of all extreme
vertices by two centers satisfying exact reflection-membership inequalities.
`UNSAT` therefore excludes every genuine primitive block.  The converse is
not used and is not claimed: a `SAT` cover could fail to extend to actual
zonotopes.

On a positive type-cone support, the normal fan is the coefficient-independent
common refinement of the ray normal fans.  Facet normals are therefore fixed
and their support numbers are rational linear functions of the projective
parameter `theta>0`.  One exact Z3 `QF_LIRA` query per cell covers the entire
open projective interval.  Exact facet enumeration verifies the inherited
H-representation, and active-normal rank five verifies every imposed image
is genuinely extreme.

Finally, type-cone coordinates add under Minkowski sum.  The target has a
positive coefficient on an obstructed ray.  Some primitive block in a
putative `P^2` sum would have to carry that coefficient.  It would lie on
the obstructed endpoint or in the positive interior, both `UNSAT`.  This
contradiction applies separately to every cell.

`THEOREM.md` freezes the quantified statement and proof.

## Controls and replay

The subject runner includes both-direction controls:

- the exact zonotope predicate accepts the square, cube, and four-cube and
  rejects the octahedron;
- a square is one-center `SAT`;
- a triangle is one-center `UNSAT` with an exact proof object, but two-center
  `SAT` and has the explicit `point + segment` primitive certificate;
- every target interior becomes `SAT` when allowed one point-center per
  extreme vertex;
- every target support face is independently re-faceted, every inherited
  exact facet is present, and every retained image has active-normal rank
  five;
- a planted interior barycenter has deficient active-normal rank.

Run:

```bash
.venv/bin/python -B artifacts/math/G-0080/decide_three_wall_j2.py --self-test

.venv/bin/python -B artifacts/math/G-0080/decide_three_wall_j2.py \
  --output artifacts/math/G-0080/three_wall_j2_symbolic_decision_v1.json \
  --proof-output artifacts/math/G-0080/three_wall_j2_z3_proofs_v1.json.gz
```

The runner refuses changed G-0035 dependency bytes before import and checks
them again after the computation.  The gzip proof bundle contains the exact
Z3 proof text for all 22 `UNSAT` queries; the report binds every proof by
SHA-256.

## Frozen hashes

Filled from the final self-replayed artifacts:

```text
decide_three_wall_j2.py                  7520cab379c9913f09188034dd4dfb09222520c79d3d473b04733d0f33618b25
three_wall_j2_symbolic_decision_v1.json  d91d15f3f6e5fbec7dae74466c1b2ef603af666f5ce3c662dcde4616d383c638
three_wall_j2_z3_proofs_v1.json.gz       407b89a59c26165a8118b6ea717d569159e14058a0e24422d277ac4cdbbd53bb
```

## No-claim boundary

- This kills only the displayed three walls.
- It does not rule out any other subdivision of `J_2`, including unequal
  ratios, different walls, or more walls.
- It says nothing by itself about a `J_2 -> J_3` construction: the candidate
  is negative, so there is no positive scaling implication to transport.
- It does not decide `W_2`, virtual cancellation, or unrestricted `MAX11`.
- No novelty or external-referee claim is made.
