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
- open gaps: G-0002, G-0005, G-0006
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

## Routes

- `H-0001` [active] MAX_11 may lie in the exact rational span of the frozen pairwise-atom family.
- `H-0002` [active] A registered lift, orbit law, or simplex subdivision may extend arity without added depth.
- `H-0003` [active] A registered real-weight invariant may obstruct MAX_11 under two-layer composition.
- `H-0004` [proposed] A normal-form theorem may reduce unrestricted MAX_n representations to finite certificates.

## Experiments (multiplicity ledger)

- `EXP-0001` [complete] family `bootstrap-toolchain-controls-v1` arm — prereg=False · trace:6c210206
- `EXP-0002` [planned] family `known-max-cleanroom-v1` arm — prereg=True · trace:b9472094
