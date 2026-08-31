# G-0123 exact-Q full-family master — T1 audit verdict

- Review completed: `2026-08-31T02:19:34Z` (final-source checks continued through the last committed hardening)
- Reviewer: `SageBridge` (Codex / GPT-5; fresh context, same model family, T1 only)
- Review preregistration: `artifacts/reviews/G-0123-full-family-master/REVIEW_PREREGISTRATION.md`, commit `c4c58f1`
- Subject preregistration SHA-256: `e7e2f6de986d839aef8614ae81d91357b34bccfb5b9ec065fd8aa5bd1a689952`
- Final subject source: `artifacts/math/G-0123/full_family_master.py`
- Final subject source SHA-256: `dc77467b31c12b40eaec8b33bbe806d0c6f2ea8e2dac3f2731324deb3c1b9cac`
- Final subject commits: `4a7191f`, `8227416`, `e74e558`
- Exact-linear-algebra helper SHA-256: `ee422e6e36085e26ddd83a75f8901c6a6efbe3fd2a99e80e280f9449d0ed8281`

## Verdict

`PASS` for implementation readiness at the narrow preregistered meanings, with **no current correctness blocker found** in the final source SHA above.

This is not a scientific-result verdict. I did not run the manifest builder or scientific master, and I did not inspect any future scientific result. The clearance means that, if the bound-input validators pass and the frozen source is the source the manifest names, the two terminal branches have the following exact meanings:

- `FULL_FAMILY_EXACT_Q_MEMBER`: exact membership on the frozen 348 rows in the span of columns drawn from the frozen 163,740-record dictionary; only a finite-row candidate for separate global replay.
- `FULL_FAMILY_EXACT_Q_NONMEMBER`: an exact integer separator for that frozen dictionary on those frozen rows; only a bounded family no-go, not an unrestricted lower bound.

The review cannot promote either possible future outcome, cannot supply T2 independence, and cannot support a MAX11 theorem or Lean formalization.

## Claim-by-claim adjudication

| Obligation | Verdict | Basis |
|---|---|---|
| Exact 348-row statement and target | PASS | The code constructs 301 panel coordinates, 11 linear coordinates, 4 accumulated hinges, and all 32 Batch32 hinges. The target is the unscaled 301-vector, ten linear zeros, `11!` in the last linear coordinate, and zero on all 36 hinge rows. No prior candidate scale enters the target. |
| Batch32 row policy | PASS | All 32 rows are retained conservatively in receipt order. The manifest records each as `KEPT_CONSERVATIVELY`, with no dependency discard claimed. This is stronger than an unsafe restricted-row discard and is consistent with the 348-row question. |
| Exact arithmetic | PASS | Decision paths use Python integers, `Fraction`, and FLINT `fmpz_mat`/`fmpq_mat`. Modular residues are input-consistency checks only; neither membership nor nonmembership is decided modularly or by floating point. |
| Restricted-master invariant | PASS | The frozen seed is required to have exact rank 115. Each appended violating column is required to increase exact rank by exactly one. The loop budget `348 - 115` is therefore sufficient: either a full-family separator appears earlier or rank 348 forces membership. |
| Membership reconstruction | PASS | Exact pivot columns and exact independent coordinate rows yield a nonsingular rational solve; the result is replayed on all 348 rows before and after denominator clearing. Normalization divides coefficients and target scale by their common gcd, keeps the scale positive, removes zero terms in the receipt, and rejects a `+1` coefficient mutant. |
| All-column nonmembership | PASS | A primitive, sign-normalized exact left-null separator with independently checked nonzero target pairing is scanned over `range(163740)` in sequence order. Only a scan returning no violation emits nonmembership. The final sequence is visited; a null return has census 163,740. A `+1` separator mutant must break annihilation or kill the target pairing. |
| Cache and record-order semantics | PASS | The consumer rehashes the 788,571,840-byte cache, checks its exact size/layout/endianness/i128 receipt, validates the transitive panel-input/row/evaluator/gate/scan/producer/preregistration bindings, checks record sequences `0..163739`, and bridges the scan and cache digests. |
| Replay and exact-price receipts | PASS at code-contract level | Both whole receipts are fixed inputs. The validators check exact binding-key sets, candidate identity and scale, both Batch32 primes, complete census fields, accumulated/linear checks, strict signed-lexicographic selected order, selected digest, exact price dimensions/order, every per-row and aggregate stream digest, and exact integer residual-to-modular bridges. Actual receipt acceptance remains a runtime precondition of the manifest build. |
| Accumulated coordinates | PASS | Each of four fixed documents is schema/direction/count checked; hinge and linear i64 streams are rehashed, all four linear streams must match the Batch32 price stream, and the candidate must have exact zero residual on every accumulated hinge. |
| Manifest and stale-source custody | PASS | The builder and runner use fixed contained paths; reject duplicate/resolved-duplicate inputs, malformed hashes, stale source/manifest/input bytes, noncanonical paths, dimension/protocol/seed/residual/direction drift, and output overwrite. Final writes pre-serialize, fsync a temporary file, and atomically hard-link without replacement; serialization failure leaves no final-path artifact. |
| Runtime reachability | PASS | Static call-graph probing confirmed that cache, receipt, accumulated-coordinate, seed, manifest, separator, stale-digest, and exclusive-write guards are on the actual `build_manifest` or `run` paths, not dead helper code. |
| Claim boundary | PASS | Both result strings explicitly refuse global identity, family completeness, unrestricted MAX11 lower bounds, and theorem status. |

## Independent probes

All probes were run against source SHA `dc77467b31c12b40eaec8b33bbe806d0c6f2ea8e2dac3f2731324deb3c1b9cac` without invoking the scientific run.

1. Subject self-test: `PASS (15 hostile mutations rejected)`.
2. Independent Fraction/FLINT cross-check: 500 random rank comparisons; 246 randomly encountered nonmember cases produced primitive, sign-normalized, target-separating exact left-null vectors; 499 nonzero-rank member cases survived independent pivot extraction, exact solve, denominator clearing, and all-row replay. The explicit scan probe detected a violation only at the fifth and final column, and a separate null probe visited the entire region. Probe digest: `eeb7adf637da9db6875e67c8117928470733a2506fec447520f21a53b4b86e80`.
3. Runtime-reachability probe: all precommitted guards were direct calls on the build/run dispatch paths. Probe digest: `3e49fdc7711b9471418b839bf4fa1b492f976ebd61c23e9a6d8774ffaa13f28e`.
4. Synthetic manifest/custody probe: a valid manifest was accepted; solver, duplicate-input, dimension, seed, residual, and Batch32-direction mutations were rejected; exclusive creation and serialization-abort cleanup held. Probe digest: `c8cee9a2c9b0ee7f2c07c9f334134e306acbcb3c9a0261d50484bb65926dee11`.
5. Panel-seed probe: the frozen panel primes are `2,000,081` and `3,000,017`, distinct from the Batch32 primes; both panel bases agree, contain 115 sorted unique sequences, and pass `load_panel_seed`. Probe digest: `03fedab8aac9621040e64d4c3d1f20df33da414b1a79b9ac6634f64324c25a12`.
6. Toolchain observation: project `.venv` reports CPython `3.13.7` and `python-flint 0.9.0`, matching `TOOLCHAIN.md`; `requirements-solvers.lock` SHA-256 is `dae95ec0dd59c0b30ea69bfe541248049cee612a92d56c4d18e0c3217c170fb8`.

## Audit yield and correction history

The review was not ceremonial. The initial draft (`19141f2b…`) had three execution-blocking protocol defects: dead cache-receipt validation, incomplete replay/price transitive validation, and a hostile suite that did not exercise most preregistered failures. It also accepted several stale-manifest mutations and could leave a partial final-path file after serialization failure. Those defects were repaired before the final source was frozen.

A later full input-validation pass exposed a distinct protocol bug: the panel bases use primes `2,000,081` and `3,000,017`, while Batch32 uses `1,000,000,007` and `1,000,000,009`. Commit `8227416` separated those constants. Commit `e74e558` then made the exact initial-rank, unit-rank-increase, and separator normalization invariants executable. The verdict applies only to the final SHA, not any superseded draft.

## Residual risks and mandatory next obligations

1. **Commit/hash discipline:** the manifest must name exactly source SHA `dc77467b…`; any source edit invalidates this clearance and requires at least a diff-focused re-audit plus self-test.
2. **Runtime input gate:** any failure while building the manifest is a hard stop. This review did not substitute for that full receipt validation.
3. **Environment evidence:** the project toolchain is pinned outside the scientific manifest. When the result is entered into the campaign ledger, bind the environment, code, and artifact digests required for computation-grade evidence.
4. **Executable provenance:** historical producer executable digests are locally attested but the binaries are not archival proof of source equivalence. The exact bridges reduce the correctness dependence, but they do not create clean-room replay standing.
5. **Result review:** whichever branch appears must receive an independent artifact-level replay. A member requires complete binding-clean global exact replay; a nonmember requires an independent all-163,740-column separator replay.
6. **Formalization boundary:** Lean work may formalize only a statement already established and statement-matched. A 348-row member or frozen-family nonmember must not be wrapped into a global MAX11 theorem.
7. **Independence ceiling:** this review is T1. It cannot satisfy the campaign's T2 requirement for a bottom-line mathematical claim.

No blocker remains for building the sealed manifest and then executing the preregistered exact master once.
