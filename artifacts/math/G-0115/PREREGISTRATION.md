# G-0115 preregistration — MAX8-to-MAX9 parity-lift calibration

Registered before writing or running the producer and before inspecting any
lift/public-support overlap.  G-0112 found exact MAX6-to-MAX7 membership after
adding one arbitrary edge to each branch of every public MAX6 degree-two
template.  This experiment tests the next transition with the same parity:
public MAX8 degree-three templates to degree-four MAX9 templates.

## Frozen family

Load the 69 public MAX8 terms and, for every term, append independently to
each branch one unordered loop-or-nonloop edge on labels `1,...,9`.  There are
`C(10,2)=45` edge choices per branch and exactly

```text
69 * 45 * 45 = 139,725
```

raw lifts.  Source coefficients are untied.  Compute two exact quotients:

1. the degree-four pair-template orbit under simultaneous `S9` relabelling
   and branch swap;
2. the signed graphical difference `W` after cancelling common edge
   occurrences, modulo `S9` and global sign.

The public 337-term MAX9 certificate is an untouched comparison set.  Report
exact pair-template and signed-W support overlap in both directions, plus one
deterministic representative per lift orbit.  The primary slices are all
edges, SHARE-distinct nonloops, and DISJOINT nonloops; loop/common records are
retained rather than silently discarded.

## Exact semantics of the cheap containment gate

For a fixed degree, equal signed-W orbits have identical ordered-cone hinge
semantics; changing common cancelled edges changes only a symmetric linear
function.  Therefore complete signed-W containment of the public MAX9 support
would give an exact lift-family MAX9 identity after an explicitly computed
linear correction.  Pair-template containment is an even stronger literal
containment.  Partial overlap is only a census and proves no membership.

## Frozen inputs and controls

- MAX8 certificate SHA-256
  `68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3`;
- MAX9 certificate SHA-256
  `4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88`;
- expected term counts: 69 and 337;
- every branch has degree three before and degree four after lifting.

Relabelling and branch swap must preserve both certificates.  Changing one
edge multiplicity and changing loop/nonloop status must be detected.  The
producer must reconcile raw counts and class multiplicities exactly.  A
deterministic sample of canonical-certificate collisions must be checked by
literal graph isomorphism with typed occurrence nodes.

## Decisions frozen before outcomes

- If all 337 public pair-template orbits occur, stop: emit the literal
  transported certificate and verify it with the public exact verifier.
- Else if all public signed-W orbits occur, compute the exact common-padding
  linear correction, emit the corrected certificate, and verify it globally.
- Otherwise report the exact overlap and quotient size.  Continue to an exact
  semantic rank/membership test only if the lift quotient is at most 100,000
  signed-W orbits and an unchanged exact DP normal-form benchmark projects at
  most four local CPU-hours and 16 GiB peak RAM.  The semantic test, if
  launched, must be separately preregistered before target rank access.
- Failure of this transition materially lowers the prior that G-0112 is a
  general parity-lifting law; success raises it but does not transport to
  MAX11.

## No-claim boundary

This is an exact finite calibration at MAX9, already known representable.  A
positive is a second lower-arity structural example, not a MAX11 identity or
a universal induction theorem.  A null excludes only this source-derived
degree-four family and is not a ReLU depth lower bound.
