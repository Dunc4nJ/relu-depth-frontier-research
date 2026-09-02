# RESEARCH CHARTER — relu-depth-frontier-research

**Created:** 2026-08-29T04:42:21Z · **Skill:** frontier-research-with-epistemic-humility v1.0.0-rc.1 · **Domain:** mathematics, translated subfield `exact-neural-representation` · **Route:** W1 dual prove/refute

## Exact target

For every integer `n >= 1`, there exist finite positive integers `m1,m2`, real matrices and biases
`W1 in R^(m1 x n)`, `b1 in R^m1`, `W2 in R^(m2 x m1)`, `b2 in R^m2`, `a in R^m2`, and `c in R` such that, for every `x in R^n`,

`max_i x_i = a^T ReLU(W2 ReLU(W1 x + b1) + b2) + c`,

where ReLU is applied coordinatewise as `max(t,0)`. Widths may depend on `n`; weights are unrestricted real numbers; equality is global and exact. The first campaign rung is the instance `n = 11`.

## Success object / failure object

- **First-rung success:** an explicit finite MAX11 network or algebraically equivalent certificate, with an audited conversion to the exact architecture, exact arithmetic verification, deliberate corruption controls, and clean-room replay.
- **Terminal success:** a proof for every `n`, preferably a scalable construction/normal form rather than isolated certificates.
- **Refutation:** one explicit `n` with an unconditional proof that no finite two-hidden-layer network over real weights represents MAX_n globally and exactly.
- **Meaningful intermediate:** a new infinite family, strict structural compression, a theorem reducing unrestricted search to a complete finite certificate class, or a lower bound that removes a genuine unrestricted route.

## No-claim boundary

Success here would not establish trainability, learnability, optimization efficiency, generalization, robustness, useful parameter count, approximation rates, or a practical ML architecture. A MAX11 witness would not prove all `n`. Failure of the Rueß pairwise-comparison/symmetric ansatz, any rational-only search, or any bounded-width family would not prove the unrestricted target false. Floating residuals are discovery signals only. Rational certificates prove existence over reals; absence over rationals does not prove absence over reals. CPWL consequences require the exact generalized-hinging hypotheses and dimension bookkeeping.

## Intended decision

Decide whether to invest the campaign in (a) a scalable constructive shallow-ReLU theory, (b) an unrestricted lower-bound/invariant program, or (c) consolidation because the first rung has been independently settled. A promotable result should be suitable for expert external review and eventual formalization.

## Budget

- Aggregate research-token ceiling: 1,000,000
- Initial wall-clock authorization: 14 calendar days
- Round budget: 24 substantive rounds
- Named-frontier floor: at least 10 substantive rounds unless decisive evidence settles or kills the target
- External paid compute or publication action: requires human approval; local CPU/storage are authorized

Budget exhaustion forces consolidate-or-extend. It never licenses an unlogged continuation or a lower evidence bar.

## Minimum review bar

Load-bearing promotion requires tier T2. At bootstrap that bar is unavailable and must fail closed.

- Author family: `openai-gpt-5`
- Counted as different: a named human referee, or a future explicitly authorized genuinely different model lineage
- Same-lineage and not different: GPT-5/Codex size tiers, snapshots, reasoning-effort settings, and parallel panes
- Cross-family transport bound: `NONE` at bootstrap

Therefore every `LOCKBOX_CONFIRMED`/`REFEREED` promotion and every bottom-line final claim emits `TYPED_REFUSAL` until a valid different-family or human-referee record exists. Volume of same-family review cannot lift this cap.

## Prior material

Prior target-selection notes, ansatz counts, scripts, and a pinned upstream checkout from `/home/ubuntu/obsidian-vault/Knowledge/ML Research/Autonomous Research/resources/papers/frontier-math-targets` are imported under `imports/target-selection-2026-08-27/`. They remain quarantined (`author_path` prefixed `import/`) until re-authored through native controls. Primary papers are independently re-retrieved where possible rather than trusted by inheritance.

## Binding field pack

`NEURAL_REPRESENTATION_EPISTEMICS.md` is the W11 translation binding this uncovered mathematical subfield, together with `domains/mathematics.md`. The nearest shipped algebra field file is advisory only where its exact-arithmetic and certificate discipline transfers.

## Compute authorization (2026-09-02, human decision)

Duncan authorized external paid compute on 2026-09-02 (Vast.ai, no spending cap, account auto-refills), with the orchestrator (AmberBluff) handling instance selection, creation and teardown, favouring quality and speed, and destroying any instance no longer needed or found too slow. This satisfies the "External paid compute ... requires human approval" clause above for the MAX11 campaign's rank, lift and pricing runs.
