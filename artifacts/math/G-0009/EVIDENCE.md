# G-0009 artifact-local evidence ledger

This table records claims internal to G-0009.  It is not the campaign
`CLAIMS_LEDGER.md`, and nothing here constitutes claim promotion.

| ID | Claim | Standing | Direct evidence | Main falsifier or boundary |
|---|---|---|---|---|
| G9-C1 | `Phi_N(A+e,B+e)=Phi_N(A,B)+2(N-2)!F_2^(N)` for any fixed loopless `e`. | proved algebraically; exact small-`n` check | `lift_identity_attestation.json`; `scripts/lift_identity.py` | Independent proof review or formalization could expose a convention/counting error. |
| G9-C2 | The generated cross list has 9,200 raw items and 3,615 classes under vertex relabeling/global color swap; all unions are full-support beta=0 trees. | exact generated-list computation | `cross_component_classes.json`; `scripts/cross_component_search.py` | A second enumerator could find a generator or quotient defect. Completeness is only relative to the 252 pinned bases. |
| G9-C3 | The generated beta2-common list has 6,740 raw items and 4,916 graph classes. | exact generated-list computation | `beta2_common_classes.json`; `scripts/enumerate_beta2_common.py` | Same single-route and relative-completeness limits as G9-C2. |
| G9-C4 | On the 886-row joint system, adding all 3,615 cross columns to the 9,804 same-component columns changes exact Q-rank by zero: `694 -> 694`. | exact finite-system computation | `cross_joint_rank_report_exact.json` | Says nothing about unmeasured hinge rows or a generator/evaluator bug. |
| G9-C5 | On the same system, adding all 4,916 beta2 columns to the same+cross baseline changes exact Q-rank by zero: `694 -> 694`. | exact finite-system computation | `beta2_joint_rank_report_exact.json` | Same finite restriction and shared-lineage limits as G9-C4. |
| G9-C6 | Every cross column and every beta2 column lies in the same-component baseline span on the 886 rows. | exact corollary of G9-C4/C5 because baseline columns are included in each union | both joint rank reports | Must never be restated as global functional redundancy. |
| G9-C7 | MAX11 is outside the cross-only finite span; a four-row dual has target pairing `5`. | exact rational dual | `dual_witness_verification.json`; `scripts/verify_duals.py` | Excludes only the named cross family. |
| G9-C8 | MAX11 is outside the beta2-only finite span; a two-row dual has target pairing `1/5`. | exact rational dual | same files as G9-C7 | Excludes only the named beta2 family. |
| G9-C9 | The 4,916 beta2 graph classes collapse globally to at most 252 source-indexed functions; on the 886 rows exactly 252 columns remain. | global algebra for within-source equality; exact finite computation for distinct count | `beta2_functional_collapse.json`; common-edge identity | Pairwise distinctness of source functions is only finite-system evidence. |
| G9-N1 | Either tested family solves MAX11 globally. | **not claimed** | no global solution/residual exists | Finite target membership is insufficient. |
| G9-N2 | No two-hidden-layer ReLU network represents MAX11. | **not claimed** | these are two restricted atom slices | Would require a universal lower bound or complete ansatz theorem. |

## Evidence-family audit

- Arithmetic: integer matrices and exact rational `python-flint` replay.
- Enumeration: one NetworkX typed-incidence/VF2 implementation.
- Atom evaluation: inherited G-0006/G-0008 lineage.
- Holdout: disjoint from the earlier selected rows but adaptively derived from
  their residual.
- Review tier before an independent audit: same-lineage computational
  evidence only.

