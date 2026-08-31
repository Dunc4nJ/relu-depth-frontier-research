# G-0125 preregistration — clean-room audit of the G-0121 finite member

## Timing, object, and contamination boundary

Frozen on 2026-08-31 before inspecting the coefficient/support payload of the
claimed member.  At freeze time the only outcome information supplied to this
reviewer was:

```text
source commit: 492462854538c563f57cbf77f87283305e18a36e
result path: artifacts/math/G-0121/full_family_master_result_v1.json
result SHA-256: 53bc7d8894a3552c226ca64f51bf7b369ce1d7c71f532241b14271964abc1036
reported branch: exact member of the frozen 163,740-column family on 348 rows
reported number of exact rank trials: 42
```

The reviewer read the earlier G-0121 preregistration and manifest, including
their frozen input paths, dimensions, row order, seed sequence list, and
claimed boundary.  The reviewer did not inspect the result's coefficients,
support list, rank-trial payload, or selected-basis digest before freezing this
plan.

The clean-room checker will not import, execute, or copy algorithms from
`artifacts/math/G-0123/full_family_master.py`.  It will not execute either
global-replay producer.  It may parse their already sealed receipts solely as
frozen row data, and it may use independently written standard-library parsing
plus `python-flint` exact integer/rational linear algebra.

## Exact bounded question

Given the committed G-0121 result and the frozen inputs named below, does the
result encode a denominator-cleared exact identity

```text
sum_j integer_coefficient_j * family_column_j
    = positive_target_scale * frozen_target
```

on all 348 registered rows, with canonical support/order, primitive positive
normalization, a valid selected-basis transcript, and exact rank claims?

A `CONSISTENT` outcome supports only this 348-row, 163,740-column finite-family
certificate.  It is not a global functional identity, not a two-hidden-layer
ReLU network, not family completeness, not MAX11 settlement, and not a Lean
theorem.  This same-lineage fresh-context review is at most T1.

## Frozen inputs

The audit binds and rehashes at least these load-bearing bytes:

```text
53bc7d8894a3552c226ca64f51bf7b369ce1d7c71f532241b14271964abc1036  artifacts/math/G-0121/full_family_master_result_v1.json
9234415af8719ea0f46eaf7952d76cab006afe44e4d7e111813fde61e4a5032c  artifacts/math/G-0121/full_family_master_manifest_v1.json
e7e2f6de986d839aef8614ae81d91357b34bccfb5b9ec065fd8aa5bd1a689952  artifacts/math/G-0121/FULL_FAMILY_MASTER_PREREGISTRATION.md
da045a6fc004afeb6c9b67c8fc093a191ed3e9c515bc8e97901a6e64cb125c5b  artifacts/math/G-0117/full_family_cache_v1.i128le
e546f65429c33012c638b0be3b37cf9af4228070c00136e05914e701436e44bf  artifacts/math/G-0117/full_family_cache_manifest_v1.json
c9acf62ea84d7e3d0405f2a5f778f431f8c3a1b16c8b9aefa453b62cfc929071  artifacts/math/G-0117/fresh_q_cegis_iteration1_coordinate_v1.json
41255b1176ca95ac8f2d43e35c8396266cf9d2c71fcae77c14dffb54ffc58a3f  artifacts/math/G-0118/iteration2_residual_coordinate_v1.json
58139181228fc2400298f400f1b80c083b72747f8d1ba3830fe4f3ee8b787f48  artifacts/math/G-0118/iteration3_residual_coordinate_v1.json
862dbbbd6c2bee9424b8faf4e8cb0a2e7b4c76c94ef0a6bd78bc3e14b90258cb  artifacts/math/G-0118/iteration4_residual_coordinate_v1.json
349e63a7a2f254a2b0d4c05a4ce4c088afa7ff859675876e2b8c3bac05b6547b  artifacts/math/G-0118/iteration4_batch32_exact_prices_v1.json
c402c0c9e89c2d8a95fc8b40c44346f9eaeae3c2ade5a7662d97cda04680ad80  artifacts/math/G-0118/iteration4_batch32_global_modular_replay_v1.json
093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8  artifacts/math/G-0113/panel_solver_input_v1.json
6f3f52bf9709cda495258f760bf51bdde33eea015e0db499cacf04c28eabb85e  artifacts/math/G-0113/panel_scan_v1.json
615e264dd64e43c8374131e6934e9728ee4c043a8b15f19ed50ec8d676fe1393  artifacts/math/G-0113/panel_retained_columns_v1.json
```

Every manifest-bound input actually consumed by the audit must also match the
manifest's lowercase SHA-256.  A missing file, path escape, symlink escape,
duplicate sequence, malformed integer, dimension mismatch, or hash drift is a
hard failure.

## Independent reconstruction

The checker will reconstruct each requested family column in this exact order:

1. 301 signed little-endian i128 panel entries read directly from the frozen
   sequence-major cache;
2. the ordered 11 signed integer linear entries, independently checked to
   agree across all four accumulated-coordinate documents and the Batch32
   exact-price receipt;
3. one hinge price from each of the four accumulated-coordinate documents in
   their preregistered direction order; and
4. 32 hinge prices from the Batch32 exact-price receipt in the selected-prefix
   direction order, cross-checked against the modular replay's selected order.

The target will be reconstructed without consulting result coefficients: the
301-entry panel target from the frozen panel input, then ten zero linear
coordinates and `11!` in the final linear coordinate, then 36 zero hinge
coordinates.  The reconstructed target must have length 348.

## Certificate checks

The audit will fail closed unless all of the following hold:

- the result schema/outcome names the exact-member branch and binds the frozen
  manifest/result hashes;
- support indices are unique, in canonical increasing family order, within
  `[0,163740)`, and agree exactly with the nonzero positions in the reported
  coefficient representation;
- coefficient/support pairing has no hidden zero terms and all integers are
  canonical decimal integers;
- `target_scale > 0`, and the gcd of target scale and every nonzero integer
  coefficient is one;
- independently reconstructed 348-vectors satisfy the denominator-cleared
  identity exactly, coordinate by coordinate;
- the first-nonzero-coefficient `+1` mutant fails, with the first mismatch row
  recorded;
- the 115 frozen seed sequences and every appended sequence are in the
  declared order, unique, and in range;
- the selected-basis digest is recomputed from the independently parsed
  sequence transcript using the result's explicitly documented canonical
  serialization, and matches the sealed result;
- all 42 reported exact rank trials can be independently reconstructed from
  their stated selected sequences: exact `rank(A)` and `rank([A|target])`
  match, every appended column strictly increases exact column rank, and the
  final trial has equal matrix/augmented ranks;
- the final coefficient vector independently solves the final selected
  system, rather than merely the full 348-row replay.

If the selected-basis digest serialization is not specified unambiguously in
the result or committed preregistration, the audit records that field as
`CANNOT_VERIFY` rather than guessing.  If exact rank reproduction is
computationally infeasible within the local ceiling, every completed trial and
the first omitted trial are reported; no sampled subset is described as all
42.

## Controls and outputs

The checker will have a deterministic `--self-test` with at least: a valid toy
integer identity, a coefficient `+1` failure, a nonprimitive normalization
failure, support reorder/duplication failures, a ragged-column failure, and an
augmented-rank mismatch.  Scientific output uses exclusive-create semantics.

Frozen output paths:

```text
artifacts/reviews/G-0121-full-family-member/replay_member_cleanroom.py
artifacts/reviews/G-0121-full-family-member/cleanroom_receipt_v1.json
artifacts/reviews/G-0121-full-family-member/REPORT.md
```

Admissible verdicts are `CONSISTENT`, `INCONSISTENT`, or `CANNOT_VERIFY`.
Byte-identical reproduction is not correctness, and even full consistency
does not cross the explicit finite-row/global boundary.
