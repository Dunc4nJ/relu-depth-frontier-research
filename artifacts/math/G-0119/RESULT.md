# G-0119 result — exact obstruction to the frozen algebraic recurrence

## Bottom line

The preregistered 24-parameter signed-edge/signed-degree operator cannot
simultaneously transport the public MAX6 and MAX8 certificates through the two
known degree-raising transitions.

The complete stacked characteristic-zero system has

```text
rows                         21,214
parameters                       24
rank_Q(operator matrix)          20
rank_Q(augmented matrix)          21
```

Thus the exact joint targets are not in the frozen operator span.  A 21-row
integer submatrix independently witnesses the obstruction: its coefficient
matrix has exact rank 20 and adjoining its target column raises the exact rank
to 21.  The witness canonical SHA-256 is

```text
21f13b2a9ee2be7f07b1b193621efdba17ee3303fabb829cf86c7a46aea88d8e
```

Per the preregistered stopping rule, no MAX10-to-MAX11 coefficient or semantic
value was evaluated.

## Frozen family decided

For source signed-edge vector `W`, added-edge difference `U`, and unsigned
endpoint-incidence map `D` with loops counted once, put

```text
a=<W,U>, b=<DW,DU>, q=<U,U>, r=<DU,DU>.
```

The raw descriptor weight was affine in the source degree `k` on each of the
twelve frozen monomials

```text
1, a, b, a^2, a*b, b^2, q, r, a*q, b*q, a*r, b*r.
```

The same 24 rational parameters were required to hit every primitive hinge row
and the full linear vectors at MAX6-to-MAX7 and MAX8-to-MAX9.  This is the only
family the rank obstruction decides; the basis was not expanded or altered
after the result.

## Complete exact construction and controls

- MAX6-to-MAX7: all 3,136 raw descriptors reconciled into 607 signed-`W`
  classes; 513 complete hinge rows plus seven linear rows.
- MAX8-to-MAX9: all 139,725 raw descriptors reconciled into 22,666 signed-`W`
  classes; all 20,685 complete hinge rows plus nine linear rows.
- Public MAX6, MAX8, and MAX10 certificates replayed exactly with zero hinge
  residual and target linear vectors; a one-unit first-coefficient mutation was
  rejected for each.
- The exact 395-term G-0115 MAX9 identity replayed against the bound complete
  matrix with linear vector `e_9`; a one-unit coefficient mutation was rejected.
- Two simultaneous relabellings and global branch swap preserved the feature
  map.  Source-only relabelling, one-edge-only relabelling, and the deliberately
  wrong loop-twice incidence convention were detected.
- Literal permutation enumeration and the independent ordered-normal-form DP
  agreed on the planted small atom.

The small-witness verifier imports neither the producer nor a semantic matrix.
It recomputes the 20/21 exact ranks directly from the serialized integer rows.
As a red-direction control, setting the witness target column to zero collapses
the augmented rank back to 20.

## No-claim boundary

This result does **not** show that MAX11 is not representable, that the public
MAX10 lift span misses MAX11, that a different algebraic or equivariant
operator fails, that the complete degree-five graphical dictionary fails, or
that arbitrary two-hidden-layer ReLU networks have a graphical normal form.
It rejects only the precisely frozen twelve-monomial, affine-in-degree,
raw-sum recurrence.  MAX11 was not tested in this artifact.

## Evidence and replay

```text
f10eb7e013d0442ce54bd1ea8ce212916cfd8e6daf2bb6f27390c826bdc8d155  PREREGISTRATION.md
6821f2f8482faab872f468a0298f303ae4db6df9910bd3b32685e92e63e8d7a9  algebraic_signed_degree_operator.py
85438a5fe983b638dd95f92c046be5b4a83ab88e0680de2f9c1c0eb05c0991cb  algebraic_signed_degree_operator_v1.json
e56260b55c2dcd9f2b31eb76de4389c067efd439609e2365e7e847e32cc6dd4f  verify_algebraic_signed_degree_obstruction.py
0a3c1bb200764026dbc9eef3ac1762f3fa63d5034ea52ded7a8434d86f551795  independent_witness_replay_v1.json
```

Run from the repository root:

```text
.venv/bin/python -B artifacts/math/G-0119/algebraic_signed_degree_operator.py --self-test
.venv/bin/python -B artifacts/math/G-0119/verify_algebraic_signed_degree_obstruction.py \
  --output /tmp/g0119-independent-replay.json
```

The second command requires an unused output path.
