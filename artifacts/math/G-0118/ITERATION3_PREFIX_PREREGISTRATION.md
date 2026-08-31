# G-0118 iteration 3 — accumulated exact prefix CEGIS preregistration

Registered after the complete iteration-2 global replay exposed the direction
below and after that row was priced, but before implementing or executing the
accumulated-row solver.

## Frozen question

Over `Q`, is the MAX11 target in the span of sequences `0..39999` of the
canonical cache, union the same 115 G-0113 panel-basis sequences, on exactly
315 rows in this order?

1. the 301 frozen G-0113 panel rows;
2. all eleven linear coordinates, targeting `(0,...,0,11!)`;
3. hinge `(0,0,0,0,0,0,0,0,1,-5,4)`, target zero;
4. hinge `(0,0,0,0,0,0,0,0,1,-4,3)`, target zero;
5. hinge `(0,0,0,0,0,0,0,0,1,-3,2)`, target zero.

The third hinge is the first canonical nonzero direction in the complete
iteration-2 replay.  For the cleared 100-term candidate its exact residual is

```text
-6682222336261653691138141713369607563179755071274345059365269959075182620102873087225424810312518464.
```

Its reductions modulo `1,000,000,007` and `1,000,000,009` are `272554640`
and `538760177`, matching the global screen.  This nonzero integer refutes the
iteration-2 candidate and fixes the new row independently of any later fit.

## Frozen solver contract

`iteration3_prefix_manifest_v1.json` is the only scientific manifest.  A new
generic accumulated-row runner must hash-check every named input, require the
same linear stream in all coordinate artifacts, append the hinge streams in
manifest order, start from the 115-column panel basis, and scan every exact
separator against the complete frozen family in canonical sequence order.  It
may add at most 32 rank-increasing columns.  The old 123 support columns are
not frozen and may not replace the complete family scan.

Membership requires an exact all-315-row solve and replay, denominator-cleared
integer coefficients, and rejection of a +1 mutation of the first nonzero
coefficient.  Nonmembership is allowed only when an exact separator annihilates
every frozen-family column.  Run twice to distinct outputs; the full decision
projection excluding wall time and RSS must match.

Any member goes immediately to complete global two-prime replay over every
labelled permutation.  Modular zero is only a screen; exact BigInt global replay
is required for a positive identity.  A nonzero modular residue rigorously
refutes the cleared candidate and supplies the next row.

## Bound digests

```text
d88dc897dbbfd77b98dd4edf2cecfd9696c5760e7c0dd3f2184b626659af7cde  first 192640000 cache bytes
093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8  ../G-0113/panel_solver_input_v1.json
6f3f52bf9709cda495258f760bf51bdde33eea015e0db499cacf04c28eabb85e  ../G-0113/panel_scan_v1.json
615e264dd64e43c8374131e6934e9728ee4c043a8b15f19ed50ec8d676fe1393  ../G-0113/panel_retained_columns_v1.json
ee422e6e36085e26ddd83a75f8901c6a6efbe3fd2a99e80e280f9449d0ed8281  ../G-0117/fresh_q_cegis_exact.py
c9acf62ea84d7e3d0405f2a5f778f431f8c3a1b16c8b9aefa453b62cfc929071  ../G-0117/fresh_q_cegis_iteration1_coordinate_v1.json
41255b1176ca95ac8f2d43e35c8396266cf9d2c71fcae77c14dffb54ffc58a3f  iteration2_residual_coordinate_v1.json
58139181228fc2400298f400f1b80c083b72747f8d1ba3830fe4f3ee8b787f48  iteration3_residual_coordinate_v1.json
1d3fd50449fd63c0f8d795cb4d1428fd7a89ef97bcd709c01c579115ea8ccb4b  prefix_exact_cegis_iteration2_v1.json
```

## Consumer and no-claim boundary

The manifest is consumed by the exact solver and independent replay; it gates
input/row-order drift.  The observed defect class is two successive finite
members failing globally on omitted hinge rows.  It stops being active input
when this exact candidate is globally dispositioned and remains only as an
immutable replay receipt.

Success is exact membership on 315 rows in this fixed subset—not a global
identity, full-family decision, family-completeness theorem, or unrestricted
two-hidden-layer MAX11 result.  Failure is only subset nonmembership.
