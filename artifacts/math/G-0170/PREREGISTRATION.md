# G-0170: first-fresh-direction obstruction gate

## Question

Does the first exact nonzero residual direction of the frozen G-0164 member add
one row of rank to the frozen 540-row, 163,740-column family matrix, or is it
already in that matrix's row span?

The frozen direction is
`[0,0,0,0,0,0,0,1,-3,-2,4]`.  Its target hinge coefficient is zero.  The
G-0164 replay reports the candidate coefficient
`379858988519969425640880275968838894169747154467569436493787649506373736737950413636778164001256433026417251950602296924512458629249878005260933604660006607265165930153855350438792638052520802532699547678484433662808677221428571717301614719241683614296777110430993345898281411351171169404068928008487414400335604088388036643010391694264177960466072190898850647789138420761349640684800`.

## Frozen inputs

- Panel records: `artifacts/math/G-0113/panel_solver_input_v1.json`,
  SHA-256 `093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8`.
- Coordinate producer source: `artifacts/math/G-0117/src/main.rs`,
  SHA-256 `b8f079d08f1100108433428bc5fe4daa40edf5e90757736013fa07002c1fab0c`.
- Exact kernel: `artifacts/math/G-0117/src/lib.rs`,
  SHA-256 `2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6`.
- Coordinate executable:
  `artifacts/math/G-0117/target/release/g0117-global-coordinate-pricer`,
  SHA-256 `66bb82580f8540087a9e0476043390694002f63593ba4bc803346a6f07ae3a04`.
- Frozen finite member:
  `artifacts/math/G-0164/all128_direct_basis_member_v1.json`,
  SHA-256 `bc4d1c58587aef6cd3b555b166ba7ec8e0f365cb0089cfd889a235e8f2e20119`.
- Frozen global result:
  `artifacts/math/G-0164/all128_global_replay_v1.json`,
  SHA-256 `c04e39834de079b7ea89884cedc23956aaaf585c6ac2f3d79241395c943dba6a`.

## Exact price and bridge

Run the frozen G-0117 executable once on
`first_fresh_direction_query_v1.json`, refusing overwrite.  Require all
163,740 signed `i64` coordinates, their digest, exact source/kernel/executable
bindings, and an end-to-end dot product with the 304 frozen primitive-integer
member coefficients.  The dot product must equal the frozen residual above.
Any mismatch is `PRICE_OR_BRIDGE_FAIL` and stops this gate.

## Rank-total decision rule

Let `A` be the certified rank-349 G-0164 540-row full-family matrix and let
`h` be the new exact row.

- `FIRST_ROW_INDEPENDENT_CONTINUE_BATCH128`: certify
  `rank_Q([A;h])=350` by an exact nonzero 350-by-350 minor and exact replay.
- `FIRST_ROW_DEPENDENT_FAMILY_OBSTRUCTION`: certify
  `rank_Q([A;h])=349`, an exact row relation spanning all 163,740 columns,
  and nonzero evaluation of that relation on the augmented target.  Only this
  branch proves incompatibility of the frozen finite family with this necessary
  global row.

Modular ranks may propose work but never establish dependence.  A modular
rank-350 minor can only nominate the exact minor to certify.  Neither branch
settles unrestricted two-hidden-layer ReLU representation, minimality, an
all-n theorem, novelty, publication, formalization, or Lean.
