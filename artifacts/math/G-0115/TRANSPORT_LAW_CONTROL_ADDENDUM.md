# G-0115 transport-law control addendum

Timestamp: 2026-08-31T02:16:16+02:00. Frozen before regenerating the raw
MAX8-to-MAX9 fibers or inspecting the 395 fitted coefficients beyond the
counts already stated in `TRANSPORT_LAW_PREREGISTRATION.md`.

This addendum removes two implementation degrees of freedom left implicit in
the main preregistration.

## Signature ladder

The source-local families are tested in this order:

1. `coarse`: added-edge relation/equality pattern plus the cancelled source
   signed degrees and isolation flags of the four endpoint slots;
2. `incidence`: `coarse` plus adjacency multiplicity and connected-component
   coincidence among endpoint blocks in the cancelled source union;
3. `radius1`: `incidence` plus the complete multiset of signed source-edge
   occurrences from every endpoint block to other endpoint blocks or to an
   external radius-one neighbor, including the external neighbor's signed
   degree profile.

For each family, global branch swap and the two within-edge endpoint swaps are
quotiented by taking the lexicographically least exact descriptor. No absolute
label, source index, target datum, solver datum, or signed-class hash occurs in
a signature.

The aggregation order is raw sum first and per-full-atom-fiber average second.
The search stops at the first family that meets both preregistered description
caps and all exact controls. More detailed families may still be reported for
falsification but cannot displace an earlier eligible positive.

## Fixed relabel controls

On nine labels the two valid simultaneous relabelings are

```text
pi  = (1 2 3 4 5 6 7 8 9)
tau = (1 9)(2 8)(3 7)(4 6), with 5 fixed.
```

They are applied to the source pair and both added edges. Every descriptor in
the raw census must preserve all three signatures under both maps.

The broken-control witness is the lexicographically first raw descriptor in
`(source_index, left_edge, right_edge)` order satisfying all of:

- both added edges are distinct nonloops;
- each added edge has an endpoint active in the cancelled source graph;
- `pi` moves at least one such active endpoint outside its original endpoint
  set.

For this one frozen witness, applying `pi` to the source pair while leaving
both edges fixed, and applying `pi` to only the left added edge, must each
change the `radius1` signature. If the predicate selects no witness, the
implementation fails rather than weakening the control.

The source-coefficient mutant changes the numerator of public MAX8 term zero
by `+1` at that term's existing denominator. The emitted-certificate mutant
changes the numerator of the first term in canonical signed-class-hash order
by `+1` at that emitted coefficient's denominator.

## Exact comparison order

Support purity is descriptive only. Coefficient reproduction is decided on
all 22,666 signed-class rows, including the 22,271 zero target coefficients.
Functional membership is then decided on all 20,685 hinge rows and all nine
linear rows. A signed-class reproduction failure does not imply functional
nonmembership; a hinge-only success does not count as functional membership.
