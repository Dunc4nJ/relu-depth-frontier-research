# G-0102 — clean-room hostile audit of the G-0099 lower gate

## Verdict: PASS, with a narrow boundary

The frozen G-0099 lower-dimensional potency result is correct for the exact
claim it makes.  There exists a rational coefficient vector in the complete
compressed degree-three pairwise Rueß family for `MAX7` whose imposed
leaf/opposite-colour-edge incidence image equals the dominant two-component
forest projection of the public `MAX6` certificate.

This audit does **not** show that the incidence operator is induced by a
functional restriction from `MAX7` to `MAX6`.  It therefore supplies no
`MAX11` identity, no global-wall certificate, no evidence that the analogous
joint `n=10 -> n=11` semantic system is feasible, and no unrestricted ReLU
lower bound.

The reviewed frozen inputs were:

- `MANIFEST.json`: `508d4cec92e18da90f889bfbc1e4e34f73db5d56ee66bc0f65d21ee0a1b87121`
- `leaf_bridge_n6_n7.py`: `88ba42e8a2955bc3f333fe44b034c8db6a41174b9e17fe481ba0ba353ef175db`
- `leaf_bridge_complete_v1.json`: `4ba88a474591e08dc28a7e17d8fe9ea9c12c03c065b578777b2fe22ad3888885`

All were unchanged between the start and end of the final replay and agree
with the frozen manifest.

## Independent reconstruction

The auditor imported no G-0099 or G-0090 module.

1. Burnside's lemma over `S7 × {global sign swap}` independently gives the
   signed loop-inclusive multigraph orbit counts
   `1, 5, 106, 2897` for masses `0,1,2,3`.  Every one of the 3,009 selected
   G-0038 records was independently canonicalized, was cancellation-reduced,
   and had a distinct key.  Adding the second common-edge basis atom gives
   exactly 3,010 compressed columns.
2. The audit independently reconstructed 53 balanced bicoloured tree orbits
   and 11 balanced two-component forest orbits.  Their orbit sizes reconcile
   to 168,070 labelled trees and 3,240 labelled forests.
3. Direct deletion and reverse attachment were separately enumerated.  All
   234 nonzero incidences satisfy

   `N_T r(T,F) = 7 N_F q(F,T)`, equivalently
   `a_F r(T,F) = a_T q(F,T)`.

   This confirms the full-permutation-sum coefficient convention
   `D(F,T) = 7 r(T,F)`.
4. Every one of the 3,010 functional columns was rebuilt by literally
   enumerating all `7!` vertex orders and directly forming the two branch
   linear forms.  This is method-disjoint from the producer's subset-DP
   semantic kernel.

## Exact results

- Reconstructed augmented matrix: `648 × 3010`
  (`630` hinge rows, `7` linear rows, `11` incidence rows).
- Exact rank over `Q`: `327`; exact nullity: `2683`.
- Rank and augmented rank are both `327` modulo each of
  `1000003`, `1000033`, and `1000081`.
- The delivered 113-term sparse rational vector replays exactly on all 648
  rows.
- Matrix, target, direction-list, descriptor-list, sparse-solution, pivot-row,
  and pivot-column hashes all match the frozen producer receipts.
- Direct evaluation of the represented function, bypassing the normal-form
  rows, equals `MAX7` on four integer profiles including tied and zero cases.
- The public `MAX6` and `MAX7` certificates independently replay exactly by
  literal permutation enumeration.

The public `MAX7` certificate itself has zero balanced-tree projection, so
that particular vector fails the desired transfer.  This is not an
existence obstruction: the constrained matrix has nullity 2,683, and the
independently replayed 113-term vector is a different solution.  Certificate
nonuniqueness therefore does not invalidate the positive potency gate.

The 648 rows are complete for this finite functional claim.  They contain
every primitive hinge direction occurring in all 3,010 atoms, together with
all seven linear coordinates and all eleven incidence constraints.  Each
retained primitive direction defines a distinct bend hyperplane meeting the
interior of the sorted cone, so exact cancellation of these coordinates is
necessary and sufficient within the dictionary.

## Potency controls

All planted defects were rejected:

- reversing the sign in `rho(u) = rho(-u) + u` created six nonzero semantic
  residual coordinates;
- incrementing one supported incidence count broke both the orbit double
  count and the constrained replay (residual `55/6`);
- adding one to the first reported coefficient created six residual rows;
- incrementing the target's final linear coefficient produced residual `-1`.

## Reproduction

```bash
.venv/bin/python artifacts/math/G-0102/audit_g0099_cleanroom.py
```

The final run completed in 183.813 seconds and wrote
`cleanroom_audit_v1.json`.  At creation, its SHA-256 was
`dbc043aa9954f1cf76ae6ba28f8925a1ef687943a539a6c48048baafe7441d33`;
the auditor source SHA-256 was
`7ca056bddc7695222114e61b87c5e726bb96bc7803847c69baf8f57191166169`.

This is a fresh-context, same-model-family clean-room replay (T1), not a T2
referee result.
