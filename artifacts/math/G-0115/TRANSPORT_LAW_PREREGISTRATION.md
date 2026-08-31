# G-0115 local transport-law preregistration

Timestamp: 2026-08-31T02:11:36+02:00. This document was frozen after the
395-term degree-four MAX9 certificate passed independent serialized-term
replay, but before its coefficient pattern, its 67 outside-public-support
classes, or their raw lift fibers were inspected beyond the already reported
support counts and column range.

## Question and exact cousin boundary

The new result proves that the complete one-edge-per-branch lift-class span of
the public degree-three MAX8 certificate contains a degree-four MAX9 identity.
It does **not** yet provide an operator on certificates. The transport question
is narrower:

> Do the 67 selected repair classes, together with the 328 retained classes,
> arise from a low-description, relabel-equivariant rule using only a source
> atom, its source coefficient, and the two newly attached edges?

Only a source-local rule is eligible for transport. A rule that refers to the
public MAX9 certificate, the nine missing MAX9 terms, the topology-distance
ordering used by the solver, column numbers, signed-certificate hashes, or the
fitted MAX9 target residual is a **MAX8-to-MAX9 cousin** and cannot be promoted
to MAX10-to-MAX11.

The structurally analogous parity jumps are

```text
MAX6 degree 2 -> MAX7 degree 3,
MAX8 degree 3 -> MAX9 degree 4,
MAX10 degree 4 -> MAX11 degree 5.
```

MAX8-to-MAX9 is the discovery/calibration transition. MAX6-to-MAX7 is the
lower-arity held-out falsifier. MAX10-to-MAX11 is the only target transition
that can establish the intended new identity, and it must be replayed in the
complete exact normal form without refitting.

## Frozen operator semantics

For a source certificate `C = sum_t c_t Phi(P_t)`, a raw lift descriptor is
`r = (P_t, e_L, e_R)`, where one edge is appended to each branch. An admissible
operator has the form

```text
T(C) = sum_r c_t * w(sigma(r)) * Phi(P_t + (e_L, e_R)).
```

Here `sigma(r)` must be invariant under simultaneous coordinate relabeling and
global branch swap. It may use only:

1. the relation/equality pattern of the two added edges;
2. loop status and repeated-endpoint pattern;
3. for each added endpoint, its two branch degrees and union degree in the
   cancelled source signed graph;
4. whether endpoints coincide, are adjacent, or lie in the same connected
   component of that source graph;
5. the isomorphism type of the radius-one rooted signed incidence neighborhood
   around the added endpoints.

The signature may not contain absolute vertex labels, source-term indices,
target data, target residuals, solver ordering, or certificate hashes. Raw
descriptors retain their exact multiplicities. Orbit averaging is a separate
frozen cousin: divide each full-atom output orbit by its raw multiplicity. Sum
and average conventions are tested separately and never mixed after seeing an
outcome.

## Tests and stopping rules

1. **Support explanation.** Regenerate all 139,725 MAX8-to-MAX9 raw
   descriptors and their full-atom and signed-`W` fibers. Measure whether the
   395 nonzero certificate classes are unions of the admissible source-local
   signatures. A signature that also hits unselected classes is not a support
   explanation unless all induced class coefficients cancel exactly under the
   frozen source coefficients.
2. **Coefficient explanation.** For both raw-sum and orbit-average
   conventions, solve over Q for shared signature weights using the complete
   20,694-coordinate MAX9 semantic target. Record rank, nullity, number of
   signatures, minimum support, and exact replay. A solution with more than 32
   nonzero signature weights or more than 64 independent fitted parameters is
   classified as a compressed solve, not a low-description transport law.
   Exact reproduction of the discovered 395 coefficients is reported
   separately; it is not required if a different operator output exactly
   equals MAX9.
3. **MAX8-to-MAX9 exact replay.** Freeze any eligible law before controls and
   require zero on all 20,685 hinge coordinates and linear vector `e_9`.
4. **Lower-arity held-out replay.** Apply the same frozen signature map and
   weights, without refitting, to public MAX6-to-MAX7. Unseen signatures get
   weight zero. Failure rejects an arity-independent universal law but not a
   possible explicitly arity-dependent cousin.
5. **Joint-law safeguard.** If the frozen pivot law fails MAX6-to-MAX7, decide
   whether any one weight vector in the same at-most-64-parameter family fits
   MAX6-to-MAX7 and MAX8-to-MAX9 jointly. This prevents rejection based only on
   an arbitrary MAX9 nullspace representative. A joint law must still obey the
   32-nonzero-weight cap.
6. **MAX10-to-MAX11 replay.** Only a law passing the joint lower transitions is
   applied to the public MAX10 certificate. No weights, signatures, support
   thresholds, normalizations, or representative choices may be changed.
   Success requires an independently serialized exact degree-five certificate,
   zero residual in the complete MAX11 ordered-cone normal form, linear vector
   `e_11`, and coefficient-mutation rejection.

If the 32/64 caps fail, the output is still useful as a quantified compression
result but is not called a transport law. If no family passes, the negative
claim is limited to the signatures and two aggregation conventions above; it
does not refute other degree-raising identities or MAX11 representability.

## Deliberately broken controls

- Simultaneously relabeling source coordinates and both added edges by each of
  two fixed nontrivial permutations must preserve every signature, output
  full-atom orbit multiset, and exact semantic vector.
- Relabeling the source pair while leaving the two added edges fixed must be
  detected on a preregistered descriptor whose added endpoints meet the source
  support; the broken output must differ.
- Relabeling only one added edge must likewise differ on a descriptor with
  distinct nonloop added edges.
- Global branch swap must preserve the aggregate output.
- Changing the first nonzero source coefficient by one numerator unit at the
  source common denominator must break any passing identity.
- Deleting one nonzero signature weight and mutating one emitted coefficient
  by one numerator unit at its denominator must each break exact replay.
- Full-atom fibers, signed-`W` fibers, raw counts, and signature counts must
  reconcile exactly. Equality only on hinge coordinates is insufficient;
  every passing claim requires the full linear vector as well.

## Bound evidence

```text
628a836542339a522fde173f13749bad29f150bdff69e7f66aeae26f786e963e  unrestricted_full_semantic_certificate_v1.json
865f7728f26f56953dbe9a3dc8d3c3bbf3c32de4d3c992eb13c73d20bd0f2413  independent_unrestricted_degree4_replay_v1.json
2fa23b8346858e85b4689a36c795ddac6d109ff42535d2238502b3c64117a148  parity_lift_representatives_v1.jsonl.gz
844dba5cf023f68a083261dd1612503c16309297f21ca57e26497f7a6df28d7a  parity_lift_census_v1.json
026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83  certificate_6_2.json
b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be  certificate_7_3.json
68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3  certificate_8_3.json
4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88  certificate_9_4.json
10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4  certificate_10_4.json
1a59b11a0dbb6e4bd91861c001687d1f93000f1bde7340d62f027626e5f77d6f  G-0114/degree_raising_identity_v1.json
d37d8c6fd1c6051676680f8ed5578a618eb0ae1f6612b731cb78327367f6d3f5  G-0114/graph_recurrence_v1.json
```

The G-0114 nulls already reject simpler relation-only and atomwise recurrence
stories. This preregistration tests whether the newly found function-level
certificate exposes a genuinely smaller source-local rule that those earlier
searches could not see.
