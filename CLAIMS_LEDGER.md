# CLAIMS LEDGER — GENERATED VIEW. Do not hand-edit.

Regenerate with `scripts/generate-ledger-view.py`. Canon lives in `ledger/*.toml`; this file renders
computed dispositions, facets, evidence classes, and each claim's weakest link. Divergence between
this view and canon is a defect in the VIEW (schema error SE-15), and the fix is always regeneration.

## Claims

### C-0001@1 — conjecture [mathematics]

> For every integer n >= 1, MAX_n(x)=max{x_1,...,x_n} on R^n is exactly representable by a finite feed-forward ReLU network with exactly two hidden ReLU layers, affine biases allowed, unrestricted finite widths, and arbitrary real weights.

- disposition: **challenged** · trace:99056a88
- evidence class: **CITED** · ceiling after dependencies: **CITED** · weakest link: `C-0001@1`
- falsifier: One explicit integer n together with an unconditional proof that no finite network of the declared architecture over real weights equals MAX_n on all of R^n.
- no-claim: Says nothing about width efficiency, trainability, approximation, bounded domains, generalization, optimization, or non-ReLU architectures.
- open gaps: G-0003
- next rung blocked by: CITED -> COMPUTED_BOUNDED: computation with domain_checked + detection_floor + repro + artifact

### C-0002@1 — conjecture [mathematics]

> MAX_11 on R^11 is exactly representable by a finite feed-forward ReLU network with exactly two hidden ReLU layers, affine biases allowed, unrestricted finite widths, and arbitrary real weights.

- disposition: **challenged** · trace:876f5bfb
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0002@1`
- falsifier: An unconditional proof that no finite two-hidden-layer ReLU network over arbitrary real weights equals MAX_11 globally.
- no-claim: A positive witness settles only n=11; failure of a rational, symmetric, pairwise-comparison, or bounded-width search does not refute this claim.
- open gaps: G-0002, G-0005, G-0006, G-0008
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0003@1 — construction [mathematics]

> For each integer n with 1 <= n <= 10, MAX_n has an exact finite two-hidden-layer ReLU representation under the campaign's architecture convention.

- disposition: **challenged** · trace:fa1259df
- evidence class: **CITED** · ceiling after dependencies: **CITED** · weakest link: `C-0003@1`
- falsifier: —
- no-claim: This retrieved construction claim has not yet been clean-room replayed here and says nothing for n >= 11.
- open gaps: G-0001
- next rung blocked by: CITED -> COMPUTED_BOUNDED: computation with domain_checked + detection_floor + repro + artifact

### C-0004@1 — reduction [mathematics]

> If MAX_(d+1) has an exact two-hidden-layer ReLU realization and every CPWL function on R^d has the cited signed decomposition into maxima of d+1 affine forms, then every CPWL function on R^d has an exact two-hidden-layer ReLU realization by parallel composition and a final affine combination.

- disposition: **challenged** · trace:9561c704
- evidence class: **CITED** · ceiling after dependencies: **CITED** · weakest link: `C-0004@1`
- falsifier: —
- no-claim: The implication is dimension- and hypothesis-sensitive; it neither proves the decomposition from metadata nor extends a MAX_11 result beyond d=10.
- open gaps: G-0004
- next rung blocked by: CITED -> COMPUTED_BOUNDED: computation with domain_checked + detection_floor + repro + artifact

### C-0005@1 — boundary-claim [mathematics]

> The imported 2026-08-27 audit reported 12179657 symmetry-reduced template columns and 657822 retained hinge rows (657833 total rows after adding 11 linear rows) for the n=11, k=5 pairwise-max/outer-max certificate family under its sorted-cone hinge reduction.

- disposition: **quarantined** · facets: HEURISTIC · trace:f73c8f2a
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0005@1`
- falsifier: —
- no-claim: The imported counts are quarantined, not independently regenerated, and do not describe unrestricted two-hidden-layer networks or exact feasibility.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0006@1 — implementation-claim [mathematics]

> Toolchain-control implementation v1 is identified by the declared control-code manifest, exact environment manifest, and synthetic control-input snapshot.

- disposition: **open** · trace:b3bbfecf
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0006@1`
- falsifier: —
- no-claim: Identity only; it establishes no behavior beyond these exact subject bytes.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0007@1 — method [mathematics]

> The pinned project-local toolchain passes the declared exact SAT, UNSAT, rational-arithmetic, floating-LP, and Lean/Mathlib known-answer smoke controls.

- disposition: **open** · facets: UNCHALLENGED · trace:ed92c8aa
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0007@1`
- falsifier: —
- no-claim: These smoke controls do not validate a future neural-network encoding, prove solver soundness generally, or support MAX_11.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0008@1 — novelty-claim [mathematics]

> Within the searches logged on 2026-08-29 and the retained primary-source corpus, the campaign found no work settling whether MAX_11 has an exact global finite two-hidden-layer ReLU representation over arbitrary real weights; the closest retrieved construction reaches n <= 10.

- disposition: **open** · facets: UNCHALLENGED · trace:afbf2c29
- evidence class: **CITED** · ceiling after dependencies: **CITED** · weakest link: `C-0008@1`
- falsifier: —
- no-claim: This is only NO_PRIOR_FOUND under the dated queries, engines, screened hits, and coverage gaps in NOVELTY_SEARCH_LOG.md; it is not a proof of priority, novelty, or universal open status.
- next rung blocked by: CITED -> COMPUTED_BOUNDED: computation with domain_checked + detection_floor + repro + artifact

### C-0009@1 — theorem-attempt [mathematics]

> MAX_11 is not in the real linear span of the fully S_11-symmetrized atoms from the registered 16,000-raw/9,804-class same-component family together with the 6,740 named beta2-common edge-multiset lifts.

- disposition: **challenged** · trace:646e28e4
- evidence class: **COMPUTED_BOUNDED** · ceiling after dependencies: **COMPUTED_BOUNDED** · weakest link: `C-0009@1`
- falsifier: One exact coefficient mismatch in the registered graph-to-matrix semantics, an invalid rational left-dual identity, a failure of quotient transport or the common-edge multiset lemma, or explicit real coefficients representing the target in the declared finite family.
- no-claim: Does not settle unrestricted MAX_11, prove completeness of the registered atoms, or exclude cross-component, multi-edge, other pair-atom, asymmetric, or arbitrary finite two-hidden-layer real-weight ReLU-network representations.
- open gaps: G-0007
- next rung blocked by: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned) (+1 more)

### C-0010@1 — implementation-claim [mathematics]

> Bounded-theorem bundle verifier v1 is identified by the exact G-0017 verifier bytes, project toolchain environment manifest, and canonical bundle specification.

- disposition: **open** · trace:4aeed740
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0010@1`
- falsifier: —
- no-claim: Identity only; this record establishes no theorem or verifier behavior beyond the exact code, environment, and data/specification bytes.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0011@1 — theorem-attempt [mathematics]

> Within the frozen fully S_11-symmetrized degree-five pair-atom semantics, every atom whose branch-difference signed core uses fewer than all 11 labels has zero pairing with the eleventh alternating finite-difference functional; consequently any certificate for MAX_11 in this semantics must use at least one full-support signed core.

- disposition: **open** · facets: UNCHALLENGED · trace:67799fa9
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0011@1`
- falsifier: One frozen pair atom with proper signed-core support and nonzero eleventh finite difference, or one error in the support-to-U-statistic reduction.
- no-claim: This does not exclude full-support atoms, prove that the pair-atom semantics is complete, or constrain arbitrary asymmetric or real-inner-weight two-hidden-layer networks.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0012@1 — implementation-claim [mathematics]

> Proper-signed-core obstruction implementation v1 is identified by the G-0047 theorem script, pinned subject environment, and frozen G-0038 signed-orbit stream.

- disposition: **open** · trace:462394e0
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0012@1`
- falsifier: —
- no-claim: Identity only; this record establishes no theorem beyond the exact implementation, environment, and input bytes.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0013@1 — theorem-attempt [mathematics]

> Within the complete frozen fully S_11-symmetrized signed-mass-one-through-three degree-five pair-atom census, no real linear combination can cancel every ordered-cone hinge while retaining nonzero eleventh finite difference; hence this finite family cannot represent MAX_11.

- disposition: **supported** · facets: UNCHALLENGED · trace:7868ca76
- evidence class: **COMPUTED_BOUNDED** · ceiling after dependencies: **COMPUTED_BOUNDED** · weakest link: `C-0013@1`
- falsifier: One omitted signed-mass-at-most-three orbit, one omitted primitive degree-three hinge, a rank or rational-replay mismatch, or explicit real coefficients producing a hinge-free vector with nonzero eleventh finite difference.
- no-claim: This does not cover signed mass at least four, atoms outside the frozen pair-orbit census, arbitrary continuous inner weights, nonsymmetric networks, or unrestricted two-hidden-layer MAX_11.
- next rung blocked by: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned) (+1 more)

### C-0014@1 — implementation-claim [mathematics]

> Signed-mass-at-most-three exact-rank verifier v1 is identified by the G-0050 exact-Q bridge script, pinned subject environment, and frozen G-0050 raw modular-rank input.

- disposition: **open** · trace:78fb9798
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0014@1`
- falsifier: —
- no-claim: Identity only; this record establishes no bounded theorem beyond the exact implementation, environment, and input bytes.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0015@1 — implementation-claim [mathematics]

> G-0046 candidate global-normal-form verifier v1 is identified by the G-0049 verifier script, pinned subject environment, and frozen G-0046 candidate report.

- disposition: **open** · trace:495d9f21
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0015@1`
- falsifier: —
- no-claim: Identity only; this record establishes no global identity or refutation beyond the exact implementation, environment, and candidate bytes.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0016@1 — implementation-claim [mathematics]

> Signed-mass-four full-core census implementation v1 is identified by the G-0052 census script, pinned subject environment, and frozen G-0038 signed-orbit stream.

- disposition: **open** · trace:57f5695c
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0016@1`
- falsifier: —
- no-claim: Identity only; this record establishes neither a signed-mass-four construction nor an obstruction.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0017@1 — boundary-claim [mathematics]

> The frozen G-0046 rank-7,302 two-prime relation is not a global identity for 11!*MAX_11 in the declared loopless registered pair-atom semantics.

- disposition: **supported** · facets: UNCHALLENGED · trace:6e142a34
- evidence class: **COMPUTED_BOUNDED** · ceiling after dependencies: **COMPUTED_BOUNDED** · weakest link: `C-0017@1`
- falsifier: An exact replay showing zero complete primitive hinge and linear residuals for the frozen coefficient vectors at both registered primes.
- no-claim: This refutes only the displayed modular relation, not every relation on the same family, signed-mass-four atoms, other atom families, or unrestricted MAX_11.
- next rung blocked by: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned) (+1 more)

### C-0018@1 — boundary-claim [mathematics]

> The frozen signed-mass-four full-support census contains exactly 1,465 distinct orbit atoms; their complete ordered-cone semantics uses a 99,858-direction degree-four universe, 1,111 atoms have nonzero eleventh finite difference, and 354 have zero eleventh finite difference.

- disposition: **supported** · facets: UNCHALLENGED · trace:9d201825
- evidence class: **COMPUTED_BOUNDED** · ceiling after dependencies: **COMPUTED_BOUNDED** · weakest link: `C-0018@1`
- falsifier: One missing or duplicate frozen full-support orbit, one escaping primitive direction, or one exact invariant/count mismatch.
- no-claim: The census alone establishes neither a signed-mass-four construction nor an obstruction, and says nothing about unrestricted networks.
- next rung blocked by: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned) (+1 more)

### C-0019@1 — boundary-claim [mathematics]

> Within the frozen 11,542 registered natural single-edge genuine-mass-five atoms, exactly 526 individual columns have identically zero degree-five-only ordered-cone normal form and all 526 are same-family. On the preregistered deterministic sketch, the other 11,016 columns have rank 6,626 modulo 1,000,003; that displayed sketch rank licenses no dependency of the complete matrix.

- disposition: **supported** · facets: UNCHALLENGED · trace:dc0e39bc
- evidence class: **COMPUTED_BOUNDED** · ceiling after dependencies: **COMPUTED_BOUNDED** · weakest link: `C-0019@1`
- falsifier: One registered-subject reconstruction mismatch, one omitted or extra zero-high column, one nonzero complete degree-five-only hinge in an emitted zero-high column, one cache/report binding drift, or an independently reproduced different rank for the frozen sketch matrix.
- no-claim: Sketch deficiency may be caused by left sketching and is not a complete-matrix kernel certificate. This claim establishes no MAX_11 representation, no obstruction for the registered family, no completeness bridge, and no statement about asymmetric or unrestricted two-hidden-layer networks.
- next rung blocked by: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned) (+1 more)

### C-0020@1 — implementation-claim [mathematics]

> Natural single-edge degree-five kernel gate v1 is identified by the frozen G-0068 script, complete input/subject snapshot, subject environment, immutable shard manifest, and output report.

- disposition: **open** · trace:1abef1ea
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0020@1`
- falsifier: —
- no-claim: Identity only; this record establishes neither that the sketch preserves complete rank nor any MAX_11 construction or obstruction.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0021@1 — boundary-claim [mathematics]

> For the pinned direct matrix consisting of the 1,288 exact S1 pivot columns and exactly 526 reconstructed G-0068 zero-high candidates on all 99,858 complete degree-four hinge rows, the rank is 1,713 modulo each of 1,000,003 and 1,000,033, so the candidate quotient rank is 425 and modular nullity is 101 at both primes. Appending the exact Lambda row raises neither modular rank.

- disposition: **supported** · facets: UNCHALLENGED · trace:3596e29e
- evidence class: **COMPUTED_BOUNDED** · ceiling after dependencies: **COMPUTED_BOUNDED** · weakest link: `C-0021@1`
- falsifier: One input, subject, semantic, source-row, or script binding drift; one independently reproduced different complete-source rank or augmented rank at either registered prime; or one nonzero complete-row or Lambda residual in a reported modular kernel relation.
- no-claim: Matching deficiency and zero Lambda gain at two primes are not an exact-Q rank theorem or rational dual certificate. This establishes no no-go for the primary block, no conclusion for the omitted 252 structural mass-four semantics, no MAX11 construction, and no statement about asymmetric or unrestricted two-hidden-layer networks.
- next rung blocked by: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned) (+1 more)

### C-0022@1 — implementation-claim [mathematics]

> Joint zero-high S1 quotient gate v1 is identified by the frozen G-0070 script, complete input/subject snapshot, subject environment, full compressed report, and bounded result receipt.

- disposition: **open** · trace:6684561b
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0022@1`
- falsifier: —
- no-claim: Identity only; this record establishes neither exact rational rank nor any MAX11 construction or obstruction.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0023@1 — boundary-claim [mathematics]

> For the pinned direct matrix consisting of the 1,288 exact S1 pivot columns, 526 primary zero-high candidates, and 252 deduplicated structural mass-four base semantics on all 99,858 complete degree-four hinge rows, the rank is 1,747 modulo each of 1,000,003 and 1,000,033. Thus the combined candidate quotient rank is 459, the structural appendix adds 34 modular quotient directions, modular nullity is 319, and appending the exact Lambda row raises neither modular rank.

- disposition: **supported** · facets: UNCHALLENGED · trace:ef71bcaf
- evidence class: **COMPUTED_BOUNDED** · ceiling after dependencies: **COMPUTED_BOUNDED** · weakest link: `C-0023@1`
- falsifier: One input, subject, semantic, alias-map, source-row, or script binding drift; failure of the 1,877-to-252 structural deduplication or exact zero-Lambda controls; one independently reproduced different complete-source or augmented rank at either registered prime; or one nonzero complete-row or Lambda residual in a reported modular kernel relation.
- no-claim: Matching deficiency and zero Lambda gain at two primes are not an exact-Q row-span dual or rational no-go. This does not retire the complete registered natural family because G-0068's nonzero-high sketch deficiency remains inconclusive; it establishes no MAX11 construction and says nothing about asymmetric loop-edge atoms, other graphical atoms, arbitrary real directions, or unrestricted two-hidden-layer networks.
- next rung blocked by: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned) (+1 more)

### C-0024@1 — implementation-claim [mathematics]

> Joint zero-high plus structural mass-four S1 quotient appendix v1 is identified by the frozen G-0070 script, complete combined input/subject snapshot, subject environment, full compressed report, and bounded appendix result receipt.

- disposition: **open** · trace:451175cb
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0024@1`
- falsifier: —
- no-claim: Identity only; this record establishes neither exact rational rank nor any MAX11 construction or obstruction.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0025@2 — boundary-claim [mathematics]

> For the frozen asymmetric loop-edge family consisting of 3,754 full-S_11 orbit columns plus the 5E and 5L linear carriers, the registered 4,107 by 3,756 matrix has column rank 3,518 modulo each of 1,000,003 and 1,000,033, while appending the exact 11!*MAX11 target raises the rank to 3,519 at both primes. Hence the target is outside the complete unsketched family span over each registered field, because the registered hinge CountSketch together with the eleven exact linear rows is a left-linear image of that complete system. A same-script run to a distinct output path reproduces the signed matrix digest, scientific payload, and both rank gaps; it is correlated reproducibility, not a clean-room replay.

- disposition: **supported** · facets: UNCHALLENGED · trace:4a959532
- evidence class: **COMPUTED_BOUNDED** · ceiling after dependencies: **COMPUTED_BOUNDED** · weakest link: `C-0025@2`
- falsifier: One frozen subject, input, loop-inclusive semantic, orbit, sketch, target, code, or backend binding drift; one independently reproduced different column or augmented rank at either registered prime; or one full modular solution whose registered sketch fails to solve the reported matrix.
- no-claim: The two modular obstructions are not an exact-Q left dual, denominator bound, or real-coefficient no-go. The same-script reproduction is not an independently reimplemented semantic or rank replay. This does not exclude other graphical atoms, nonsymmetric blocks, non-graphical inner directions, arbitrary real weights, deeper networks, or unrestricted two-hidden-layer representations of MAX11.
- next rung blocked by: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned) (+1 more)

### C-0026@2 — implementation-claim [mathematics]

> Asymmetric loop-edge global span gate v1 is identified by the frozen G-0072 producer and fail-closed reproduction verifier, Git revision, bound inputs and principal backend entrypoints, deterministic subject and scientific-payload digests, canonical venv environment manifest, and compressed result receipt.

- disposition: **open** · trace:4f6de3e3
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0026@2`
- falsifier: —
- no-claim: Identity only. The binding hashes principal Python/backend entrypoints rather than every transitively linked shared library, and establishes neither an exact rational obstruction nor any MAX11 construction or unrestricted-network lower bound.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0027@1 — boundary-claim [mathematics]

> For the frozen 364 by 8,107 integer profile matrix of 8,104 full-S_11 Y-spoke orbit columns plus C_L, C_E, and C_Y, exact integer Gram/RREF computation gives rational rank 258 and row nullity 106, and the exact MAX11 profile target lies in the rational column span. An emitted 257-term rational witness, consisting of 256 Y-spoke orbit columns and C_E, replays with zero residual on all 364 rows using both FLINT and stdlib Fraction arithmetic; a disjoint clean-room semantic implementation independently replays the same selected witness exactly.

- disposition: **supported** · facets: UNCHALLENGED · trace:151f1eae
- evidence class: **COMPUTED_BOUNDED** · ceiling after dependencies: **COMPUTED_BOUNDED** · weakest link: `C-0027@1`
- falsifier: One frozen subject, orbit, normalization, matrix, target, producer, or backend binding drift; one independently reproduced nonzero rational residual on any of the 364 rows; one exact full-matrix rank different from 258; or one descriptor mismatch in the selected 257-term witness.
- no-claim: This establishes equality only on the 364 symmetric profiles over levels {0,1,2,3}. It is not a global CPWL identity, a two-hidden-layer MAX11 network, a proof away from the frozen profiles, or an unrestricted depth result. The clean-room replay establishes the selected witness and a rank-258 lower bound but not the full 8,107-column rank upper bound.
- next rung blocked by: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned) (+1 more)

### C-0028@1 — implementation-claim [mathematics]

> Y-spoke exact symmetric-profile gate v1 is identified by frozen producer SHA-256 333dba4065c08d54742177941305c13841e6237001f364cf5a68a9e4ec2ebf67, preflight scientific payload d440ecf8b5119f1c6b8f872444cb364995d1f4043513519d57fbbd3eeb3517b8, the complete registered compressed outcome, and canonical subject environment manifest.

- disposition: **open** · trace:bf569940
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0028@1`
- falsifier: —
- no-claim: Identity only; this record establishes neither a global MAX11 construction nor correctness beyond the bound subject, profiles, semantics, and principal backend entrypoints.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0029@1 — implementation-claim [mathematics]

> G-0073 clean-room semantic replay v1 is identified by standalone replayer SHA-256 f67a0adcba1b273cec38266b52f27908a27e5c6e0b6a5a2fecbcbda70191c54b, the registered outcome bytes it binds, and audit receipt SHA-256 a207d86304470ec5d813843be4fc71ad72373afcff93630f9d585b4222cf4db2.

- disposition: **open** · trace:d6944314
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0029@1`
- falsifier: —
- no-claim: Identity only. The replay is a fresh-context same-model-lineage T1 implementation, not T2 or human review, and it reconstructs only the selected witness columns rather than the complete 8,107-column matrix.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0030@1 — boundary-claim [mathematics]

> For the frozen 1,378 by 8,107 integer system consisting of the 364 G-0073 rows plus all 78 three-colour profiles at all thirteen Farey-F6 spacings, one shared 443-term rational vector (442 Y-spoke orbit columns plus C_E) has exact zero residual on every row. The registered switch-form enumeration proves those nodes contain every possible breakpoint, so translation covariance and positive homogeneity extend the identity to every real input with at most three distinct coordinate values. A disjoint clean-room implementation independently replays the same vector on all 1,378 registered rows and 936 open-interval midpoint rows.

- disposition: **supported** · facets: UNCHALLENGED · trace:c6662233
- evidence class: **COMPUTED_BOUNDED** · ceiling after dependencies: **COMPUTED_BOUNDED** · weakest link: `C-0030@1`
- falsifier: One frozen subject, orbit, row, target, normalization, producer, or backend binding drift; one nonzero exact witness residual on a registered or midpoint row; one missing switch root outside Farey F6; one failed translation/homogeneity degree; or one selected-descriptor mismatch in the clean-room replay.
- no-claim: This establishes equality only on the at-most-three-valued locus. It is not equality on four-or-more-valued inputs, a global CPWL identity, a compiled two-hidden-layer MAX11 network, or an unrestricted depth theorem. The producer has an exact rank-460 lower-bound minor and modular rank 460 at three primes; the clean-room audit independently establishes only rank 444 because seventeen zero-coefficient pivot descriptors are absent from the sparse artifact. No exact full-matrix rank upper bound is claimed.
- next rung blocked by: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned) (+1 more)

### C-0031@1 — implementation-claim [mathematics]

> G-0074 all-spacings three-level gate v1 is identified by frozen producer SHA-256 269472b1eaeb38db852f92e0587243bba6429a300a7acdd35e0930a6b235f10d, preflight scientific payload fc166ac93a268c54c85c9e15f43fcd9c0cfba16b3ebb4d3c3951df39c3c188df, complete registered compressed outcome, row manifest, and canonical subject environment manifest.

- disposition: **open** · trace:b3cb5522
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0031@1`
- falsifier: —
- no-claim: Identity only; this record establishes neither a global MAX11 construction nor correctness beyond the frozen subject, nodes, exact replay contracts, and principal backend entrypoints.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0032@1 — implementation-claim [mathematics]

> G-0074 clean-room semantic replay v1 is identified by standalone replayer SHA-256 29142b4d905527082efcd0f8001feeec1c93e76e2dada768ee97c7ebbcad0de3, the registered outcome bytes it binds, and audit receipt SHA-256 4baae77f8190d388c88a64f6552da544b61add9561ccc695b4d3bb0231d95706.

- disposition: **open** · trace:5cf5bb18
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0032@1`
- falsifier: —
- no-claim: Identity only. The replay is fresh-context same-model-lineage T1 evidence, not T2 or human review. It reconstructs the 443 selected witness columns and C_L, not the complete 8,107-column matrix or the producer's full 460-column pivot minor.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0033@1 — boundary-claim [mathematics]

> For the frozen 16,738 by 8,107 integer evaluation matrix of 8,104 full-S_11 Y-spoke orbit columns plus C_L, C_E, and C_Y, a primitive rational functional supported on 229 selected rows and raw row 2,410 annihilates all 8,107 construction columns exactly and has nonzero pairing with the MAX11 target. Hence that target is outside the rational and real column spans of the complete frozen family on the bound row system. A standalone clean-room implementation independently recomputes all 230 augmented-row gcds and replays every exact residual.

- disposition: **challenged** · trace:72417a10
- evidence class: **COMPUTED_BOUNDED** · ceiling after dependencies: **COMPUTED_BOUNDED** · weakest link: `C-0033@1`
- falsifier: One frozen subject, row, target, normalization, certificate, producer, verifier, or matrix binding drift; one recomputed augmented-row gcd or exact division mismatch; one nonzero exact residual on any of the 8,107 construction columns; a zero or changed exact target pairing; or an independently reconstructed raw rational functional that fails the stated identities.
- no-claim: This excludes only the hash-bound 8,107-column Y-spoke-plus-carrier family on the hash-bound 16,738-row system. It proves no completeness reduction from arbitrary two-hidden-layer networks, no unrestricted ReLU lower bound, no obstruction for absent graphical or facet-gluing atoms, and no novelty or priority claim. The clean-room replay is same-model-lineage T1 evidence, not T2 or human review.
- open gaps: G-0009, G-0010, G-0011
- next rung blocked by: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned) (+1 more)

### C-0034@1 — implementation-claim [mathematics]

> G-0078 adaptive sparse exact left-dual lift v1 is identified by frozen producer SHA-256 6aec90e28318b45680d3ee94254ff491d5eab89df9eec112fe9b5e66ce4f5229, preflight scientific payload 2e055acf291460f793e6673c9df4d76441ee2d52eda59d49ddb9f809bc91ffec, exact outcome scientific payload 0bb1a524503359529bb592030f220be86d88756b797e55c4be04c031852bd573, complete compressed outcome, raw matrix hash, and canonical subject environment.

- disposition: **open** · trace:b927a732
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0034@1`
- falsifier: —
- no-claim: Identity only; this record establishes neither completeness of the frozen construction family nor an unrestricted MAX11 lower bound.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0035@1 — implementation-claim [mathematics]

> G-0078 clean-room exact-dual replay v1 is identified by standalone verifier SHA-256 39fd3b6f0a74ef22b264e16bb184eed2d5094a32c08ab018124182dd10ff5d52, exact upstream artifact SHA-256 8e08caecbf5a4d7b457a32f445702121dc1d095b4e368d45db8bc64847b4ae96, deterministic receipt SHA-256 d5149c9e6495e97549ffb43d5a2f1d75cd4ca71929dec6fc6e09c5d613f42119, and audit-payload SHA-256 b5c469436e99485b7f3adfdf272af543f95926aee653aa45ace7fa2081bb3f50.

- disposition: **open** · trace:b2d76e0d
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0035@1`
- falsifier: —
- no-claim: Identity only. The verifier is fresh-context same-model-lineage T1 evidence on the same frozen inputs, not T2, human review, or an independent new subject construction.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

## Routes

- `H-0001` [active] MAX_11 may lie in the exact rational span of the frozen pairwise-atom family.
- `H-0002` [active] A registered lift, orbit law, or simplex subdivision may extend arity without added depth.
- `H-0003` [active] A registered real-weight invariant may obstruct MAX_11 under two-layer composition.
- `H-0004` [proposed] A normal-form theorem may reduce unrestricted MAX_n representations to finite certificates.

## Dead ends

- `D-0001` Reuse the current G-0011 rational left dual unchanged as a separator after adjoi · scope: Exactly G-0011 dual SHA fe6768c8..., G-0009 cross-family ser · retry_when: `data_changes(cross-component-family-serialization)` · trace:e415470a
- `D-0002` Continue repairing the frozen G-0046 registered-only modular relation by adding  · scope: Exactly the G-0046 rank-7,302 serialized support and its 7,1 · retry_when: `regime_boundary(pair-orbit-family-enlarged-beyond-g0046)` · trace:e0b4a9d2
- `D-0003` Search for MAX11 inside the fully symmetrized asymmetric loop-edge lift of the 2 · scope: Exactly the 5,040 G-0071 labelled seeds quotienting to 3,754 · retry_when: `data_changes(asymmetric-loop-edge-orbit-subject)` · trace:d09d860d

## Experiments (multiplicity ledger)

- `EXP-0001` [complete] family `bootstrap-toolchain-controls-v1` arm — prereg=False · trace:6c210206
- `EXP-0002` [planned] family `known-max-cleanroom-v1` arm — prereg=True · trace:b9472094
- `EXP-0003` [complete] family `max11-same-component-bounded-theorem-v1` arm — prereg=True · trace:edf220a0
- `EXP-0004` [complete] family `max11-proper-signed-core-obstruction-v1` arm — prereg=False · trace:add27c4c
- `EXP-0005` [complete] family `max11-g0046-global-normal-form-falsification-v1` arm — prereg=True · trace:183cb157
- `EXP-0006` [complete] family `max11-signed-mass-at-most-three-exact-q-obstruction-v1` arm — prereg=True · trace:fa9efa60
- `EXP-0007` [complete] family `max11-signed-mass-four-full-core-census-v1` arm — prereg=True · trace:d2fb7ef9
- `EXP-0008` [complete] family `max11-natural-single-edge-mass5-zero-high-census-v1` arm — prereg=True · trace:ff2593a4
- `EXP-0009` [complete] family `max11-zero-high-joint-s1-quotient-v1` arm — prereg=True · trace:e7ff91b4
- `EXP-0010` [complete] family `max11-zero-high-plus-structural-mass4-joint-quotient-v1` arm — prereg=True · trace:66226b80
- `EXP-0011` [complete] family `max11-asymmetric-loop-edge-inherited-weight-probe-v1` arm — prereg=False · trace:ec8d81bb
- `EXP-0012` [complete] family `max11-asymmetric-loop-edge-3754-orbit-global-span-v1` arm — prereg=True · trace:ed682030
- `EXP-0013` [complete] family `max11-y-spoke-8104-orbit-exact-profile-gate-v1` arm — prereg=True · trace:6e699958
- `EXP-0014` [complete] family `max11-y-spoke-complete-three-level-spacing-gate-v1` arm — prereg=True · trace:b80b3dda
- `EXP-0015` [complete] family `max11-y-spoke-generic-four-level-direct-rank-gate-v1` arm — prereg=True · trace:74032ac3
- `EXP-0016` [complete] family `max11-y-spoke-target-aware-four-level-kernel-v1` arm — prereg=True · trace:d74e8ce9
- `EXP-0017` [complete] family `max11-y-spoke-exact-left-dual-lift-v1` arm — prereg=True · trace:34ecda54
- `EXP-0018` [complete] family `max11-y-spoke-sparse-exact-left-dual-lift-v1` arm — prereg=True · trace:f66d54d4
- `EXP-0019` [aborted] family `max11-same-component-complete-exact-price-vector-v1` arm — prereg=True · trace:4146b2e1
