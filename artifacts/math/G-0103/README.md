# G-0103 — semantic status of the leaf/bridge incidence

## Verdict

The G-0099 leaf-deletion/opposite-colour-edge incidence has one real but
strictly bounded semantic property, followed by three decisive failures:

1. **Tree-only quotient: exact positive at `n=5` and `n=7`.**  On the span of
   balanced bicoloured tree atoms alone, `D` respects every functional
   relation tested.  It therefore induces an abstract linear map from the
   tree-function span to the forest-function span in these two dimensions.
2. **Zero-extension: exact negative already at `n=5`.**  Defining `D` on
   tree atoms and zero on every other fixed-degree Rueß atom is not a
   representation-independent operation on support functions.
3. **Eventwise tied face: exact negative already at `n=5`.**  The honest
   exposed face retains selected endpoints.  The resulting branch-specific
   translations are generally nonlinear relative to the unshifted forest
   atom and cannot be discarded even modulo global translation.
4. **Canonical tagged-facet repair: exact negative already at `n=5`.**  Even
   retaining the selected endpoint as a loop on the appropriate residual
   branch does not respect functional relations among tree atoms.

Consequently the G-0099 constraint is, at present, a **combinatorial gauge on
coefficient vectors**, not an induction law for support functions or
polytopes.  Its lower-dimensional solvability does not transport MAX6 to
MAX7, and it supplies no MAX10-to-MAX11 implication.

## Definitions and normalization

For a multiset of coordinate edges `A`, put

```text
Z_A = sum_{ij in A} [e_i,e_j],
P(A,B) = conv(Z_A union Z_B).
```

For an unordered-colour orbit `T=(A,B)` on `n` labels, the Rueß atom is

```text
Phi_n(T) = sum_{sigma in S_n} h_{P(sigma A,sigma B)}.
```

Let `T_n` be the rational vector space on balanced bicoloured spanning-tree
orbits (`|A|=|B|=(n-1)/2`), and let `F_(n-1)` be the space on balanced
two-component forest orbits after a leaf and one opposite-colour edge have
been removed.  If `r(T,F)` counts such deletions from the chosen tree-orbit
representative, G-0099 uses

```text
D_n(F,T) = n r(T,F).                                      (1)
```

This factor is not heuristic.  Writing `N_T,N_F` for labelled orbit sizes,
`a_T,a_F` for unordered-colour stabilisers, and `q(F,T)` for reverse
extensions, the independent enumeration checks every nonzero entry of

```text
N_T r(T,F) = n N_F q(F,T),
a_F r(T,F) = a_T q(F,T).                                 (2)
```

The semantic columns were reconstructed independently of G-0099: literal
enumeration of every vertex order, exact signed back-degree words, primitive
ReLU hinges, and exact linear parts on the ascending braid chamber.

## Result 1 — the restricted quotient really does descend

The required and sufficient condition for a linear map on the tree-function
span is

```text
ker(Phi_n | T_n) subset ker(Phi_(n-1) D_n).                (3)
```

Equivalently, stacking `Phi_(n-1) D_n` below the matrix for `Phi_n` must not
increase column rank.

| test | tree orbits | tree rank | tree kernel | forest orbits | forest rank | rank `D` | stacked rank |
|---|---:|---:|---:|---:|---:|---:|---:|
| `n=5 -> 4` | 6 | 4 | 2 | 2 | 2 | 2 | 4 |
| `n=7 -> 6` | 53 | 34 | 19 | 11 | 9 | 11 | 34 |

Thus (3) holds exactly in both tested dimensions.  The lexicographically
first nonzero entry of `D` was then incremented by one.  The mutated stacked
rank rises at `n=5` from 4 to 5 and supplies the exact killed kernel relation

```text
(1,-2,0,1,0,0),
```

whose mutated lower residual has nonzero entries `6,18`.  The same fixed
mutation is recorded for `n=7` in the final receipt.

This is **quotient descent**, not a constructed geometric operation.  At
`n=7`, the forest coefficient space has dimension 11 while its semantic
image has dimension 9, so even the output of the induced abstract map is
only determined modulo a two-dimensional forest kernel.  Nothing here
establishes (3) at `n=11`.

## Result 2 — zero on non-trees is not semantic

The first complete nondegenerate fixed-degree family is small enough to
settle exactly.  For `n=5,k=2`, including loops, repeated edges, and common
branch occurrences:

```text
15 edge types
120 branch multisets
7,260 raw unordered branch pairs
131 S_5 x colour-swap orbits
125 non-tree orbits and 6 tree orbits.
```

The full 131-column semantic matrix has rank 17.  The 125 non-tree columns
alone also have rank 17.  If `D` is put on the six tree columns and zero on
the other 125, appending its lower semantic image raises the rank from 17 to
19.  Hence this extension cannot factor through support functions.

One explicit eight-term witness, writing `ij` for edge `(i,j)`, is

```text
 2 Phi({00,00}|{00,12})
+1 Phi({00,00}|{12,34})
-2 Phi({00,01}|{00,23})
+2 Phi({00,01}|{02,34})
-2 Phi({00,01}|{12,34})
-4 Phi({00,11}|{02,34})
+2 Phi({00,12}|{01,34})
+1 Phi({01,02}|{03,04}) = 0.                              (4)
```

The last term is the balanced two-colour star tree; all other terms are
non-trees.  The exact 20-row upper normal-form residual in (4) is zero.  The
zero-extended lower residual is

```text
(0,0,240,720),                                             (5)
```

which is nonzero.  Changing the first coefficient in (4) by one produces an
upper residual `24`, so the witness check rejects its planted mutation.

This is the smallest decisive reason G-0099's imposed incidence rows cannot
be interpreted as a functionally necessary condition on a general Rueß
representation: two coefficient vectors for the same function receive
different lower functions.

## Result 3 — the honest exposed face carries endpoint terms

Let `e` and `f` be the deleted opposite-colour edges.  If a normal `u` is
constant on every residual component, then every undeleted segment remains
as a segment and the two branch faces are exactly

```text
face_u(Z_A) = e_p + Z_(A-e),
face_u(Z_B) = e_q + Z_(B-f),                               (6)
```

where `p,q` are the `u`-maximal endpoints of `e,f`.  On a branch tie,

```text
face_u(P(A,B)) = conv(e_p+Z_(A-e), e_q+Z_(B-f)).            (7)
```

The unshifted D atom drops `e_p,e_q`; (7) shows the missing terms exactly.
They can be encoded as one loop on each residual branch before the leaf
coordinate is removed.

The smallest explicit failure uses

```text
A={(0,1),(0,3)}, B={(0,4),(1,2)},
leaf=4, e=(0,4), f=(0,1), u=(0,-1,-1,0,1).
```

Both branches have support zero at `u`.  After deleting coordinate 4, the
actual face is

```text
conv(e_0+[e_0,e_3], [e_1,e_2]),                            (8)
```

whereas D uses

```text
conv([e_0,e_3], [e_1,e_2]).                                (9)
```

The vertex coordinate sums of (8) are `{1,2}`; those of (9) are `{1}`.
Moreover the support difference `(8)-(9)` at `x=e_0` and `x=-e_0` is
respectively `1` and `0`.  A global translation would give opposite values,
so the discrepancy is not affine.  A common-endpoint star event is retained
as a positive control and differs by exactly one global translation.  Changing
the counterexample leaf-normal value from `+1` to `0` destroys the tie and is
rejected.

The standard coordinate operations fail for the same concrete reason:

- `x_leaf -> -infinity` replaces the leaf segment by the surviving endpoint
  and retains every opposite-colour edge; it does not delete an arbitrary
  `f`.
- `x_leaf -> +infinity` eventually selects the branch containing the leaf
  edge, eliminating the outer two-branch hull.
- restriction `x_leaf=0` projects `[e_leaf,e_a]` to `[0,e_a]`, rather than
  deleting it;
- identifying the leaf with its neighbour contracts the leaf segment but is
  tree-dependent and still does not remove an arbitrary opposite edge;
- a fixed exposed face either selects one outer branch or has the endpoint
  terms in (7).  A directional jump records the same branch switch rather
  than the unshifted deletion sum.

## Result 4 — retaining the endpoint still does not define an eventwise map

The most direct repair was bound before execution in
`TAGGED_FACET_CORRECTION_PREREGISTRATION.md`.

Let the leaf edge have sign `s in {+1,-1}` in `B-A`.  After removing `e,f`,
let `C` contain the leaf neighbour, let `D` be the other residual component,
and put

```text
d = (#B edges internal to C) - (#A edges internal to C).
```

Normalize the component levels to `u_C=0`.  The tie equation is

```text
0 = -d u_D + s(max(u_leaf,0)-max(0,u_D)).                  (10)
```

There is one full-dimensional tied-facet chamber with `u_leaf>0`:

```text
if s*d >= 0: u_D=+1, u_leaf=s*d+1, select f's endpoint in D;
if s*d <  0: u_D=-1, u_leaf=-s*d,  select f's endpoint in C.
```

After deleting the leaf coordinate, the selected endpoint of `f` was retained
as a branch-specific loop and all event functions were summed with the factor
`n` from (1).  This is the canonical eventwise full-facet correction to D.

It still fails the semantic kernel test at `n=5`:

```text
tree rank                    4
tree kernel dimension        2
tagged output rows           23
rank after stacking          6
```

The already-known exact tree relation

```text
(1,-2,0,1,0,0)
```

has zero upper residual but corrected-facet residual beginning

```text
(-90,40,-10,0,20,0,-10,20,30,...)
```

and ending in linear entries `(-40,0,120)`.  All 32 event normals tied
exactly; increasing the leaf level by one destroyed every tie.  The
preregistered stop therefore fired at `n=5`; no `n=7` correction run was
performed.

## What this changes

The lower-dimensional G-0099 membership result remains exact as a constrained
coefficient solve, but its proposed semantic interpretation is now sharply
bounded:

- `D` can be used as a heuristic coordinate gauge inside the tree sector;
- it is not a necessary condition on arbitrary Rueß representations;
- it is not coordinate restriction, an infinity limit, an unshifted face
  map, or the canonical selected-endpoint facet sum;
- a successful future transport must define nonzero correction terms on the
  full atom family and prove a representation-independent fixed-normal or
  genuinely additive valuation identity.

The retry predicate is therefore narrow: retry this route only with an
explicit operator on **every** fixed-degree atom, fixed independently of its
chosen graph presentation, for which `ker(Phi)` containment is proved or
passes before it is applied to MAX coefficients.

## Exact replay

```bash
cd /data/projects/relu-depth-frontier-research

.venv/bin/python -B artifacts/math/G-0103/semantic_descent_audit.py \
  --max-n 7 \
  --output artifacts/math/G-0103/n5_n7_semantic_descent_v1.json

.venv/bin/python -B artifacts/math/G-0103/zero_extension_audit.py \
  --output artifacts/math/G-0103/n5_zero_extension_v1.json

.venv/bin/python -B artifacts/math/G-0103/ridge_face_counterexample.py \
  --output artifacts/math/G-0103/n5_ridge_face_counterexample_v1.json

.venv/bin/python -B artifacts/math/G-0103/tagged_facet_correction_audit.py \
  --max-n 5 \
  --output artifacts/math/G-0103/n5_tagged_facet_correction_v1.json
```

## Claim boundary

All four results are exact rational/integer statements in the dimensions and
families named above.  The tree-only positive is bounded to `n=5,7`.  The
three negative results refute the specified uniform raw/eventwise operator
interpretations because each already fails at `n=5`.  They do **not** refute
an as-yet-undefined fixed-normal or weighted flag valuation, the complete
degree-five Rueß ansatz at `n=11`, or unrestricted two-hidden-layer ReLU
representability of MAX11.

## Certification state

These artifacts are author-produced and author-replayed in one agent context.
“Independent of G-0099” here means a separately transcribed enumerator and
literal semantic normal form; it does **not** mean independent-agent or
different-lineage verification.  The results therefore stand as exact
computed-bounded evidence pending a fresh clean-room replay/referee.  The
tagged correction was hash-bound before execution.  The tree-descent,
zero-extension, and first face counterexample were exploratory discoveries
that were frozen and deterministically replayed afterward, not
retrospectively relabelled as preregistered.
