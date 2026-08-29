# G-0016 final adversarial referee report on G-0015

<!-- G0016_MACHINE_REVIEW_V1 {"claim_boundary":"exact nonmembership for the registered 16000-raw/9804-class same-component family union the 6740 named beta2-common edge-multiset lifts","schema":"max11-bounded-theorem-review-v1","semantic_report_sha256":"581a8d9b5a1cd28f1ee2896e119a262977084369d32550ca8523fd205596ec71","subject_sha256":"852fa1b15ee06c7f04628bded536cd7e29d0533d5740eb96c11fbf4408dc4d9a","t2_or_human_review_obtained":false,"tier":"same-family T1","verdict":"PASS_BOUNDED_PROOF_LOGIC"} -->

**Subject:** `artifacts/math/G-0015/THEOREM_DRAFT.md`, SHA-256
`852fa1b15ee06c7f04628bded536cd7e29d0533d5740eb96c11fbf4408dc4d9a`.

**Evidence rechecked:** G-0012 exact-audit SHA-256
`9c26c0e6329804ee2a87ec9ef6b86cd935c91551ca503a97409368f41ac3676a`,
G-0014 semantic-audit SHA-256
`581a8d9b5a1cd28f1ee2896e119a262977084369d32550ca8523fd205596ec71`,
and G-0018 beta2-mapping-audit SHA-256
`88ba04742803439713e3a9fd7c01171c3f6fe3a6edc64b8d99b19c546d4c009d`.

<!-- G0016_VISIBLE_REVIEW_V1_BEGIN -->
> **Verdict (normative):** PASS_BOUNDED_PROOF_LOGIC
>
> **Tier (normative):** same-family T1
>
> **Scope (normative):** exact nonmembership for the registered 16000-raw/9804-class same-component family union the 6740 named beta2-common edge-multiset lifts
<!-- G0016_VISIBLE_REVIEW_V1_END -->

This fresh proof-level pass found no mathematical counterexample or scope leak
in the bounded theorem.  The review is same-model-family/same-lineage T1
evidence.  It is not a blind different-family replication or a human referee
review and does not confer T2 standing.

## Lemma-by-lemma verdicts

| Draft lines | Claim | Finding | Referee analysis |
|---|---|---|---|
| 13–57 | Definitions and registered-family censuses | **PASS** | The atom is the unnormalised `S_11` sum of the outer maximum of two edgewise-max branch sums, with multiset occurrences counted.  The pinned source filter yields 252 bases with component census `(2,8):168`, `(3,7):39`, `(4,6):32`, `(5,5):13`.  The same-component endpoint count is 16,000.  The internal-edge count is `168*29+39*24+32*21+13*20=6,740`; exactly eight existing union edges per base give `252*8=2,016` duplicate-occurrence cases and 4,724 edges absent from both branches. |
| 77–120 | Ordered-cone normal form | **PASS** | Every registered branch has five loopless edge occurrences, so each right-minus-left direction is integral and zero-sum.  On the ordered chamber each edge maximum is its higher-ranked coordinate, giving `max(L_A,L_B)=L_A+rho_d`.  Primitive orientation and `rho_(-h)=rho_h-h dot x` give the stated linear correction.  One loopless edge contributes `2*r*9!` permutations to rank `r`; five occurrences give the universal `5*2*r*9!` base. |
| 105–120 | Equal-size scope of the normal form | **PASS** | The earlier literal overbreadth is fixed: the draft now says “every registered five-edge-per-branch atom.”  This is load-bearing because arbitrary unequal-size multisets from the opening general definition need not produce a zero-sum direction and do not have the universal five-left-edge base.  The proof no longer claims that extension. |
| 124–134 | Active-hinge independence and selected-coordinate projection | **PASS** | Summation by parts gives `h dot x=-sum_k s_k delta_k`.  Canonical orientation supplies a positive prefix; a negative prefix is therefore exactly what makes the hyperplane meet the strict chamber.  Distinct primitive oriented directions define distinct hyperplanes.  At a generic interior point of one such hyperplane, only its ReLU has a gradient jump, forcing its coefficient to vanish in any functional identity.  Linear terms then vanish on an open set.  Equality of functions therefore forces equality of complete coordinates and, necessarily, of any selected valid projection; completeness of the 7,135 directions is not required. |
| 136–175 | Target scaling, exact separator, and real coefficients | **PASS** | On the chamber, `MAX11=x_11`; the integer target for `11!*MAX11` is supported only at row 7145 with value 39,916,800.  Excluding this nonzero scalar multiple excludes `MAX11`.  Multiplying equation (1) by `4/D` gives the stated rational row functional with `lambda_f=1`, `lambda^T M=0`, and `lambda^T b=11!`.  The contradiction applies to every `c in R^9804`; rationality is required only of the separating functional, not of a putative representation. |
| 181–188 | Quotient transport | **PASS** | Simultaneous vertex relabelling reindexes the full permutation sum and one global `A/B` swap preserves the outer maximum.  Hence every raw atom equals its orbit representative and class sizes do not weight a linear span.  G-0014 independently reconstructed the 16,000 raw list and 9,804-class partition, found no partition conflict, matched every class size and first representative, and bound frozen representative `j` to matrix column `j`. |
| 192–230 | Common-edge multiset lemma and beta2 inclusion | **PASS** | Adding one occurrence of the same edge to both branches gives `max(L_A+h_e,L_B+h_e)=h_e+max(L_A,L_B)`, including when one source branch already contains `e`.  A fixed loopless edge hits every unordered image pair under exactly `2*9!` permutations, so its symmetrised increment is placement-independent.  Replacing the beta edge by `{a,11}` on the same source base gives a valid coincident-endpoint member of `F` with the identical function.  Thus every beta2 function lies in the `F` function set and `span_K(F union B)=span_K(F)` for `K=Q,R`. |
| 238–260 | Exact arithmetic and semantic matrix evidence | **PASS** | G-0012 replayed the exact 5,270-row relation on all 9,804 columns: 51,667,080 relation entries, raw target pairing 39,916,800, no discrepancy, eleven exact modular reductions, and six rejected hostile mutations.  G-0014 regenerated all `7,146*9,804=70,059,384` integer entries with zero mismatched columns, entries, or dual-support entries; its regenerated matrix hash is `aaa4f481f6e29f05ac226f2de44e3829563190fd6daddd8a66130e9257493b0c`.  Inputs were unchanged during the run. |
| 250–260 | Direction, support, and target bindings | **PASS** | G-0014 validated all 7,135 directions as distinct primitive zero-sum oriented active cuts, matched their canonical hash, bound 5,269 pivot rows plus failing row 7145, and reproduced the target with no hinge support and sole final-linear value `11!`.  This supplies the semantic premise used by the exact left dual without claiming independent rediscovery of the adaptive direction-selection provenance. |
| 261–265 | Exhaustive beta2 mapping evidence | **PASS** | G-0018 reconstructed all 6,740 raw beta2 occurrences and all 4,916 quotient representatives, verified five occurrences per branch, audited the 2,016/4,724 duplicate/new census, mapped every record to a valid same-base coincident-endpoint witness in `F`, passed direct permutation controls for `n=4,5,6,7`, and rejected all three hostile mutations. |
| 273–293 | Claim boundary | **PASS** | The normative statement is exactly finite-family real-span nonmembership.  The draft expressly declines the 9,200 cross-component family, multi-edge lifts, other pair atoms, asymmetric constructions, arbitrary finite two-hidden-layer networks, the all-`n` conjecture, width lower bounds, approximation, and trainability.  A nonzero dual value on one cross-family class is correctly described only as failure of this separator for the enlarged family, not as a membership result. |

## Required disposition

1. Record G-0015 as an internally certified bounded theorem at same-family T1:
   `MAX11` is outside the real span of the registered 16,000-occurrence,
   9,804-class same-component family together with the 6,740 named
   beta2-common edge-multiset lifts.
2. Preserve the exact claim boundary.  The result is not an unrestricted
   MAX11 theorem and is not a lower bound for arbitrary two-hidden-layer ReLU
   networks.
3. Preserve the review boundary.  This report supplies no different-family or
   human T2 review and must not be labelled as one.
4. Bind the exact G-0012, G-0014, G-0015, G-0016, and G-0018 bytes in the
   fail-closed G-0017 receipt and release custody record.

No counterexample was found.  The former smallest decisive falsifier—a single
semantic mismatch between a regenerated graph-pair column and the frozen
matrix—was exhaustively tested by G-0014 and did not occur.  The remaining
limitations are the explicit scope boundary and review tier, not an unresolved
premise of the bounded proof.
