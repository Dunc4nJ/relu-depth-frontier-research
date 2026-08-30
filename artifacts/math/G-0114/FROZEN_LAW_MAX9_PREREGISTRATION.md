# G-0114 preregistration — frozen local law on the genuine 8 -> 9 raise

Frozen after `degree_raising_identity_v1.json` and
`graph_recurrence_v1.json` were written, before applying any fitted weight to
MAX8-derived atoms or computing an aggregate MAX9 normal form.

```text
1a59b11a0dbb6e4bd91861c001687d1f93000f1bde7340d62f027626e5f77d6f  degree_raising_identity_v1.json
eeb70dd51d2d24eb5a2a9215a7700c8d12822cd08b5116b8245c830b7855c57b  G-0090/known_certificate_normal_form.py
68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3  certificate_8_3.json
4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88  certificate_9_4.json
```

## Frozen law

Use exactly the 148 nonzero local-signature weights from
`local_incidence_test.joint_shared_law_decision.support`.  Those weights were
fit jointly to the complete MAX5 -> MAX6 and MAX6 -> MAX7 normal forms.  Do
not refit, rescale, fill missing signatures, or use any zero-weight signature.

For every public MAX8 degree-three source term and every ordered pair of
distinct nonloop added edges that share one endpoint or are vertex-disjoint,
multiply the lifted atom by

```text
source coefficient * frozen weight[local signature],
```

with absent signatures assigned weight zero.  Quotient only by a lossless
full-atom incidence certificate, summing exact rational fiber coefficients.
Then compute the complete exact ordered-cone normal form of every nonzero
quotient class with the bound subset-DP evaluator and sum it exactly.

## Decision

- Exact equality to `x_9` on every linear and projective-hinge row is a
  three-transition replay of this one frozen law.  It is still not MAX11.
- Any nonzero exact residual rejects this 148-weight law as an arity-universal
  degree-raising identity.  Record the first residual row and full residual
  digest.
- A one-unit mutation of the first nonzero law weight must change the output;
  coordinate relabeling and branch swap must preserve quotient classes.

Failure rejects this frozen solution, not every possible vector in the
319-dimensional joint small-arity solution space.  No sampled row may be used
to claim equality; sampled rows may only stop computation early as a falsifier.

