# G-0072 result

The fully registered asymmetric loop–edge span gate is negative at both
frozen primes.

| quantity | modulo 1,000,003 | modulo 1,000,033 |
|---|---:|---:|
| column rank | 3,518 | 3,518 |
| rank after appending `11! * MAX11` | 3,519 | 3,519 |
| target in registered sketched span | no | no |

Because the registered map is a left-linear CountSketch on all hinge rows and
retains the eleven linear rows exactly, target nonmembership in the sketched
system implies target nonmembership in the complete unsketched system over
the same field.  Therefore no coefficient choice in the frozen 3,754 graph
orbits plus the two linear carriers solves MAX11 modulo either registered
prime.

This does **not** establish an exact-rational obstruction: a hypothetical
rational solution could have a denominator divisible by a registered prime.
It also says nothing about other atom families or unrestricted two-hidden-layer
ReLU networks.

The forest-level implication is to stop expanding this graphical loop–edge
catalogue.  The next construction test should change the inner-wall geometry;
the minimal candidate currently identified is the support-three Y-spoke wall
`x_l + x_11 - 2*x_k = 0`, which preserves the required MAX10 facet but is no
longer a braid/root direction.
