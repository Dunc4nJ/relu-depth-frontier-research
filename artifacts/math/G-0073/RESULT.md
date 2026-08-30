# G-0073 registered result: exact bounded survivor

The preregistered Y-spoke family **survives** the frozen four-level symmetric
profile gate over the rationals.

| quantity | registered value |
|---|---:|
| profile rows | 364 |
| Y-spoke orbit columns | 8,104 |
| averaged carriers | 3 |
| exact matrix rank | 258 |
| exact row nullity | 106 |
| emitted witness support | 257 |

The registered integer matrix has SHA-256
`958bcdc7fbfc3d925aaed739aa98b60e10da35056186ec7e7c620cd26f34dc32`.
The target has SHA-256
`a3d3be16df8de6f25b40e318f656efbee4607806413e72a48b2d276d7f21f4d7`.
Exact Gram/RREF resolution gives rank 258, and the target is in its rational
column span.  The emitted basic witness uses 256 Y-spoke orbit columns and the
averaged edge carrier `C_E`, with sparse-coefficient digest
`aa28b03000d18c1471ed7806614fb33f824e63343a7753f39f872905d31b2309`.
FLINT and a separate stdlib `Fraction` replay both give zero residual on all
364 rows.

The registered outcome is
`artifacts/math/G-0073/y_spoke_profile_gate_v1.json.gz`, byte SHA-256
`59b81312f44e98ae61481fcac2e61075d60d187c4bf5b4201a821c44ec3b60bb`
and scientific-payload SHA-256
`6c006df13c7e010128b8f2ce71b5a2eb9e599581d575f262ef8084637ef92f56`.

## Independent replay

A fresh-context, disjoint implementation reconstructed the 252 bases, 18,400
raw seeds, all 256 selected Y-spoke descriptors, the selected semantic
columns, and the carrier without importing or executing the producer.  Its
exact `Fraction` replay has zero residual on all 364 rows.  It also finds rank
258 for the selected 258 columns modulo 1,000,003, 1,000,033, and an extra
prime 1,000,037.  See `artifacts/cleanroom/G-0073/AUDIT.md` and run:

```bash
.venv/bin/python -B artifacts/cleanroom/G-0073/replay_cleanroom.py
```

This is same-model-lineage T1 evidence using an independent implementation,
not T2 or human review.  The clean-room audit does not reconstruct all 8,107
columns, so it independently validates the witness and a rank-258 lower bound,
not the producer's full-matrix rank upper bound.

## Exact claim boundary

This is a finite-grid survivor, not a global CPWL identity or a MAX11 network.
The 364 constraints leave 7,849 coefficient degrees of freedom, and the
displayed 257-term basic solution has very large interpolation-like rational
denominators.  Failure of that one vector on a new point would not reject the
family; later gates must retain all 8,107 coefficients.

The shortest next discriminator is the complete three-valued spacing gate:
after normalizing the levels to `(0,t,1)`, every branch switch occurs at a
Farey-order-six breakpoint.  Testing all count profiles at all such
breakpoints can therefore certify every three-valued input while preserving
the full coefficient space.  A survivor must then face the global
facet-curvature normal form.
