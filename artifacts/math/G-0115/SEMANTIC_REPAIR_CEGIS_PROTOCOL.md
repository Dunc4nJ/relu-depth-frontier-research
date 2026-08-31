# G-0115c protocol — full-family row CEGIS and exact minor lift

Registered after the coefficient-frozen target and family were fixed in
`SEMANTIC_REPAIR_PREREGISTRATION.md`, and before computing any full-family
membership result.  Dense modular pilots on the frozen prefixes through 4096
had returned prefix nonmembership and showed that continuing with complete
dense RREFs would be wasteful.  Those pilots changed the computational route,
not the target, family, coefficient constraints, column order, or standards of
evidence.

## Frozen computation

Generate the complete exact ordered-cone vector `(H, Lambda)` for each of the
22,338 repair classes and store the resulting integer matrix in the already
frozen topology order.  The matrix has 20,686 coordinates: all 20,685
degree-four primitive hinge directions in lexicographic order, followed by
`Lambda`.  Bind its bytes, row order, column order, semantic kernel, source
map, and target certificates by SHA-256.

Test the preregistered prefixes

```text
256, 512, 1024, 2048, 4096, 8192, 16384, 22338.
```

Start with `Lambda` and at most 255 evenly spaced nonzero target hinge rows.
Rows persist when the prefix grows.  At a prefix, solve the selected-row system
modulo 1,000,003.  If it is nonmember, replay the same projection at 1,000,033
and 1,000,037, record only finite-field prefix nonmembership, and grow.  If it
is a member, replay the selected modular solution on every coordinate.  Add at
most 256 evenly spaced nonzero residual rows and repeat.  The ordering and
batch rule are deterministic.

A modular full replay is only a support/minor selector.  Lift the selected
minor over `Q`, replay it on every one of the 20,685 hinge directions and
`Lambda`, and reject it on any residual.  A positive then receives the same
fixed-retained certificate and lower-arity correction treatment specified in
the original preregistration.  Mutating one nonzero coefficient must fail
complete replay.

If the complete dictionary is nonmember only modulo the frozen primes, report
that strictly as a modular gate and run a separate exact rational-separator
stage before making a characteristic-zero negative claim.

## Claim boundary

Row CEGIS is an exact computational acceleration for the already frozen finite
system.  It does not weaken the final replay requirement.  A positive is an
exact MAX9 calibration inside this lift family, not MAX11 or an induction
theorem.  A modular negative is not a rational obstruction.
