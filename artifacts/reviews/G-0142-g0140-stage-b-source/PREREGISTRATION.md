# G-0142 preregistration — G-0140 Stage-B source/custody audit

- Registered UTC: `2026-08-31T18:23:19Z`
- Auditor: `CobaltSpire` (`codex`, `gpt-5-codex`; same model family as campaign authors, therefore at most T1)
- Mode: outcome-blind, read-only source/custody audit
- Subject commit: `f603a6b8e51e31b810d957176836da52142aa0a9`
- Subject purpose: exact Pool128-by-163740 hinge-coordinate pricing for G-0140 Stage B

This document is frozen before the auditor reads the Stage-B implementation or runs an audit
checker. It authorizes no scientific pricing run and no consumption or creation of the future
G-0140 manifest or scientific outputs.

## Immutable subject

The audit binds these paths at the subject commit and the corresponding current worktree bytes:

1. `artifacts/math/G-0140/stage_b_pricer/src/main.rs`
   - preregistered SHA-256: `2b09a0c36d060c7cbc03fb26009cb9bba0c49ef0c14ff7d24ec52f4f6294b09b`
2. `artifacts/math/G-0140/stage_b_pricer/Cargo.toml`
3. `artifacts/math/G-0140/stage_b_pricer/Cargo.lock`
4. `artifacts/math/G-0140/stage_b_pricer/target/release/g0140-stage-b-pool128-pricer`
   - preregistered SHA-256: `13d24a884b3714f803bb1b79d879527ed4f99445788debe7922a5c53054cc79e`

The receipt will record SHA-256 for every item. The two Cargo-file expectations are the exact Git
blobs at the subject commit; they are not inferred from a mutable working tree. Any absent file,
worktree/commit byte mismatch, provided-hash mismatch, or end-of-audit rehash mismatch is a FAIL.

## Claim under audit

The frozen Stage-B producer is eligible to be placed behind a future G-0140 manifest gate only if
static inspection and bounded non-scientific controls establish all of the following:

- it consumes the exact G-0140 Stage-A Pool128 interface and canonical full-family records;
- it computes each coordinate as an arbitrary-precision signed-integer dot product, without a
  narrowing bridge, for exactly `128 * 163740 = 20,958,720` cells;
- direction-major and record-minor ordering is canonical and explicit;
- its output schema and input schemas are strict, with exact cardinality, digest, order, and gate
  checks rather than permissive or partial acceptance;
- it checks the G-0139 result gate, the Stage-A source-audit gate, Stage-A result/custody bindings,
  its own compiled-byte custody, and the future one-shot manifest before scientific work;
- it refuses pre-existing output, writes exclusively/atomically or with equivalent no-overwrite
  semantics, and rehashes load-bearing inputs/executable at the end;
- its self-test includes positive known-answer coverage plus hostile controls that must fail;
- its claim remains narrow: source/custody fitness is not a scientific result, a complete pricing
  replay, target membership, a lower bound, or a theorem.

## Falsifiers and hostile controls

Any one of these is sufficient for FAIL unless the item is genuinely inapplicable and the receipt
explains why:

1. Mutating any bound subject byte is accepted.
2. A compiled executable not byte-bound to the manifest/source is accepted.
3. A missing or malformed G-0139, G-0141, Stage-A, or self-source gate is accepted.
4. A scientific manifest/output is required or consumed by the audit itself.
5. An out-of-range Pool128 direction or an order permutation is accepted.
6. A family record is skipped, duplicated, reordered, or priced in direction-minor order.
7. A dot product crosses `i64`/`i128` bounds and is silently narrowed or wraps.
8. A short census (`<20,958,720` cells), extra cell, or digest mismatch is accepted.
9. A pre-existing Stage-B output can be overwritten or reused.
10. An input/executable mutation between initial validation and final custody check goes unnoticed.
11. Unknown JSON fields or schema/result-name drift are silently accepted where strictness is
    load-bearing.
12. Self-test/preflight reports success while exercising zero relevant checks.

## Allowed evidence and execution boundary

Allowed:

- read-only source inspection at the exact subject commit/current matching worktree;
- hash, Git-object, executable-format, and dependency-lock inspection;
- the producer's self-test and a static/preflight-only mode that does not read a future scientific
  manifest or Stage-A scientific output;
- an independent checker self-test over synthetic/source-level fixtures, including must-fail
  mutants; compilation required solely to run those bounded checks.

Forbidden:

- creating, opening, parsing, or otherwise consuming the future G-0140 one-shot manifest;
- creating, opening, parsing, or otherwise consuming G-0140 Stage-A/Stage-B scientific outputs;
- running the `128 x 163740` pricing computation or any substitute scientific computation;
- modifying Stage-B or repairing a discovered defect in this audit.

If a forbidden future artifact already exists, the auditor records existence only, does not open
it, and stops the affected check. The required receipt fields are
`scientific_manifest_observed=false` and `scientific_output_observed=false`; otherwise the audit
cannot PASS under this preregistration.

## Verdict rule and receipt contract

The checker emits exactly one receipt at
`artifacts/reviews/G-0142-g0140-stage-b-source/SOURCE_AUDIT_RECEIPT.json` with schema
`max11-g0142-g0140-stage-b-source-audit-v1` and explicit `PASS` or `FAIL`.

PASS requires every applicable claim item and hostile control above to pass, both absence flags to
remain false, and the final byte rehash to equal the initial bindings. The receipt must nest the
subject commit, path, Git blob/object identity where applicable, SHA-256, size, and executable
binding rather than flattening these into an unauditable narrative. FAIL is the default on any
parse error, unsupported mode, missing evidence, or checker exception.

Independence limitation: even PASS is same-campaign, same-lineage T1 evidence. It establishes only
that this frozen source/executable passes this bounded audit. It does not independently replay the
scientific pricing output and cannot promote any mathematical bottom line to T2, REFEREED, or
FORMALIZED standing.

## Anti-ceremony creation gate

- Boundary: humans and the future campaign gate read this audit, so it is process rather than
  product runtime state.
- Consumer: research leader `RainyGorge`, who explicitly requested G-0142, and the future G-0140
  manifest-sealing decision.
- Gate: Stage-B scientific pricing must not be authorized from this frozen producer unless G-0142
  passes.
- Observed defect class: this campaign already caught a nearby semantic overclaim (`rank=204` was
  target-sufficient selected-column rank, not 412-row rank), demonstrating that field/interface
  semantics require independent binding before promotion; the operator explicitly requested this
  audit for that class of source/custody drift.
- Deletion/retirement condition: this receipt ceases to be a controlling gate when any bound
  Stage-B byte or subject commit changes; a new audit is then required. It remains only as historical
  provenance.
- Opportunity cost: the highest-priority capability is the exact G-0140 experiment, but one bounded
  source audit is its explicit authorization gate. No broader governance or second meta-audit is in
  scope.
- Verdict: `LEGITIMATE GATE`; build only the preregistration, one checker, and one receipt.
