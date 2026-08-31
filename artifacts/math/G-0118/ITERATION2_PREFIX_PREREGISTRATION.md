# G-0118 iteration 2 — exact prefix CEGIS preregistration

Registered after the iteration-1 global counterexample was fixed and before
implementing or executing the iteration-2 solver.

## Frozen question

Over `Q`, is the MAX11 target in the span of the same frozen family used in
iteration 1: sequences `0..39999` of the canonical G-0117 cache, union the 115
G-0113 panel-basis sequences?

The matrix has exactly 314 rows, in this order:

1. the 301 frozen G-0113 panel rows;
2. all eleven linear coordinates, targeting `(0,...,0,11!)`;
3. hinge direction `(0,0,0,0,0,0,0,0,1,-5,4)`, targeting zero;
4. the independently confirmed iteration-1 counterexample direction
   `(0,0,0,0,0,0,0,0,1,-4,3)`, targeting zero.

The second hinge row is the complete 163,740-column exact price stream in
`iteration2_residual_coordinate_v1.json`.  The old 122-column support is not
frozen: every exact separator is scanned against the entire frozen family and
the first nonzero sequence in canonical order is appended.  At most 25 rank
increases are allowed.

## Decision and controls

- `rank(A) = rank([A|b])` must be followed by an exact all-314-row solve and
  replay.  Emit denominator-cleared integer coefficients and reject a +1
  mutation of the first nonzero coefficient.
- `rank(A) < rank([A|b])` counts as subset nonmembership only if the exact
  separator annihilates every column in the frozen family.
- The runner must refuse input/hash drift, a short or changed cache prefix,
  row-order drift, duplicate selected sequences, non-increasing exact rank,
  overwrite of an existing result, or mutation-control escape.
- Run the solver twice to distinct outputs.  A decision projection excluding
  elapsed time and RSS must match byte-for-byte.

Any member is immediately sent to complete global modular replay over all
labelled permutations.  Two-prime modular zero is only a screen; a positive
claim requires exact integer global replay.  A nonzero residue modulo either
prime rigorously refutes the cleared rational candidate and supplies the next
CEGIS row.

## Bound inputs

```text
d88dc897dbbfd77b98dd4edf2cecfd9696c5760e7c0dd3f2184b626659af7cde  first 192640000 cache bytes
093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8  ../G-0113/panel_solver_input_v1.json
6f3f52bf9709cda495258f760bf51bdde33eea015e0db499cacf04c28eabb85e  ../G-0113/panel_scan_v1.json
615e264dd64e43c8374131e6934e9728ee4c043a8b15f19ed50ec8d676fe1393  ../G-0113/panel_retained_columns_v1.json
c9acf62ea84d7e3d0405f2a5f778f431f8c3a1b16c8b9aefa453b62cfc929071  ../G-0117/fresh_q_cegis_iteration1_coordinate_v1.json
41255b1176ca95ac8f2d43e35c8396266cf9d2c71fcae77c14dffb54ffc58a3f  iteration2_residual_coordinate_v1.json
ee422e6e36085e26ddd83a75f8901c6a6efbe3fd2a99e80e280f9449d0ed8281  ../G-0117/fresh_q_cegis_exact.py
bad55cb45134cfdab3be86b3d3c676807acb402d69b6d37d0af59767152e531c  prefix_exact_cegis_v1.json
ee7ccc77c34454845b59e709507b901d814263242d8ff9b66e4257f06e0e90d4  prefix_global_modular_replay_v1.json
```

## Claim boundary

Success is exact membership on these 314 rows in this 40,000-plus-basis
subset.  It is not a global identity, not full 163,740-family membership, not
family completeness, and not an unrestricted two-hidden-layer MAX11 theorem.
Failure is nonmembership only in this frozen subset.  The global target remains
unchanged.
