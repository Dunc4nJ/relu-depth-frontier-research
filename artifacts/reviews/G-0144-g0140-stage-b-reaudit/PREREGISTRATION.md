# G-0144 preregistration — G-0140 Stage-B repaired-source re-audit

- Frozen at: 2026-08-31T19:03:00Z
- Auditor: `BronzeRobin` (`openai-gpt-5` lineage; fresh context; T1 ceiling)
- Mode/domain/route: outcome-blind W2 source-and-custody audit; mathematics; no scientific execution
- Exact subject commit: `25629769a711c286d867969653b7ad398d64e87a`
- Subject tree: `artifacts/math/G-0140/stage_b_pricer/**`
- Intended consumer: the G-0140 research lead and the one-shot manifest gate
- Gate: Stage B may not enter the one-shot Pool128 execution unless this exact repaired revision receives an independently produced PASS receipt
- Observed defect class: G-0142 found permissive nested record admission and insufficient G-0141/G-0142 audit-receipt semantics; the repaired revision claims to close both
- Retirement condition: this audit ceases to govern when the subject bytes or executable change, or after the exact revision is accepted/rejected and the one-shot decision is made

## Frozen question

Does the committed Stage-B source and release executable at the exact subject revision correctly and fail-closedly implement the preregistered Stage-A-to-Stage-B coordinate-pricing interface, including the two repaired admission contracts, while preserving custody and without itself producing an outcome-bearing scientific result?

## Contamination and no-run boundary

The auditor will not inspect Stage-A or Stage-B scientific result artifacts, run Pool128 pricing, infer priced coordinates, inspect selected directions, or search for a replacement result. Allowed execution is limited to source inspection, compilation/custody comparison, producer self-tests, static preflight, parser/interface-only fixtures, and hostile mutations whose outputs cannot reveal the scientific outcome. The subject tree is read-only.

## Obligations and decisive falsifiers

PASS requires every obligation below. One decisive failure yields FAIL; it will not be severity-shopped or repaired inside this audit.

1. **Exact-subject and compiled-byte custody.** The audited source and tracked release executable must be read from commit `25629769a711c286d867969653b7ad398d64e87a`; hashes must be recorded. A clean isolated rebuild must either reproduce the tracked release bytes or the producer must furnish a pinned, independently checkable compiled-byte binding that detects substitution. The executable must refuse source/binary drift before any scientific path.
2. **Strict nested record admission.** Every admitted `Candidate`, Stage-A record, `AccumulatedDirection`, and panel `Record` object—including each nested representative—must reject unknown fields. Hostile one-field injections at every layer must fail. A positive fixture matching the real 163,740-record panel/candidate schema must still parse, so strictness cannot be bought by rejecting legitimate input.
3. **Exact audit-gate semantics.** G-0141 and G-0142 gate checks must require their exact schema identifiers and exact `PASS` result. They must reject a schema lookalike, a missing/alternate result, and a correctly shaped current `FAIL` receipt. Exact hash/commit/path bindings must be checked where the manifest contract assigns them.
4. **Positive A→B interface.** Stage B must consume Stage A's actual committed output key/shape contract, not merely a synthetic cousin. Key names, counts, hashes, ordering, candidate/panel nesting, and the Stage-A output schema must agree. The positive interface check must reach the same production parser and validation path used before pricing.
5. **Arithmetic and census path.** Source inspection and bounded fixtures must establish that all `128 × 163740 = 20,958,720` cells are traversed exactly once in canonical pool-row-major/candidate-minor order; counts reconcile; the signed dot product uses a checked `i64` bridge into `BigInt` without overflow or lossy conversion; malformed dimensions/counts/order are rejected.
6. **Output custody.** Output creation must be exclusive/no-overwrite, all bound inputs must be rehashed at the end, and mutation between entry and exit must refuse success. Partial/truncated output must not masquerade as a valid receipt.
7. **Executable tests at committed bytes.** The committed test suite, release self-test, and static preflight must all run non-vacuously. Independent hostile fixtures must demonstrate red directions for obligations 2, 3, 4, and 6. No ignored tests, weakened assertions, regenerated goldens, source edits, or hard-coded success are allowed.

## Planned evidence

- Inspect `git show`/`git ls-tree` at the exact subject commit and hash each admitted producer byte.
- Materialize an isolated temporary checkout of exactly the subject commit; do not modify the shared producer tree.
- Read Stage-B source and the Stage-A producer's actual output struct/key contract at that same revision.
- Run the committed Rust tests, self-test, and static preflight only.
- Add an independent audit harness under this G-0144 directory that exercises parser/gate/custody logic through non-scientific fixtures and carries at least one must-fail mutation per repaired defect class.
- Record exact commands, observed exits, counts, and SHA-256 values in the final receipt; independently validate the receipt's internal hashes before issuing the verdict.

## Verdict rule and claim boundary

- `PASS`: all seven obligations hold at the exact subject revision.
- `FAIL`: any obligation fails or cannot be verified from committed bytes without executing outcome-bearing science.
- `CANNOT_VERIFY`: required bytes/tooling are unavailable or the exact revision cannot be reconstructed.

Even PASS certifies only source/custody and positive interface readiness for Stage B at this exact revision. It does **not** certify a scientific pricing result, target membership, family completeness, MAX11, any unrestricted two-hidden-layer ReLU theorem, or T2 independence.
