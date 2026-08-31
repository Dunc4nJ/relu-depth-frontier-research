# G-0115b preregistration — coefficient-frozen MAX9 residual repair

Registered after the target-blind G-0115 census and before generating any
repair-column normal form, modular rank, target rank, or coefficient.

## Frozen inputs

- census report SHA-256
  `844dba5cf023f68a083261dd1612503c16309297f21ca57e26497f7a6df28d7a`;
- representative map SHA-256
  `2fa23b8346858e85b4689a36c795ddac6d109ff42535d2238502b3c64117a148`;
- semantic DP SHA-256
  `d63f08e9e641109154d0e16f0d84d04a0ad4edd4402b8ffe5d01985de9163f71`;
- MAX8/MAX9 certificate hashes and term counts as in `PREREGISTRATION.md`.

The census found 328 of the 337 distinct public MAX9 signed-W classes in the
22,666-class lift quotient.  For every contained public class, freeze its
public coefficient and replace it by the lexicographically frozen lift
representative in the map.  These 328 classes are excluded from the repair
dictionary.  The repair dictionary is exactly the remaining 22,338 lift
signed-W classes, in deterministic target-aware order described below.

## Exact target system

Let `H` be the complete primitive ordered-cone hinge vector and let `Lambda`
be the ninth alternating finite difference of the ordered-cone linear vector.
The nine missing public terms, with their untouched public coefficients,
define one weighted residual

```text
b = (sum_missing H, sum_missing Lambda).
```

Independently require `sum_missing H = -sum_retained_public H` using the
original public templates.  Solve only

```text
[H_repair; Lambda_repair] x = b.
```

The Lambda row prevents the zero-function cancellation even if a retained
class accidentally re-enters; exclusion is also checked explicitly.  A
solution makes the 328 fixed lift terms plus the repair combination
hinge-free with exactly the MAX9 alternating invariant.  Its remaining linear
error must then be decomposed exactly in the embedded subset-maximum basis
`U1,...,U8` and compiled from known MAX1--MAX8 identities.

## Deterministic search order and resource gate

Repair classes are ordered by an invariant topology distance to the nine
missing signed graphs: signed mass mismatch, active-vertex mismatch, absolute
component/cycle-rank mismatch, sorted absolute-degree mismatch, and sorted
per-branch degree mismatch, followed by signed-certificate hash.  Test nested
prefixes `256, 512, 1024, 2048, 4096, 8192, 16384, 22338`.

Before a prefix is solved, benchmark exact DP normal forms on the first 128
columns and project full generation time/nonzeros.  Continue only if the
full projection is at most four local CPU-hours and the selected dense or
sparse solve representation is at most 16 GiB.  Modular arithmetic may select
a candidate support but never establishes equality.  A positive must be
lifted over `Q` and replayed on every one of the 20,685 degree-four primitive
hinge directions plus `Lambda`; every omitted row must be explicitly zero.

If a prefix is nonmember modulo a frozen prime, grow the prefix; do not promote
that modular miss.  If the full dictionary is exactly nonmember, extract a
primitive rational separator, replay it on all repair columns, and report its
pairing with each of the nine missing terms.  No one-prime miss is a
characteristic-zero obstruction.

## Controls

The DP must exactly replay the public MAX8 and MAX9 certificates and agree
with literal `9!` enumeration on two frozen atoms.  Relabelling, branch swap,
and common-edge padding must preserve hinge semantics; one edge mutation must
change it.  A planted linear system must exercise both member and nonmember
branches.  The final coefficient mutation must fail complete replay.

## No-claim boundary

An exact positive is a new MAX9 certificate inside a source-derived family and
a second parity-lift calibration.  It is not MAX11 and not an induction
theorem.  A negative excludes only the frozen coefficient-retained repair
protocol (or, on the full prefix, this finite lift span); it is not a ReLU
depth lower bound.
