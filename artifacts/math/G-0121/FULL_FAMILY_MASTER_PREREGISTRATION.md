# G-0121 preregistration — reopened exact-Q full-family Batch32 master

## Timing and question

Frozen on 2026-08-31 after the G-0117 panel cache completed, but before either
future file below existed or was inspected:

```text
artifacts/math/G-0118/iteration4_batch32_global_modular_replay_v1.json
artifacts/math/G-0118/iteration4_batch32_exact_prices_v1.json
```

Question: after adjoining the deterministically selected Batch32 rows, is the
fixed MAX11 target in the rational column span of **all 163,740 records** of
the already frozen family?  The two admissible outcomes are an exact-Q member
of that finite family or an exact integer separator annihilating every one of
those 163,740 columns.  Neither outcome establishes completeness of the
family, an unrestricted two-hidden-layer lower bound, or a MAX11 theorem.

## Frozen pre-Batch32 inputs

```text
093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8  artifacts/math/G-0113/panel_solver_input_v1.json
6f3f52bf9709cda495258f760bf51bdde33eea015e0db499cacf04c28eabb85e  artifacts/math/G-0113/panel_scan_v1.json
615e264dd64e43c8374131e6934e9728ee4c043a8b15f19ed50ec8d676fe1393  artifacts/math/G-0113/panel_retained_columns_v1.json
0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c  artifacts/math/G-0111/dual_rows_v1.json
e546f65429c33012c638b0be3b37cf9af4228070c00136e05914e701436e44bf  artifacts/math/G-0117/full_family_cache_manifest_v1.json
da045a6fc004afeb6c9b67c8fc093a191ed3e9c515bc8e97901a6e64cb125c5b  artifacts/math/G-0117/full_family_cache_v1.i128le
ac6cecfe4702866d8177dbeefd81b71a3933578a6f88b1f9cbcbc12f0cfb1022  artifacts/math/G-0117/FULL_FAMILY_CEGIS_PREREGISTRATION.md
39de1eb61aaee37a24c8a45d55cbc5fd6f27c7b68d506f8757f352881a6e0c17  artifacts/math/G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md
c9acf62ea84d7e3d0405f2a5f778f431f8c3a1b16c8b9aefa453b62cfc929071  artifacts/math/G-0117/fresh_q_cegis_iteration1_coordinate_v1.json
41255b1176ca95ac8f2d43e35c8396266cf9d2c71fcae77c14dffb54ffc58a3f  artifacts/math/G-0118/iteration2_residual_coordinate_v1.json
58139181228fc2400298f400f1b80c083b72747f8d1ba3830fe4f3ee8b787f48  artifacts/math/G-0118/iteration3_residual_coordinate_v1.json
862dbbbd6c2bee9424b8faf4e8cb0a2e7b4c76c94ef0a6bd78bc3e14b90258cb  artifacts/math/G-0118/iteration4_residual_coordinate_v1.json
728c06bd02f03367fbfa9f50c0353dc74b708a6ef576520cc0eaa72e2e472e1b  artifacts/math/G-0118/prefix_exact_cegis_iteration4_v1.json
f29c7095a60ab945293bb1b182afde372405e3cb45c3509080f766aebf46911f  artifacts/math/G-0118/prefix_exact_cegis_iteration4_recheck_v1.json
54a329587786c8824e8eede13a6165983ecc64c27a7f758be9676583bd283feb  artifacts/math/G-0118/BATCH32_ITERATION4_PREREGISTRATION.md
```

The canonical panel cache has 163,740 sequence-major columns, 301 signed-i128
entries per column, little-endian layout, and exactly 788,571,840 bytes.  A
consumer must independently recompute its SHA-256, validate the manifest's
dimensions/layout/claim boundary, and verify its transitive bindings to the
panel input, row document, evaluator, evaluator gate, corrected scan, producer,
and preregistration.  File size or the cache producer's own verdict alone is
not a sufficient audit.

The accumulated hinge directions, in this order, are

```text
(0,0,0,0,0,0,0,0,1,-5,4)
(0,0,0,0,0,0,0,0,1,-4,3)
(0,0,0,0,0,0,0,0,1,-3,2)
(0,0,0,0,0,0,0,0,1,-2,1)
```

Each accumulated coordinate document must contain exactly 163,740 hinge
prices, exactly 163,740 ordered 11-vectors, its stated direction, and valid
signed-i64 stream digests.  All four linear streams must agree byte-for-byte.

## Future-result custody and scientific manifest

No scientific branch is chosen from the future modular residues.  A mechanical
manifest builder may run only after both future receipts are sealed.  It must
validate them and create, with exclusive-create semantics,

```text
artifacts/math/G-0121/full_family_master_manifest_v1.json
```

The manifest schema is `max11-g0121-full-family-master-manifest-v1`.  It binds
the exact path and SHA-256 of every frozen input above, both future receipts,
this preregistration, and the solver.  Paths are workspace-relative and must
resolve inside the workspace; duplicates, symlinks escaping the workspace,
missing files, malformed lowercase SHA-256 strings, and hash drift are fatal.

The global replay receipt must have the frozen G-0118 schema, candidate,
primes, `K = 32`, complete census, accumulated-row zero checks, strict signed
lexicographic selected order, selected-prefix digest, and successful +1
mutant.  This branch requires a nonempty selected prefix.  The exact-price
receipt must bind that replay receipt and reproduce its directions and modular
residues in order.  It must contain one direction-major signed-i64 hinge row
of length 163,740 per selected direction plus 163,740 ordered signed-i64
linear 11-vectors.  Per-row, aggregate hinge, and linear stream hashes are
recomputed from values, not trusted as labels.  Reordering any row, direction,
residue pair, record, or linear coordinate is fatal.

## Exact row system and deterministic rank filter

Columns have, in order:

1. the 301 cached panel entries;
2. the shared 11 linear entries;
3. accumulated hinge rows `d1,d2,d3,d4`; and
4. the Batch32 rows in the exact selected-prefix order.

The unscaled rational target is the 301-entry panel target, then ten zeros and
`11!` in the last linear coordinate, then zero on every hinge row.  A prior
certificate's denominator-cleared `target_scale` is never reused.

The 316 pre-Batch32 rows remain the frozen accumulated system.  Process new
Batch32 rows in receipt order.  A new row may be discarded only after an exact
rational dependency against the current accumulated rows has been verified on
all 163,740 family columns **and on the target coordinate**.  Restricted-column
rank increase proves independence.  Apparent restricted dependence triggers
an exact relation and a sequence-order scan: the first violating column is
added to the rank-test coordinates and the test repeats.  No modular rank,
hash equality, or restricted rank may certify dependence.  Record every kept
and discarded row and every pivot-enrichment column.

## Reopened exact-Q restricted master

Seed the column set with the common ordered 115-sequence panel basis recorded
by both primes in the frozen panel scan.  Thereafter, at every iteration:

1. construct the full retained-row matrix on the selected family columns;
2. compute exact ranks over `Q` for the matrix and its target augmentation;
3. if the target is in the restricted span, derive an exact-Q coefficient
   vector and replay **every retained row** exactly;
4. otherwise derive a primitive exact integer left separator with nonzero
   target pairing;
5. stream every family sequence `0..163739` in order and price the separator
   against the complete column;
6. append the first exact nonzero column and repeat; or, only if every one of
   the 163,740 prices is exactly zero, emit finite-family nonmembership.

Every appended column must strictly increase exact column rank.  The scan may
be optimized by omitting zero separator coordinates, but it may not skip,
sample, reorder, modular-screen away, or restrict family columns.  A modular
calculation is never an exact-Q obstruction.

On membership, clear denominators only after the exact solve, remove zero
terms, divide the integer coefficient vector and target scale by their common
gcd, and normalize the scale positive.  Replay the denominator-cleared
identity on every retained row.  Add one to the first nonzero coefficient and
require the mutant to fail.  On nonmembership, normalize the primitive
separator by gcd and first-nonzero sign, rescan every family column, require a
nonzero target pairing, and require a one-entry separator mutant to fail the
annihilation or pairing check.

## Frozen hostile controls

The solver and manifest builder must provide executable self-tests that reject:

- a false nonmembership created by freezing old support when an omitted column
  violates the separator;
- a row that appears dependent on seed columns but differs on an omitted
  family column;
- a +1 member coefficient mutant and a +1 separator mutant;
- reordered Batch32 directions or prices, a changed record order, and a stream
  digest mutation;
- an input-hash mutation, path escape, output overwrite, ragged matrix, stale
  solver source, stale manifest, and cache truncation.

All result writes use `O_EXCL`; source, manifest, and cache hashes are checked
again before the write.  Aborted trials write no scientific result.  The final
receipt reports wall time, peak RSS, every exact rank/augmented-rank trial,
every all-column scan census, and the finite-family claim boundary verbatim.

## Outcome boundary

`FULL_FAMILY_EXACT_Q_MEMBER` means only that the frozen target is represented
by the frozen 163,740 records on the accumulated finite row system.  It is a
candidate for a separate binding-clean global exact replay, not a global
identity.  `FULL_FAMILY_EXACT_Q_NONMEMBER` means only exact nonmembership in
this frozen family on these rows; it is not an unrestricted lower bound.
