# G-0118 iteration 4 — accumulated exact prefix CEGIS preregistration

Registered after complete iteration-3 replay exposed and exact pricing fixed
the fourth hinge row, but before solving iteration 4.

## Frozen question

Over `Q`, is the MAX11 target in the same 40,000-plus-panel-basis family on
316 rows: the 301 G-0113 panel rows, all eleven linear rows targeting
`(0,...,0,11!)`, and these four zero-target hinges in order?

```text
(0,0,0,0,0,0,0,0,1,-5,4)
(0,0,0,0,0,0,0,0,1,-4,3)
(0,0,0,0,0,0,0,0,1,-3,2)
(0,0,0,0,0,0,0,0,1,-2,1)
```

The last row is the first canonical nonzero direction in the complete
iteration-3 global replay.  Its exact cleared residual on that 101-term
candidate is

```text
-2569037380781138550866227164032447962596830880486090488375885126283130833555936658580160857076351162672,
```

with residues `737152734` and `959268884` modulo the two frozen primes.  This
nonzero integer fixes the row independently of the next fit.

`iteration4_prefix_manifest_v1.json` freezes every input.  The unchanged
accumulated runner must start from the 115 panel-basis columns, scan each exact
separator across the complete frozen family in sequence order, and permit at
most 32 rank increases.  The prior 124-column support is not a substitute for
that scan.

Membership requires exact all-316-row solve/replay, cleared integer
coefficients, and a rejected +1 coefficient mutant.  Nonmembership requires an
exact separator annihilating every subset column.  Two distinct runs must have
identical decision projections after deleting time and RSS.

Any member goes to complete global two-prime replay.  Modular zero is only a
screen; an exact BigInt global replay is required for a positive identity.

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
862dbbbd6c2bee9424b8faf4e8cb0a2e7b4c76c94ef0a6bd78bc3e14b90258cb  iteration4_residual_coordinate_v1.json
cf14304010b29fea6730550f1b3a72b136ce8e617a7d3a383a270853f461010c  prefix_exact_cegis_iteration3_v1.json
8f364f384f070d5e061d8f61afe8374e8af5f5cac268fe3998d5bbf3c187d370  prefix_exact_cegis_accumulated.py
```

## Consumer and no-claim

The manifest is consumed by the solver and independent replay; it gates the
observed finite/global row-omission defect and retires as active input once
iteration 4 is globally dispositioned.  A member is only exact 316-row subset
membership—not a global identity, full-family decision, completeness result,
or unrestricted MAX11 theorem.  A nonmember is only subset nonmembership.
