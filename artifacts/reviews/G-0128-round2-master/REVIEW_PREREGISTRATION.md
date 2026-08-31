# G-0128 round-2 exact-Q master — adversarial review preregistration

- Frozen at: `2026-08-31T03:13:00Z`
- Reviewer: `MagentaEagle` (Codex / GPT-5; fresh context, same model family, T1 only)
- Mode: read-only source/manifest audit with synthetic hostile probes
- Subject protocol: `artifacts/math/G-0128/FULL_FAMILY_MASTER_ROUND2_PREREGISTRATION.md`
- Subject source: `artifacts/math/G-0128/full_family_master_v2.py` (eventual frozen SHA recorded in the verdict)
- Audited ancestor: G-0123 source SHA-256 `dc77467b31c12b40eaec8b33bbe806d0c6f2ea8e2dac3f2731324deb3c1b9cac`
- Forbidden before source clearance: building, running, or inspecting `full_family_master_result_v2.json`, and any inference from that result

## Exact review question and boundary

Does the eventual frozen source implement the preregistered 380-row exact-rational all-column master such that either terminal branch proves exactly its narrow statement, while every malformed, stale, partial, reordered, or semantically inconsistent input fails closed?

The strongest admissible clearance is implementation readiness for:

- exact membership of the fixed 380-row target in the span of the fixed 163,740 T1-family columns; or
- exact nonmembership on that same frozen system, certified by an integer separator annihilating all 163,740 columns with nonzero target pairing.

This review cannot establish a global/MAX11 identity, family completeness, an unrestricted lower bound, a Lean theorem, `REFEREED` standing, or T2 independence. A member still requires separately preregistered complete global replay; a nonmember remains a bounded frozen-dictionary obstruction.

## Frozen source-clearance obligations

1. **Exact row system.** Reconstruct and assert the exact order `301 panel + 11 linear + 4 accumulated + 32 old Batch32 + 32 new G-0126/G-0127 = 380`, with all 64 Batch32 decisions `KEPT_CONSERVATIVELY`, no dependency discard, and no order-changing abstraction.
2. **G-0126/G-0127 custody.** Rehash the complete G-0121 expected-input set and the G-0126/G-0127 protocol, source, Cargo, executable/receipt, panel, candidate, and kernel bindings. Require exact binding key sets; exact 32-row receipt order; both frozen selected digests; `32*163740` hinge and `163740*11` linear entries; per-row and aggregate digests; extrema/nonzero censuses; and old/new source distinction.
3. **Exact bridge and dots.** Independently recompute the 131-term candidate dot product on every new hinge row and require canonical equality to the matching nonzero G-0126 exact residual, ordered-prime reductions, and frozen decimal-LF digest. Independently recompute each linear dot, requiring ranks 0–9 zero and rank 10 equal to `target_scale*11!`.
4. **Warm start.** Require 156 sorted unique G-0121 `selected_sequences`, equality with `support_sequences`, valid bounds, exact selected-basis signed-i128 digest on the first 348 rows, exact replay of the old scaled member, and exact rank 156 both before and after appending the 32 new coordinates.
5. **Target construction.** Build the unscaled target afresh: frozen 301 panel entries, ten zeros, `11!`, then 68 hinge zeros. Reject reuse of the G-0121 denominator-cleared target scale or any row-count/order mismatch.
6. **Exact decisions.** Trace all rank, nullspace, solve, normalization, pairing, and replay decisions to integer/Fraction/FLINT exact arithmetic. Modular arithmetic may only validate bridges.
7. **Rank-growth invariant.** Start with rank 156; every appended first-violating column must be new and increase exact rank by exactly one; permit iterations 0 through 224 inclusive and refuse exhaustion or skipped checks.
8. **All-column scan.** Scan sequences exactly in `range(163740)` order, including the last sequence, with complete 380-coordinate columns and exact prices. Nonmembership is reachable only after a zero scan with census 163,740; exceptions or partial scans cannot be converted to success.
9. **Member branch.** Select independent columns and coordinate rows, solve over Q, replay all 380 rows before and after denominator clearing, remove zero terms, divide by the joint gcd, normalize positive scale, bind coefficients to support positions, emit the full selected-basis digest, and require a `+1` coefficient mutant to fail a real row equation.
10. **Nonmember branch.** Emit a primitive sign-normalized 380-entry integer separator only after independently checking nonzero target pairing and all-column annihilation; require a `+1` separator mutant to break annihilation or kill pairing.
11. **Transcript and manifest.** Serialize every iteration with ranks, branch, separator fields, first violation and price, and exact scan census. Manifest schema/path must bind every frozen and transitive input, row policy/order, warm seed, target, source, preregistration, and both residual digests; duplicate or resolved-duplicate paths are fatal.
12. **Custody and atomicity.** Refuse stale source, preregistration, manifest, prior result, G-0127 receipt, or underlying expected-input bytes; contain all paths; refuse pre-existing outputs before expensive work; pre-serialize JSON; use an exclusive same-directory temporary, flush/fsync, no-overwrite atomic publication, directory fsync, and cleanup on serialization/write/link failure.

## Precommitted hostile probes

- Static call-graph/reachability audit for every validator on both `build_manifest` and `run` paths, plus ancestor-versus-v2 semantic diff.
- Exact off-by-one scan probes with the sole violation at the final column and with a truly null scan; loader exceptions must propagate.
- Synthetic rank/member/nonmember cross-checks against an independent `Fraction` implementation, including a non-unit-rank mutant and coefficient/support permutation.
- Mutations of new-row order, truncation, duplication, record order, direction, residue, exact residual, per-row digest, aggregate hinge digest, linear digest, extrema, nonzero census, and every transitive binding.
- Old/new Batch32 source swap and concatenation-order swap; 348-row false member made false only by a new row.
- Warm selected/support mismatch, seed reorder/duplicate/out-of-range, basis digest mutation, old term/coefficient/scale mutation, and target-scale contamination.
- Member `+1` and separator `+1` mutants checked through terminal arithmetic, not digest-only helpers.
- Cache truncation, ragged 380-row column, duplicate/resolved-duplicate manifest input, path escape/symlink escape, stale source/prereg/manifest/receipt/input, pre-existing output, and serialization/write/link abort cleanup.

## Verdict rule

`PASS` requires every obligation above to be reachable and every hostile probe to fail in the intended direction on one recorded frozen source SHA. `CONDITIONAL_PASS` permits only a named non-scientific repair followed by re-audit. Any reachable terminal false positive is `FAIL`; lack of enough source evidence is `INCONCLUSIVE`. Source edits after clearance invalidate the verdict. Scientific output remains unopened until source clearance is recorded.
