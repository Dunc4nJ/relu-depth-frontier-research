# G-0118 iteration-4 Batch32 adversarial replay preregistration

## Review identity and contamination

- Reviewer: `PeachGull` (Codex, same model lineage as producer; at most T1).
- Mode: fresh-context adversarial review of an existing bounded computation.
- Frozen repository baseline: commit
  `e694b5fb8190d97b69c226a71f12aeb9bb137e7c`.
- Producer commits named in the assignment: `a3c5f82` and `e694b5f`.
- I inherited the headline that these commits contain a candidate-4 Batch32 global
  modular replay and an exact-price artifact, plus partial expected SHA-256 prefixes
  `c402c0...` and `349e63...`. This prevents discovery-blind review. The audit is
  therefore a correctness/provenance replay, not an independent discovery.
- Before writing this preregistration I inspected only repository metadata (HEAD,
  worktree status, the producer commits' path names) and ran `./skill-runtime
  verify-quick`; I did not open the scientific payloads.

## Frozen review scope

Read-only producer objects:

1. `artifacts/math/G-0118/iteration4_batch32_global_modular_replay_v1.json`
2. `artifacts/math/G-0118/iteration4_batch32_exact_prices_v1.json`
3. `artifacts/math/G-0118/ITERATION4_BATCH_HANDOFF.md`
4. Their recursively named candidate, manifest, source, and cache dependencies.

Writable scope is restricted to
`artifacts/reviews/G-0118-iteration4-batch/**`.

## Claims under test

This review will test only the following bounded claims:

1. The replay is bound to the intended iteration-4 candidate and complete frozen
   enumeration, with every declared input digest and count reconciling.
2. The four accumulated directions d1--d4 have zero candidate residual modulo both
   frozen primes.
3. The selected 32 directions are exactly the first 32 directions satisfying the
   preregistered nonzero-residual rule in the declared canonical ordering.
4. Every one of the 32 exact price rows has the declared order, length, record census,
   coefficients, and candidate dot-product residual; the linear target row is correct.
5. The producer artifacts and all relevant dependencies have the declared hashes and
   are attributable to the frozen commits.

No outcome can establish a global MAX11 identity, unrestricted family completeness,
novelty, a theorem, T2 independence, or formalization readiness.

## Independent implementation plan

The review implementation will not call the G-0117 pricing or replay kernel as its
sole verifier. It will:

1. Parse and validate JSON shapes with duplicate-key rejection and exact integers.
2. Re-derive the canonical record census/order directly from the frozen mathematical
   record specification or from an independently audited raw cache format.
3. Re-transcribe the hinge coefficient from the mathematical definition and compute
   it by a disjoint algorithm (integer subset/dynamic-program accumulation, not the
   producer helper). Symmetry reduction, if used, will be independently justified.
4. Recompute all 32 directions across all 163,740 records when feasible. If resource
   limits prevent this, the report will state the exact sampled indices/directions and
   will not certify unexecuted rows.
5. Recompute all 32 candidate dot products and target residues with Python arbitrary
   precision integers/rationals, independently of producer summaries.
6. Recompute d1--d4 modular residuals and independently validate first-32 selection;
   if a full labelled global replay is prohibitively expensive, the exact omitted
   coverage will remain an explicit obligation rather than being inferred.

## Frozen controls and kill conditions

- Hash mutation: one-byte mutation of each principal producer payload must change its
  digest and be rejected by the verifier.
- Coefficient mutation: add one to a nonzero candidate coefficient; at least one
  independently recomputed row residual must change.
- Direction mutation: alter one coordinate of a selected direction; the independent
  price vector or residual must change.
- Order mutation: swap two directions or two record rows; the binding/order check must
  fail even if the multiset is unchanged.
- Census truncation: remove the last record or last direction; exact counts and digest
  binding must fail.
- Arithmetic cross-check: at least one small instance is evaluated by literal subset
  enumeration and by the independent dynamic program; disagreement kills the kernel.

Any dependency hash mismatch, unexplained record-order mismatch, nonzero d1--d4
residual, incorrect first-32 selection, or one incorrect exact price/dot product makes
the relevant claim `INCONSISTENT`. A fully matching run supports only a same-lineage T1
clean-room consistency verdict for the bounded artifacts.
