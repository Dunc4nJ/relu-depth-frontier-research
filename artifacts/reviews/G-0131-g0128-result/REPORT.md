# G-0131 fresh-context audit of the G-0128 terminal result

- Review completed: `2026-08-31T04:14:42Z`
- Reviewer: `LavenderCreek` (Codex / GPT-5; fresh context, same model family; T1 only)
- Preregistered audit plan: `artifacts/reviews/G-0131-g0128-result/PREREGISTRATION.md`
- Preregistration commit: `0f384376dde61e025e1978c3f5102c951396aef5`
- Preregistration SHA-256: `74594f4a88a840dd144b69d154a7b77445d13b20ff55630e9b5d932253e1d799`
- Delivered result: `artifacts/math/G-0128/full_family_master_result_v2.json`
- Delivered result commit: `b5b73a1b6ffec75ca2c54a31bf2ebb62ec9dbf0c`
- Delivered result SHA-256: `17c4fd5c8890006feaf5b9b9d6dbd542002dfca80e85b27b2dcacec16ebca838`
- Independent checker: `artifacts/reviews/G-0131-g0128-result/replay_member_cleanroom.py`
- Independent checker SHA-256: `41b4b5d0266ea8b3724dd93938013d02829bbf1bf16ba3be2655369014fece7a`
- Machine-readable audit receipt: `artifacts/reviews/G-0131-g0128-result/cleanroom_member_audit_v1.json`
- Audit receipt SHA-256: `0159910b476b1cac9ea0e8f6ad05e16e061036b361efc8b2f5a3a1aa02c09926`

## Verdict

`CONSISTENT_MEMBER` for the exact, frozen 380-row system over the frozen 163,740-record family.

The delivered branch is `FULL_FAMILY_380ROW_EXACT_Q_MEMBER`. An independently written checker reconstructed the row system and target from the frozen manifest inputs, reconstructed all 176 selected columns, parsed and normalized the exact certificate, and obtained zero residual on every row. The terminal certificate contains 132 nonzero terms; 44 of the 176 selected-basis coefficients are zero. The coordinate square has exact rank 176, all 21 reported rank/augmented-rank checkpoints agree, and the final checkpoint is 176/176. The preregistered `+1` mutation of the first nonzero coefficient is rejected.

This is a finite-system consistency verdict and nothing broader. It is at most T1 evidence. It does not establish a global functional identity, settle MAX11, prove representability by an unrestricted two-hidden-layer ReLU network, prove completeness of the frozen family, or create a Lean theorem. A new, separately committed preregistration and independent complete global replay are mandatory before any global language is allowed.

## Custody and blind boundary

The result did not exist when the audit plan was frozen. The audit preregistration was committed and pushed at `0f384376...`; the result commit `b5b73a1...` has that exact commit as its direct parent. The following anchors were checked from Git objects and from the working bytes:

| Object | Frozen anchor | Audit result |
|---|---|---|
| G-0128 scientific source | SHA-256 `cfdb3f3d758d8cc5cc81c8ad9a71f4b9bd5c2001f1ff2f8a646715a4c6ca3da8` | Exact match |
| Source audit | commit `2269652fc689519220ecfcef028519b8ac6283e5` | Exact ancestry/blob binding checked |
| Sealed manifest | commit `3676d68e14815296c9c424837625993ea4d0c3d2`, SHA-256 `79078391da63eb25b09f90f8e9335e614db46bcf69edac5d2ca8386131c3f6ec` | Exact match |
| Result | commit `b5b73a1b6ffec75ca2c54a31bf2ebb62ec9dbf0c`, SHA-256 `17c4fd5c8890006feaf5b9b9d6dbd542002dfca80e85b27b2dcacec16ebca838` | Exact match |
| G-0131 preregistration | commit `0f384376dde61e025e1978c3f5102c951396aef5`, SHA-256 `74594f4a88a840dd144b69d154a7b77445d13b20ff55630e9b5d932253e1d799` | Exact match; direct result parent |

The checker rehashed 46 decision-bearing files at both entry and exit, including every manifest input plus the result, manifest, source, source-audit report, and audit preregistration. Both hash censuses contain 46 files and agree byte-for-byte. It also rejected path escapes, resolved duplicates, noncanonical hash text, malformed integers, boolean-as-integer coercions, duplicate indices, and ambiguous certificate structures.

The checker does not import or execute `full_family_master_v2.py`. It uses independent parsing, row construction, exact integer arithmetic, and FLINT rank/solve calls.

## Exact replay results

| Obligation | Independent result |
|---|---|
| Row census and order | Exactly 380 rows: 301 panel, 11 linear, 4 accumulated hinge, 32 old Batch32, and 32 new Batch32 rows |
| Family census | Exactly 163,740 canonically ordered records |
| Target reconstruction | Reconstructed without using a result-supplied target: the 301-entry panel target, ten linear zeros, `11! = 39,916,800` in the final linear coordinate, and 68 added hinge zeros |
| Selected columns | 176 unique, strictly increasing, in-range family sequences reconstructed from frozen inputs |
| Mathematical support | Exactly 132 nonzero terms, paired canonically with their sequences and integer coefficients |
| Normalization | Positive target scale; gcd of the scale and all nonzero integer coefficients is exactly 1 |
| All-row identity | Residual is exactly zero on rows `0..379`; no sampled substitute |
| Coordinate solve | Independent 176-by-176 exact solve has zero residual and exact rank 176 |
| Rank transcript | All 21 rank/augmented-rank receipts recomputed; first is rank 156 versus augmented rank 157, final is rank 176 versus augmented rank 176 |
| Hostile mutant | Adding 1 to the first nonzero coefficient fails first at row 0 with residual `1269724`; 321 of 380 rows become nonzero |

The exact target scale is

`2289393005496338240468982655090335335732668690900751540287809289663720291914849699943112917639850352050294840444775090516901570116753181129941246082620`.

## Recomputed decision-bearing digests

| Payload and canonical serialization | SHA-256 |
|---|---|
| Target, canonical decimal plus LF per coordinate | `dbd973914dc41f82d6404b21412762e5541f2be580b44d12f3caa5bf371b862d` |
| Selected sequence axis, little-endian u64 | `4584a7f87748b976f86734308efa4abb621e4caab5fa973673faf6aa0a913bc7` |
| Nonzero term support, little-endian u64 | `dda733b9e2f52e0abcd95dd7f98809425e1d9743a9339156ac5d54a29491716d` |
| Integer coefficient vector, canonical decimal plus LF | `2a581d6f48513e2aea9863f9394a5c922c544f8a29f50e25257a024024b96420` |
| Canonical certificate payload JSON | `0be364bf9cfc01a32d2dca4d4348a15cbad8825a1ff63fc62be00b02c8da876c` |
| Canonical rank transcript JSON | `ddb8d0d42edf7e584c375b226d9c676621b4ea9332674fbc8dd6ea4a1455107d` |
| Full 380-by-176 selected basis, row-major little-endian i128 | `3f86d6360219b29812635f110bbabc3ecc85ab1026526a7ed06c20d9b87c6758` |

The independently computed full selected-basis digest exactly matches the result. Additional row-major/column-major control digests in the machine receipt make layout transposition detectable rather than relying on the reported digest alone.

## Finding: support field nomenclature

`NOTE — SUPPORT_SEQUENCES_IS_BASIS_AXIS.` The result's `support_sequences` field equals `selected_sequences` and therefore contains all 176 pivot columns, including 44 positions whose integer coefficients are zero. It is not the mathematical nonzero support despite its name. The canonical `terms` array is the exact 132-term nonzero support, and its sequences are unique, strictly increasing, in range, paired with the corresponding nonzero coefficient positions, and replayed exactly.

This note is not load-bearing for the identity because the certificate exposes the selected axis, full coefficient vector, and canonical nonzero `terms` separately, and the audit validates their exact cross-consistency. Future schemas should rename this field to `selected_basis_sequences` or require it to contain only the nonzero term support.

## Audit attempts and correction history

The final receipt was created exclusively only after the full checker passed. Three earlier checker-development attempts failed before any receipt was written:

1. The first attempt used the SHA-256 of an older G-0123 review in place of the frozen G-0128 round-two source-audit file. The custody mismatch stopped the run. The binding was corrected to `049a0a85bfec5b3ab053208da825a173dbd16302af72004c47f54a906a2ae4ed`.
2. The second attempt incorrectly required the old G-0118 exact-price receipt to carry a selected-prefix digest that belongs to its paired selection receipt. The schema-specific custody check was corrected; no missing digest was invented.
3. The third attempt applied the later 131-term G-0121 candidate to the historical G-0118 residual stream. The checker was corrected to reconstruct the old 102-term G-0118 candidate for the old residual lineage and retain the 131-term candidate only for the new G-0127 lineage.

These were fail-closed audit-implementation errors, not failures of the delivered G-0128 certificate. They are reported to preserve the campaign's full attempt record and to prevent the successful run from being presented without its debugging history.

The checker self-tests also exercised the valid path and required rejection of the coefficient mutant, nonprimitive normalization, malformed canonical decimals, booleans presented as integers, duplicate indices, and a selected-prefix mutation.

## Residual boundaries and required next step

1. The verdict is exact only on the registered 380 coordinates. Finite-row equality is not global functional equality.
2. The verdict is exact only for the frozen 163,740-record family. It is not a family-completeness theorem and says nothing by itself about arbitrary network parameters.
3. The reviewer is fresh-context but from the same model lineage, so this is at most T1 and cannot satisfy a T2 independence requirement.
4. No part of this audit promotes the claim to `REFEREED` or `FORMALIZED`.
5. The only admissible next promotion attempt is a separately preregistered, independent complete global replay that binds the certificate bytes and audit receipt, reconstructs the compiled functional semantics, checks complete domain/chamber coverage and the exact architecture conversion, and rejects its own hostile mutant.

Subject to those boundaries, no blocker, major inconsistency, or failed decision-bearing check remains in the delivered finite 380-row member certificate.
