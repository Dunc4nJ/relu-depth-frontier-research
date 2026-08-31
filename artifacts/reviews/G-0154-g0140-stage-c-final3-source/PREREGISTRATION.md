# G-0154 Stage-C final3 source/custody audit preregistration

## Audit identity and frozen object

- Audit: `G-0154`
- Reviewer: `IvoryKite` (`codex`, `gpt-5.4`), fresh same-lineage/T1 source reviewer
- Mode: outcome-blind, read-only W2 source/custody audit
- Frozen subject commit: `69a3449c7bc291f283c10c669e5d39f2a1212782`
- Preregistration path: `artifacts/reviews/G-0154-g0140-stage-c-final3-source/PREREGISTRATION.md`
- Planned receipt path: `artifacts/reviews/G-0154-g0140-stage-c-final3-source/SOURCE_AUDIT_RECEIPT.json`

At the time this preregistration was written, this reviewer had not opened, hashed, parsed,
diffed, imported, or executed any of the six Stage-C subject files below and had not inspected any
Stage-C scientific manifest or Stage A/B/C/D/E scientific output. The abandoned G-0152 review
also ended before any subject-byte access or preregistration artifact.

## Exact subject bindings

| Binding | Frozen path | Required SHA-256 |
|---|---|---|
| `selector_source` | `artifacts/math/G-0140/stage_c_selector/complete_matrix_rank_selector_v1.py` | `9c5e0e7e40c7f12b8d299148fa7f9a942207eacdc26aa6662c59bb86f481b9b0` |
| `native_proposer_source` | `artifacts/math/G-0140/stage_c_selector/ffpack_modular_pivots.cpp` | `198262e449c901f70b1e26cd260cbd5ade4e6eaf2868659e4cfd59a1ab72d9c7` |
| `native_proposer_executable` | `artifacts/math/G-0140/stage_c_selector/ffpack_modular_pivots_v1` | `207fcf88fe3f89c8119bd6b38037d9f0919165eecf04b48d1b0aaae039843171` |
| `native_build_receipt` | `artifacts/math/G-0140/stage_c_selector/ffpack_modular_pivots_v1.build.json` | `5157c020cc343de6bb891fb339a1027a9f8f3059aa03ea2a32722bc13d0fff76` |
| `native_test` | `artifacts/math/G-0140/stage_c_selector/test_ffpack_modular_pivots_v1.py` | `5d2b920f06100a2a7bd4069ebe4f009d4c2ba8aecea8872c9d4c58abe9296b94` |
| `launcher` | `artifacts/math/G-0140/stage_c_selector/run-stage-c-selector-v1` | `786b42f28d4720ca2578de78a3e312ce0186b8609d2b2c9c85c8f76bdd409d78` |

Binding discovery is closed: only these six named paths are subjects. Recursive discovery,
replacement files, displaced copies, later commits, and same-named decoys are outside the audit.

## Preregistered attack battery

1. **Custody and ancestry.** Resolve each path at the frozen commit; compare Git blob bytes,
   frozen-commit bytes, and working-tree bytes; verify all six required SHA-256 values and that this
   preregistration commit is a descendant of the frozen subject. Audit executable/build-receipt
   custody, compiler/link inputs, dynamic-link and runtime library identity rather than trusting a
   filename or receipt assertion.
2. **Exact G-0154 receipt contract.** Extract the frozen selector's declared schema, reviewer,
   preregistration, subject, required-check, and no-claim constants only after this preregistration
   is pushed. Require exactly the six named bindings and exact paths/hashes. Reject recursive
   binding discovery, unknown keys, forbidden `audit_git_commit`, duplicate JSON keys, trailing
   JSON, self-reference, displaced/decoy subjects, and any non-false scientific flag.
3. **Strict JSON primitive typing.** Verify that every required boolean is a JSON boolean, not a
   numerically equal integer (`0`/`1`), string, or other scalar. Mutation-control each relevant
   required-check and scientific/no-claim boolean so `1 == true` and `0 == false` cannot pass via
   Python equality. Retain a minimal reproducible counterexample if any typed mutation is admitted.
4. **Upstream receipt admission.** Verify exact G-0150 and G-0151 source-audit receipt custody,
   ancestry, shape, named bindings, and declared digests. Attack them with displaced subjects,
   decoys, unknown keys, duplicate keys, trailing JSON, and self-reference; no byte-identical or
   same-lineage receipt is treated as independent mathematical evidence.
5. **Complete-matrix contract.** Establish from source that the intended matrix shape is exactly
   `540 x 163740`; modular primes may propose a work order only; exact-rational completion scans the
   full column domain until every left-annihilator price is zero or exact full row rank is reached.
6. **Completion evidence logic.** Inspect completion-pass censuses and digest construction, exact
   nonzero-minor certification, and fail-closed accounting. Exercise synthetic false-modular-zero
   and omitted-column controls that a prematurely truncated or modular-only implementation must
   fail.
7. **Exact prefix and row selection.** Verify all prefix ranks derive from a complete exact basis,
   rank increments are only zero or one, the first 32 growing-pool rows are selected, and no
   modular selection result can substitute for exact selection. Exercise complete-basis and
   row-selection synthetic oracles in both positive and planted-negative directions.
8. **Dependent-row replay.** Verify every dependent row is checked through all 128 rows even after
   the admission cap; each gets either a compatible zero target or a primitive exact separator,
   with a full 163740-coordinate replay and nonzero target pairing. Recheck the earlier G-0143
   post-cap failure class with a synthetic planted violation.
9. **Source-mode fail closure.** Inspect argument parsing, hidden reads, output creation,
   overwrite/refusal behavior, temporary-file handling, end-of-run rehash, and error propagation.
   Exercise only the permitted source modes: project `.venv/bin/python ... --self-test`,
   `--static-preflight`, and the committed native small-oracle test. Any scientific/default mode,
   `--preflight`, future manifest access, or Stage A/B/C/D/E scientific-output access is forbidden.
10. **Statement and cousin boundary.** Test only source/custody clearance. Treat modular pivots as
    proposals, finite/synthetic controls as source tests, and source clearance as neither matrix
    membership nor any unrestricted or depth lower-bound result.

All executed commands will keep stderr visible. No test may be weakened, faked, regenerated to a
golden, or made green through a hard-coded success path. A failure produces the smallest preserved
counterexample and no PASS receipt.

## Forbidden science

The reviewer will not open any future G-0140 manifest or any Stage A/B/C/D/E scientific output;
will not run the selector's default/scientific mode or `--preflight`; will not create or repair
scientific evidence; and will not modify any frozen subject. Only source inspection, static
analysis, synthetic/mutation controls, `--self-test`, `--static-preflight`, and the committed native
small oracle are authorized.

## Process-artifact creation gate

Consumer: the frozen G-0154 selector runtime gate and the orchestrator deciding whether Stage-C
source is admissible. Gate: no Stage-C run may consume a review unless the exact receipt contract
accepts it. Observed defect class: prior source-audit shape validation admitted integer `0`/`1` as
JSON booleans through Python's bool/int equality. Retirement condition: this preregistration remains
an immutable custody record but has no operative authority once G-0154 is withdrawn or superseded
by a newly frozen subject and preregistered audit.

## No-claim

Even a PASS would establish only that these exact six frozen source artifacts satisfy the exact
G-0154 source/custody contract under the preregistered attacks. It would not execute or validate a
scientific Stage-C run; certify any future manifest or output; establish exact matrix membership,
span, feasibility, a ReLU representation, a lower bound, or any mathematical theorem; raise an
independence tier beyond same-lineage T1; or repair/upgrade G-0150, G-0151, G-0140, or G-0143.
