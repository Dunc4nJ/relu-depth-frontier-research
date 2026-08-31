# G-0117c preregistration — exact integer global normal-form replay

Registered while the corrected G-0113 scan was live at or below its observed
100,000/163,740 checkpoint, before the DISJOINT boundary and before any target
membership result.

## Purpose

Remove the remaining two-prime ambiguity from G-0117.  For a denominator-cleared
v2 seed, aggregate the complete ordered-cone normal forms over `Z`, using
arbitrary-precision coefficients, and decide whether the residual normal form is
exactly zero.

The exact replay consumes only schema
`max11-g0117-global-replay-certificate-v2`.  It must enforce the v2 provenance,
the frozen G-0113 input and exact-postprocessor bindings, canonical nonzero
integer coefficients, positive integer target scale, unique in-range sequences,
and the full 163,740-record census.  Unknown certificate fields are refused.

## Exact computation

For every certificate term `a_j F_j`, regenerate `F_j` with the existing full
labelled-`S_11` normal-form kernel.  Accumulate every hinge coefficient and all
11 linear coordinates as arbitrary-precision signed integers.  Subtract

```text
target_scale * 11! * x_11
```

from the linear vector.  Remove exact zero hinge entries and select the
lexicographically first nonzero direction, if any.

Exactly one result is allowed:

- `EXACT_GLOBAL_NORMAL_FORM_ZERO`: every hinge and linear residual is zero;
- `EXACT_GLOBAL_NORMAL_FORM_RESIDUAL`: report the first exact nonzero hinge
  coefficient, or, if all hinges vanish, the first nonzero linear coordinate.

The output must bind the input, certificate, current source, embedded-at-build
source, kernel, executable, and preregistration hashes.  A stale executable
compiled from different source must fail rather than self-attest newer files.

## Controls fixed before implementation

1. The planted v2 certificate `7 F_0 - 6 F_1 = 14 T` must return direction
   `(0,0,0,0,0,0,0,0,1,-2,1)` with exact residual `662784`, reproducing both
   modular residues.
2. Changing the first coefficient from `7` to `8` must change that exact
   residual to `786432`.
3. A unit-level exact accumulator whose synthetic hinge terms cancel and whose
   linear vector equals its scaled target must return exact zero; independent
   hinge and linear mutants must return nonzero.
4. Malformed integers, zero coefficients, duplicate sequences, provenance
   drift, input drift, and unknown certificate fields must be rejected.

## Logical boundary

An all-zero aggregate is an exact identity on the ordered chamber because every
atom's normal-form expansion is an exact equality.  Extending by permutation
symmetry and compiling the orbit identity into the declared two-hidden-layer
architecture remain separate proof obligations.

A nonzero hinge coefficient refutes equality with the linear target only after
the ordered-chamber normal-form uniqueness lemma is pinned: every retained
primitive active direction defines a distinct hyperplane meeting the chamber
interior, and the gradient jump across a generic point of that hyperplane is
its coefficient times the normal direction.  That lemma will be written and
reviewed separately; until then the machine output is named a nonzero normal
form, not silently promoted to an unrestricted lower bound.

Either result remains about the fixed G-0113 family.  A negative is not family
completeness.  Lean formalization begins only if a decisive global identity and
its architecture compilation survive review.
