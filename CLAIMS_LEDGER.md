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
- open gaps: G-0002, G-0005, G-0006, G-0008, G-0012, G-0014, G-0015
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

### C-0036@1 — boundary-claim [mathematics]

> For the complete registered same-component Y-spoke extension, the primitive exact G-0078 row functional has nonzero pairing with 17,952 of the 18,582 frozen new full-S_11 orbit columns and zero pairing with the remaining 630; its pairing with the MAX11 target is nonzero. All 4,273,860 support entries and the complete exact price vector were independently replayed. Consequently, the exact functional that separates MAX11 from the old 8,107-column family does not annihilate the combined frozen 26,689-column dictionary.

- disposition: **supported** · facets: UNCHALLENGED · trace:a22d81a5
- evidence class: **COMPUTED_BOUNDED** · ceiling after dependencies: **COMPUTED_BOUNDED** · weakest link: `C-0036@1`
- falsifier: One frozen source, preregistration, semantic input, seed, orbit representative, column order, support entry, functional weight, price, target pairing, count, artifact digest, or independently reconstructed literal nested value differs from the registered bytes.
- no-claim: This exact price vector proves neither membership nor nonmembership of MAX11 in the combined finite dictionary, gives no rational coefficient vector, filters no zero-price or nonzero-price column from a later solve, establishes no global CPWL identity, and proves no unrestricted two-hidden-layer result. The clean-room replay is same-model-lineage T1 evidence and shares the frozen G-0078 functional artifact and Pynauty ordering dependency.
- next rung blocked by: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned) (+1 more)

### C-0037@1 — implementation-claim [mathematics]

> G-0079 complete exact price-vector v2 is identified by frozen runner SHA-256 7539515641c241a28be45cea88445bd4f598f7c0693ab521c31805530c9f67da, preregistration SHA-256 c3da38c06f6d8b9b5ab9e89322f50ca9c797ea5bcfe5c9ea4dc8d618464e5b05, exact outcome SHA-256 5d6754c91f7971aa3fdad2d1f171645f32fa57c26b4a001bb3b6ac9d5e802958, scientific payload SHA-256 357e2437849dac4074995892a6f174d9f225848280e2bf53d9f9ea1010d9e265, and the bound semantic-source and environment manifests.

- disposition: **open** · trace:ce7c8417
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0037@1`
- falsifier: —
- no-claim: Identity only; this establishes neither target membership nor nonmembership, rational coefficients, a global identity, or completeness of the frozen dictionary.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0038@1 — implementation-claim [mathematics]

> G-0079 exact-price clean-room replay v2 is identified by standalone verifier SHA-256 fd1d0293ea507f9dd26d0948f54ff9358eb6ee8213d538ec3ec0510a4478b02a, exact upstream artifact SHA-256 5d6754c91f7971aa3fdad2d1f171645f32fa57c26b4a001bb3b6ac9d5e802958, deterministic replay receipt SHA-256 6ace81f51e1c944756166d475914b3fd8e8c09030491651bd946441d4d8f58ae, price-vector digest 9ee2e4af9df71e83d72b418f30a023308244abae50073e9fbd766d79c7261e3d, and literal-matrix digest a38b8237b108284ecafaa4f97a0c0c29a60b3a9dd58521389762effb4e4619b2.

- disposition: **open** · trace:4a245353
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0038@1`
- falsifier: —
- no-claim: Identity only. The verifier is fresh-context same-model-lineage T1 evidence, not T2 or human review; it shares Pynauty for frozen orbit ordering and the registered G-0078 functional artifact, and it does not independently reconstruct all 8,107 old columns.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0039@1 — theorem-attempt [mathematics]

> For every n>=2, the alternating proper-complement sum R_n(x)=sum_{empty!=S proper subset [n]} (-1)^(|S|+1) MAX_{[n]\S}(x) equals max_i x_i+(-1)^n min_i x_i. For n=11, conditional on the retrieved exact MAX_k two-hidden-layer representations for k<=10, R_11=max-min is itself two-hidden-layer representable. Its centered difference body Delta_11^0+(-Delta_11^0) has, at each simplex facet normal, exactly the same independently translation-normalized exposed-face shape as Delta_11^0 while differing in support height and global normal fan. Therefore the eleven projected MAX10 face shapes, even when induced by one global network, do not suffice to reconstruct centered MAX11.

- disposition: **open** · trace:7263d0de
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0039@1`
- falsifier: One incorrect alternating coefficient, one complement of arity eleven, failure of same-depth parallel composition, a sign or scaling error in the centered difference-body face calculation, or one projected facet that differs from the centered MAX10 simplex.
- no-claim: This refutes only reconstruction from eleven independently translation-normalized exposed-face shapes. It does not refute stronger criteria retaining support heights, selected endpoint translations, additional normal directions, or the complete global wall fan; it neither constructs MAX11 nor proves MAX11 impossible. The MAX1--MAX10 network dependency remains only CITED in this campaign.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0040@1 — theorem-attempt [mathematics]

> In the centered n=11 space H, let eleven ordered local zonotope branch pairs (P_i,Q_i) have generators in E_i={z in H:z_i=0} and tied relative centers p_i-q_i in E_i. After canonical consolidation by unoriented generator line, the condition that each line visible on two local faces has the same total length on both, separately for P and Q, is necessary and sufficient for finite full-dimensional global zonotopes P,Q whose exposed faces at d_i=mu-e_i equal P_i,Q_i up to one common translation per i. Rational local data admit an explicit rational construction, and each resulting convex-hull primitive compiles into exactly two hidden ReLU layers.

- disposition: **open** · trace:12df823d
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0040@1`
- falsifier: Compatible rational local data satisfying the generator-consistency and branch-tie hypotheses for which the explicit visible-generator union plus 110 dense center-correctors fails to reproduce one exposed face; a hidden compatibility not captured by canonical generator lines; a dependence in the claimed basis of H^11; or a required skip connection or third hidden layer in the compiled primitive.
- no-claim: The theorem glues only eleven specified exposed faces and their support ties. Dense correction and padding generators generally create additional global walls. It proves neither cancellation of those walls, equality of the global virtual polytope with the simplex, a MAX11 construction, nor an unrestricted impossibility theorem. Novelty has not been adjudicated and T2 or human review is unavailable.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0041@1 — boundary-claim [mathematics]

> Over F_1,000,003, the frozen 16,738-row integer evaluation matrix containing all 8,107 old Y-spoke/carrier columns and all 18,582 registered complementary same-component columns has rank 8,868, while adjoining the MAX11 target raises the rank to 8,869. Equivalently, after a rank-6,876 old basis is eliminated, the complete target-last Schur matrix has new-column rank 1,992 and augmented rank 1,993. Hence no coefficient vector over this finite field represents the target on the frozen rows using the complete 26,689-column dictionary. The persisted Schur RREF was independently recomputed byte-for-byte by the supervising parent process.

- disposition: **challenged** · trace:d1c11992
- evidence class: **COMPUTED_BOUNDED** · ceiling after dependencies: **COMPUTED_BOUNDED** · weakest link: `C-0041@1`
- falsifier: One frozen input, column, row, target, ordering, Schur projection, cache receipt, rank, pivot, custody, or byte-for-byte parent RREF replay mismatch; a mod-1,000,003 coefficient vector solving all 16,738 rows; or failure of the target-last pivot under an independent exact modular reconstruction.
- no-claim: This is one-prime finite-row nonmembership only. It is not characteristic-zero or real nonmembership, because the old or enlarged integer matrix rank may drop at this prime; it supplies no rational dual, global CPWL obstruction, completeness theorem for degree-five atoms, or unrestricted two-hidden-layer MAX11 lower bound. The parent replay shares the registered implementation and host, so current standing is computed-bounded rather than clean-room independent.
- open gaps: G-0013
- next rung blocked by: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned) (+1 more)

### C-0042@1 — implementation-claim [mathematics]

> G-0081 complete native Schur/RREF implementation v1 is identified by runner SHA-256 f95ad8bba3220f84a4ae8b6d3794b85ca40893454916616729fcf2786a54033b, preregistration SHA-256 f30a771dd1854420f1ff0e06881cdae2ac7f02025681c578b41c73a0164d8827, canonical CPython environment SHA-256 f17bb20bb817e5c4fe626f3782c3b382b1ba0cd2397b704def11a26df61ea1b4, final compressed result SHA-256 61e9c63b974a64d0272569b5e71a04541d49d853a76ec31ca59a6b6d0d1b95ef, scientific payload SHA-256 6d8d9bb6406f26a1515d60ef8c1a366fb556d40207184fa17d776d1626a0a06a, and its bound C-to-S-to-R receipt chain.

- disposition: **open** · trace:6d8e6a5d
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0042@1`
- falsifier: —
- no-claim: Identity only. This record establishes neither correctness beyond the exact registered bytes nor characteristic-zero, global, family-complete, or unrestricted MAX11 nonrepresentability.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0043@1 — boundary-claim [mathematics]

> For the G-0099 leaf/opposite-colour-edge incidence D, exact semantic calculations show that D annihilates every relation among balanced bicoloured tree atoms at n=5 and n=7, so it descends abstractly on those tested tree quotients. However, already at n=5: extending D by zero to the complete 131-column loop-inclusive degree-two Rueß dictionary raises semantic rank from 17 to 19; the literal tied exposed face retains branch-dependent selected-endpoint translations and need not equal the unshifted deletion atom even modulo a global linear term; and the canonical endpoint-tagged event sum raises tree rank from 4 to 6. Thus the tested G-0099 incidence is a coefficient gauge, not a representation-independent support-function induction law.

- disposition: **open** · facets: UNCHALLENGED · trace:33fbe0ee
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0043@1`
- falsifier: One exact relation whose reported upper residual is nonzero, a zero lower residual for the exported eight-term witness, global translation equivalence of the literal tied-face counterexample, descent of the tagged event map on the reported tree kernel, or an independent reconstruction disagreeing with any stated orbit census or rank.
- no-claim: The negative statements exclude only the specified zero-extension, unshifted face, and canonical atom-dependent tagged-event interpretations. They do not refute a fixed-normal face derivative, a genuinely additive valuation defined on every atom, the complete degree-five Rueß span, MAX11 representability, or unrestricted two-hidden-layer networks. Three of the four discoveries were exploratory before deterministic freezing and still await independent replay.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0044@1 — implementation-claim [mathematics]

> G-0103 leaf-incidence semantic audit suite v1 is identified by manifest-file SHA-256 145d890dcf46b41717c8310c8fad18bd6d6e5f5cbee9e529c8fe7729930fc25d and the eleven producer, preregistration, result, and README entries whose hashes it checks.

- disposition: **open** · trace:5832a2fc
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0044@1`
- falsifier: —
- no-claim: Identity only. The suite is author-produced and author-replayed in one same-family context; only the tagged-facet test was preregistered before its outcome, and no independent-agent, T2, or human certification is asserted.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0045@1 — boundary-claim [mathematics]

> Over F_1,000,003, the preregistered 9,814-row joint system combining 8,427 frozen MAX11 semantic equations with 1,387 imposed G-0099 incidence equations is inconsistent on the 22,265-column registered-plus-all-tree-plus-5E/5L dictionary: the incidence Schur rank is 1,380 and the augmented rank is 1,381. An exported modular row functional annihilates every joint dictionary column and pairs with the joint target by 239,271.

- disposition: **supported** · facets: UNCHALLENGED · trace:bdadebd1
- evidence class: **COMPUTED_BOUNDED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0043@1`
- falsifier: One frozen binding, tree alignment, incidence entry, semantic column, rank, separator residual, or target pairing mismatch; an accepted incidence-entry mutation; or a mod-1,000,003 coefficient vector satisfying every frozen semantic and incidence row.
- no-claim: Because C-0043 shows that the imposed incidence is not a representation-independent semantic necessity, this excludes only the finite gauge-constrained candidate generator. It is not rational nonmembership, nonmembership in the unconstrained dictionary, a global identity test, or an unrestricted MAX11 lower bound.
- next rung blocked by: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned) (+1 more)

### C-0046@1 — implementation-claim [mathematics]

> G-0104 joint semantic/incidence discriminator v1 is identified by producer SHA-256 e9e82629680dacab96a0ff5775f58736a60bf2f1bc96c42ce0e569cca1e0fc0c, preregistration SHA-256 57c8501e8a3a0eb3544d9f64e0d990fcba399d8cd96cd7078ee9e10c1de7da6f, compressed result SHA-256 a9fdd478eb5baf5f24ffa474bee3452bc3d54d679748b0b8f9b00aacaebcc2e8, direct separator replay SHA-256 572eb55d3e1a757c04b7cce793a70f6c2f19e48d7d8ac2c9a831ca45d264bc64, and manifest SHA-256 e7e93ce717fb18e844a93cd9bf892ab5955259c89cc20a073a2472694ac72e21.

- disposition: **open** · trace:a4f3fa6d
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0046@1`
- falsifier: —
- no-claim: Identity only. This establishes no semantic necessity for D, characteristic-zero obstruction, global MAX11 result, or completeness theorem.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0047@1 — boundary-claim [mathematics]

> Within the complete compressed degree-three pairwise Rueß dictionary on seven variables, there is a 113-term rational coefficient vector whose exact global normal form equals MAX7 and whose imposed G-0099 leaf/opposite-colour incidence image equals the dominant balanced two-component projection of the public MAX6 certificate. A fresh-context implementation independently reconstructed all 3,010 columns by literal 7! permutation enumeration, obtained exact rank 327 and nullity 2,683 for the complete 648-row system, and replayed the vector with zero residual on all rows.

- disposition: **open** · facets: UNCHALLENGED · trace:baf680db
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0047@1`
- falsifier: One omitted degree-three orbit or primitive hinge, one different exact rank, a nonzero semantic or incidence residual of the 113-term vector, a failed direct MAX7 evaluation, a broken orbit double count, or survival of any planted sign, incidence, coefficient, or target mutation.
- no-claim: The incidence target was imposed rather than derived from a semantic restriction. This result is an exact lower-arity potency control, not an n=6-to-7 induction theorem, MAX11 identity, evidence that the analogous n=10-to-11 joint system is feasible, or an unrestricted-network theorem.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0048@1 — implementation-claim [mathematics]

> G-0102 clean-room audit of the G-0099 lower-dimensional potency gate is identified by standalone auditor SHA-256 7ca056bddc7695222114e61b87c5e726bb96bc7803847c69baf8f57191166169, frozen G-0099 manifest SHA-256 508d4cec92e18da90f889bfbc1e4e34f73db5d56ee66bc0f65d21ee0a1b87121, and deterministic audit receipt SHA-256 dbc043aa9954f1cf76ae6ba28f8925a1ef687943a539a6c48048baafe7441d33.

- disposition: **open** · trace:10548e0c
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0048@1`
- falsifier: —
- no-claim: Identity only. This same-model-family clean-room implementation establishes neither semantic necessity of the imposed incidence nor any MAX11 or unrestricted-network result.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0049@1 — theorem-attempt [mathematics]

> At ambient dimension eleven, the 17 frozen signed-mass-four, support-six G-0187 basis columns 12, 15, 17, 21, 24, 28, 68, 72, 75, 82, 87, 90, 91, 108, 117, 121, and 122 are exact zero complete symmetrized piecewise-linear functions: every primitive hinge coefficient and all eleven linear coordinates cancel over the integers. The 17 coefficient relations are independent over Q because they are a subset of the certified G-0187 basis. Together with the three-dimensional retained signed-mass-at-most-three subkernel placed in O by G-0185, exactly 20 independent directions of the 478-dimensional retained restriction kernel are now classified in O, leaving 458 global directions unclassified.

- disposition: **supported** · facets: UNCHALLENGED · trace:8cdd952e
- evidence class: **INDEPENDENTLY_REPLAYED** · ceiling after dependencies: **INDEPENDENTLY_REPLAYED** · weakest link: `C-0049@1`
- falsifier: One nonzero complete hinge or linear residual in any listed relation; one mismatch between a listed relation and its frozen G-0187 basis column; rank below 17 for the listed coefficient vectors; one selected graph record or normal form differing under independent exact reconstruction; or survival of the hostile coefficient mutation.
- no-claim: This is a fixed n=11 finite theorem. It does not prove a parameterized graph-exchange identity, an all-n theorem, novelty, classification of the other 458 restriction-kernel directions, the full STAR quarantine, MAX11 representability or nonrepresentability, ansatz completeness, or an unrestricted two-hidden-layer ReLU lower bound.
- next rung blocked by: INDEPENDENTLY_REPLAYED -> REFEREED: fresh-context referee verdict holds at tier T2+

### C-0050@1 — implementation-claim [mathematics]

> The preregistered G-0189 complete-normal-form outcome is identified by combined scanner/library code SHA-256 b2e2ec00fe6c14620693176d33a2f9ac3d283670f519716419c394f1c8321df1, scanner executable SHA-256 4bab8c77304c4cd7de840a1ac7082d0b2b2d113842e0e97046cff8e54d5b152f, frozen sparse-basis input SHA-256 24ca642c27ab84508daee27a609483e860af09e8c28134cd00e859dbe443f4fe, and registered-result SHA-256 e90a79984c0dd7c582ca9dbbcb7f73b08c0c1505d0597bfcd98d44361ded8005.

- disposition: **open** · trace:ba177960
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0050@1`
- falsifier: —
- no-claim: Producer identity only. It is not an independent replay, proof-assistant formalization, parameterized theorem, novelty adjudication, or MAX11 conclusion.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0051@1 — implementation-claim [mathematics]

> The independent G-0109 replay of G-0189 is identified by combined audit-code SHA-256 eb8efd9968c6f12bd7d1e50657ee685f44cd0d0ef0fe65cf3a7b90cd9d4e87c3, historical G-0109 executable SHA-256 e487f78b5f8c4f2f5b3b7764abbb742c6b2a47007d78561e4e125fc829498426, exact 92-record audit-input SHA-256 67b4ada6a6c5b311de23ac7b5038ddd5940159cb7fda698f5db1b06c61aa2990, regenerated evaluator-output SHA-256 76a060bd88ac3bf6c46e5123b74cd701efff95b84c8335b0215c16d38bf595d4, and audit-receipt SHA-256 501bdfc8f6f406ea915e254caf6535bbfa101cd32cd6c8ef6afaaa8f7d5db014.

- disposition: **open** · trace:1e189307
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0051@1`
- falsifier: —
- no-claim: Replay identity only. This is a fresh-context, same-model-family T1 audit using a historical implementation-distinct evaluator; it is not T2 or human review, a proof-assistant formalization, a parameterized theorem, a novelty adjudication, or a MAX11 conclusion.
- next rung blocked by: ASSERTED -> CITED: retrieved citation with locator+excerpt

### C-0052@1 — theorem-attempt [mathematics]

> For the frozen 851-row retained signed-mass-at-most-four STAR restriction block with 6,795 integer coordinates, the rank over Q is exactly 808 and the left-kernel dimension is exactly 43. The frozen G-0190 43-column coefficient matrix consists of exact independent left-null vectors and therefore is a complete basis of that left kernel. Its first 42 columns are the listed G-0187 basis columns in order, and its last column is exactly B_24+B_174+B_235-B_295+B_345.

- disposition: **supported** · facets: UNCHALLENGED · trace:59934e89
- evidence class: **COMPUTED_BOUNDED** · ceiling after dependencies: **COMPUTED_BOUNDED** · weakest link: `C-0052@1`
- falsifier: One nonzero coordinate among the 292,185 exact C^T A equations; coefficient rank below 43; block rank over Q different from 808; one selected row, row-to-sequence map, candidate term, source-column lineage, or matrix byte differing from its bound value; or failure of the one-unit mutation control.
- no-claim: This finite restriction-matrix theorem does not classify the 40 genuinely mass-four directions into the old-primary function span O, prove the support-34 SMT minimum without trusting Z3, settle MAX11, establish ansatz completeness, or imply an unrestricted neural-network lower bound.
- next rung blocked by: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned) (+1 more)

### C-0053@1 — implementation-claim [mathematics]

> The G-0195 clean-room audit of the G-0190 filtration basis is identified by combined verifier/ranker code SHA-256 2f40804af58b87d2f137525835deb472c21d7c3412393fee41264c9a9b98849f, audit-receipt SHA-256 e3aa2e030fbc78d46acf994d0337b96a6a1555a8045643ba8850208f6f4967ef, compressed matrix SHA-256 84761d297bed5b5e8b6df399bf1b54cb4d99b03dbdb8674a23e6863989a46588, and decompressed matrix SHA-256 d57ec8abb9a843dc68327d88d0fe9c5843a055762cd3ae9f53ac45fb9eb50efd.

- disposition: **open** · trace:e4eb280b
- evidence class: **ASSERTED** · ceiling after dependencies: **ASSERTED** · weakest link: `C-0053@1`
- falsifier: —
- no-claim: Implementation and custody identity only. This is same-model-lineage T1 exact computation, not a T2 or human referee, a proof-assistant formalization, an old-primary classification, or a MAX11 conclusion.
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
- `D-0004` Reconstruct centered MAX11 from only the eleven independently translation-normal · scope: Exactly reconstruction criteria that discard independent nor · retry_when: `regime_boundary(face-data-retains-support-heights-or-global-wall-fan)` · trace:b4306f20
- `D-0005` Interpret the G-0099 leaf-edge/opposite-colour-edge deletion incidence as a repr · scope: Exactly the raw zero-extension on the complete n=5 degree-tw · retry_when: `regime_boundary(leaf-operator-defined-on-complete-semantic-quotient)` · trace:7b8f7884
- `D-0006` Seek MAX11 in the 22,265-column registered-plus-all-tree-plus-5E/5L dictionary w · scope: Exactly the frozen 8,427 semantic rows, 1,387 imposed incide · retry_when: `regime_boundary(incidence-constraint-proved-semantic)` · trace:72bd986a
- `D-0007` Repair the G-0179 STAR restriction rank deficiency by appending either 480 froze · scope: Exactly the 5,769 retained common-apex STAR records, origina · retry_when: `regime_boundary(characteristic-zero-star-kernel-quotient)` · trace:bfbe9e5a

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
- `EXP-0020` [complete] family `max11-same-component-complete-exact-price-vector-v2` arm — prereg=True · trace:331603cd
- `EXP-0021` [complete] family `max11-complete-same-component-native-schur-v1` arm — prereg=True · trace:03e0008a
- `EXP-0022` [complete] family `leaf-bridge-lower-dimensional-potency-v1` arm — prereg=False · trace:312a6efb
- `EXP-0023` [complete] family `leaf-bridge-semantic-status-v1` arm — prereg=False · trace:e5b8ff77
- `EXP-0024` [complete] family `max11-joint-semantic-incidence-v1` arm — prereg=True · trace:1e8b8933
- `EXP-0025` [complete] family `degree-five-full-dimensional-filter-v1` arm — prereg=False · trace:1ba2022b
- `EXP-0026` [complete] family `max11-full-family-member-global-replay-v1` arm — prereg=True · trace:3dd6654f
- `EXP-0027` [complete] family `max11-star-loop-quotient-rank-expansion-v1` arm — prereg=True · trace:d5504f6f
- `EXP-0028` [complete] family `max11-star-loop-exact-rational-kernel-v1` arm — prereg=False · trace:d462a681
- `EXP-0029` [complete] family `max11-star-loop-four-term-primary-lift-v1` arm — prereg=False · trace:250fd02c
- `EXP-0030` [complete] family `max11-star-loop-six-term-primary-lift-v1` arm — prereg=False · trace:c997dfd7
- `EXP-0031` [complete] family `max11-star-loop-third-six-term-primary-lift-v1` arm — prereg=False · trace:57e61560
- `EXP-0032` [complete] family `max11-retained-low-mass-star-kernel-quarantine-v1` arm — prereg=False · trace:62f36227
- `EXP-0033` [complete] family `max11-star-loop-exact-sparse-kernel-basis-v1` arm — prereg=False · trace:588eee71
- `EXP-0034` [complete] family `max11-mass4-sparse-exact-zero-identities-v1` arm — prereg=True · trace:06c365dd
- `EXP-0035` [complete] family `max11-mass-le4-filtration-exact-basis-v1` arm — prereg=True · trace:85641ae7
