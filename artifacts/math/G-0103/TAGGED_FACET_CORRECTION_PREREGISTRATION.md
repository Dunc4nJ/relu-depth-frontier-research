# G-0103 tagged-facet correction confirmation binding

Bound before executing `tagged_facet_correction_audit.py` on 2026-08-30.

## Question and exact map

For every balanced bicoloured tree orbit on odd `n`, take every pair
`(leaf, opposite-colour edge)`.  Remove the leaf edge and opposite edge.  Let
`C` be the residual component containing the leaf's neighbour, let

```text
d = (# blue residual edges internal to C) - (# red residual edges internal to C),
s = +1 for a blue leaf edge and -1 for a red leaf edge.
```

The unique full-dimensional two-branch tied facet has leaf level positive.  If
`s*d >= 0`, set the other-component level to `+1`, the leaf level to
`s*d+1`, and select the opposite edge's endpoint in the other component.  If
`s*d < 0`, set the other-component level to `-1`, the leaf level to `-s*d`,
and select its endpoint in `C`.  After deleting the leaf coordinate, retain
that selected endpoint as a loop on the opposite-colour residual branch.
Sum the resulting symmetrised support functions with the same factor `n` as
the orbit-basis leaf/bridge count.

The test is the exact commutative-square condition

```text
ker(Phi_tree,n) subset ker(R_tagged,n).
```

Equivalently, appending `R_tagged,n` below the complete tree normal-form
matrix must not increase column rank.

## Region, order, and decision

- First and primary region: the complete six balanced tree orbits for
  `n=5`, all deletion events, literal permutation normal forms.
- If `n=5` passes, extend unchanged to all 53 tree orbits for `n=7`.
- If `n=5` fails, stop: that already refutes a uniform all-odd-`n` semantic
  interpretation of this tagged event sum.  An `n=7` run would be descriptive
  only and is not required by this decision.
- **Pass:** stacked rank equals tree rank and every exact tree-kernel basis
  vector has zero tagged residual.
- **Fail:** stacked rank is larger and an exact integer tree-kernel vector has
  a nonzero tagged residual.
- No extrapolation to `n=11` from a pass at `n=5` or `n=7`.

## Controls and fixed mutation

- Every derived normal must tie the two original branches exactly.
- For every event, increasing the leaf normal level by one must destroy the
  tie.  This mutation is fixed before the run.
- The existing independent tree normal-form control and the one-entry `D`
  mutation remain in `n5_n7_semantic_descent_v1.json`; they do not substitute
  for the tagged-face mutation above.

## Frozen producers

```text
5dbfbe534ae036050bd0e8c2d1e28d5da3aa9a2d3776dd237547f60973f88dc2  tagged_facet_correction_audit.py
790ce4e3a98ed066238a36dc3f9b18b457ae82d2bbd2b8c8bf71551dec32e76d  semantic_descent_audit.py
```

Command:

```bash
.venv/bin/python -B artifacts/math/G-0103/tagged_facet_correction_audit.py \
  --max-n 5 \
  --output artifacts/math/G-0103/n5_tagged_facet_correction_v1.json
```

## No-claim boundary

This decides only whether this precisely defined endpoint-tagged event sum
descends on the tested balanced-tree semantic quotient.  It does not decide
whether some fixed-normal face map, differently weighted flag valuation, or
other correction exists; it does not construct or obstruct MAX11.
