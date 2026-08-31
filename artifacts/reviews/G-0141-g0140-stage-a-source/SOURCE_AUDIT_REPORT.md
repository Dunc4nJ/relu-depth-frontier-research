# G-0141 outcome-blind source/custody audit — G-0140 Stage A

## Verdict and calibrated summary

`FAIL` for source clearance of the exact frozen Stage-A Pool128 producer at
commit `1ee34276dcbbd35aedf090cb19bddf57283eb1d2`.

- **What moved:** the delivered producer's embedded-byte custody, direct
  G-0135 ancestor checks, strict G-0140 manifest shape, deterministic output
  construction, no-overwrite publication, and bounded claim string survived
  inspection and the three permitted outcome-blind runtime modes. Two
  load-bearing admission/custody gaps did not.
- **What did not move:** no G-0140 scientific manifest or output was observed
  or created, no scientific replay ran, and no mathematical claim changed.
- **Weakest link:** `validate_g0139_gate` accepts semantically deficient
  committed G-0139 receipts, even though a future one-shot manifest would bind
  the accepted bytes exactly.
- **Residual doubts:** this is same-campaign, same-model-lineage T1 review. It
  inspected the author's source and exercised its non-scientific preflights;
  it is not a clean-room implementation or a T2 review.
- **What changes the assessment:** tighten both blockers below, rebuild and
  freeze a new executable/source commit, and obtain a new outcome-blind source
  audit before creating the one-shot manifest or running Stage A.

Skill: `frontier-research-with-epistemic-humility` v1.0.0-rc.1, audit mode,
mathematics pack, W2. Generated `2026-08-31T18:40:27Z`. Auditor:
`GoldenSnow` (Codex / GPT-5). Audit preregistration commit:
`ba39813b58d8aaff7d34389ebbd2ac5de667c0bc`.

Custody attestation: `ATTESTED_READ_ONLY_W2` toward the frozen subject. The
subject was not edited or repaired. Only review artifacts in the reserved
G-0141 directory were created. This is a local procedural attestation, not an
authenticated multi-user custody claim.

## Exact subject binding

Subject commit `1ee34276dcbbd35aedf090cb19bddf57283eb1d2`, parent
`4ad09a05724bf686edc424b712dfd212baeadde5`, tree
`3935d1ca0a43b324d22edd7253ad2a416e816f1a`. The G-0140 preregistration commit
`af7ff480359c59544293c492b8f2913ab94773a2` and the G-0135 Stage-D result commit
`270a62455097cbaf0a8f80426c54b6121d1afcba` are strict ancestors. The subject is
a strict ancestor of G-0139 commit
`0bfdbf2db065d8517ad2d98d762473fed052cb54` and the G-0141 preregistration.

| Object | Git mode / blob | Bytes | SHA-256 |
|---|---:|---:|---|
| `artifacts/math/G-0140/stage_a_pool/src/main.rs` | `100644` / `ceccb8d424a6d2ebcdc12639e5fa8b89beacf933` | 135,449 | `9c5051e4027a78330fcfb23a3d024b3042849215642f1bc4b4f85c6037419334` |
| `artifacts/math/G-0140/stage_a_pool/src/engine.rs` | `100644` / `7440f2be7b9aad13548f305c64f41e2294861afc` | 15,390 | `b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c` |
| `artifacts/math/G-0140/stage_a_pool/Cargo.toml` | `100644` / `9ed3f8e7473abaaa3812e8afaaec90c3621219a5` | 348 | `eb20b76b6a133a9c6e18052822974287047c9d1bd92c3b4851d20cf2c1dafc26` |
| `artifacts/math/G-0140/stage_a_pool/Cargo.lock` | `100644` / `049848c82f23bb781c3ce6f0a6db2423adc7c6af` | 7,618 | `263f994a09ef9d687136e287e300cf7b63caa744015027c051eadd59189e0eae` |
| `artifacts/math/G-0140/stage_a_pool/target/release/g0140-stage-a-pool128-global-replay` | `100755` / `f42d0a5a61c5626351d627535ab4357adafca998` | 2,102,784 | `5632324ebf0d0b5fb0ad0a64f79e5fd08024f3251b1ec6bb616092270fe14b3c` |

The executable is an x86-64 PIE ELF with GNU/Linux interpreter and build ID
`aa203929a53a6080b94167bc66c91a05de1b47b6`. Commit-object and current working
bytes matched for all five objects.

## Blocking findings

### F-1 — G-0139 semantic admission is incomplete

`main.rs:1103-1127` requires only:

1. schema `max11-g0139-g0135-result-audit-v1`;
2. verdict `PASS`;
3. result `CONSISTENT_RESIDUAL_T1`; and
4. any recursively located binding with the exact Stage-D path and SHA-256.

It does not check the G-0139 receipt's exact subject commit, evidence class,
same-model-lineage flag, outcome-aware preregistration flag, claim boundary,
Stage-D source-audit anchor, entry/exit custody statement, fixed-input set, or
transitive-input census/content. The current real G-0139 receipt satisfies all
of those omitted conditions; the defect is that the producer does not require
them.

The important mitigation was tested and retained: `validate_g0140_manifest`
requires the future manifest's G-0139 binding to equal the receipt SHA returned
by the gate (`main.rs:1616-1619`), and the gate calls `git_commit_for_path`, so
the working receipt must equal reachable committed bytes. That establishes
byte identity after the one-shot manifest is frozen. It does not establish the
meaning of those bytes. A semantically deficient committed receipt can still
be bound exactly and admitted.

The preregistered probe constructed six in-memory hostile receipts: wrong
subject commit, false T2 evidence class, false independence/outcome disclosure,
empty claim boundary, missing transitive custody, and a false source-audit
anchor. Every fixture retained the four fields the implementation checks and
was accepted by the source-modeled implementation predicate; every fixture
failed the frozen semantic predicate. The built-in self-test contains no
G-0139 semantic mutant. See `HOSTILE_FIXTURE_RECEIPT.json` and
`audit_source.py`.

Method limitation: the checker does not dynamically invoke the private Rust
`validate_g0139_gate` function. It extracts that function from the exact
committed subject, asserts that the decision-bearing tokens are absent, and
evaluates an exact Python model of the predicate at `main.rs:1107-1122`. The
fixtures therefore demonstrate source-modeled acceptance. The source
extraction and token assertions make divergence visible, but they are not a
substitute for a Rust-level mutation harness.

### F-2 — the one-shot G-0140 manifest need not itself be committed

`validate_g0140_manifest` (`main.rs:1459-1622`) strictly parses the future
manifest, checks every bound file digest, and requires the preregistration,
producer-source, and source-audit commit fields to equal each path's latest
reachable committed bytes. Neither that function nor the full preflight/run
path calls `git_commit_for_path(root, G0140_MANIFEST_PATH)` or otherwise proves
that the manifest bytes being consumed are committed.

Consequently, a correctly shaped but uncommitted one-shot manifest can reach
the scientific path. This contradicts G-0140 preregistration lines 211-213,
which require the manifest to be committed before scientific execution, and
weakens the intended ancestry anchor. The outcome-blind static preflight's
current absence check is useful but cannot enforce the later commit boundary.

## Obligation-level disposition

| Obligation | Disposition | Evidence / boundary |
|---|---|---|
| Five exact subject objects and executable mode/bytes | `PASS` | Git tree/object metadata and SHA-256 pairs above |
| Source/executable compiled-byte custody | `PASS_WITH_BOUNDARY` | `include_bytes!` binds main/engine/Cargo/lock and prerequisite bytes (`main.rs:130-137`); `validate_compiled_bytes` compares them to contained regular committed files (`1238-1253`); the exact committed executable's static preflight passed. No path-independent build reproducibility claim is made. |
| Direct G-0135 Stage-D anchor | `PASS` | hard-coded result SHA/commit plus censuses/digests/first direction/first32 checks (`1047-1101`); ancestor preflight passed |
| G-0139 admission logic | `FAIL` | F-1 and six accepted hostile semantic fixtures |
| Strict G-0140 manifest shape and planned outputs | `PASS` | duplicate-key rejection, `deny_unknown_fields`, exact parameters, stage order, planned-output map, required binding set, path containment and SHA checks (`609-710`, `1459-1621`) |
| One-shot manifest Git custody | `FAIL` | F-2; no committed-blob check on `G0140_MANIFEST_PATH` |
| Deterministic output contract and claim boundary | `PASS` | typed serialization, canonical direction/coefficient digests, fixed result enum, and bounded `CLAIM_BOUNDARY` (`541-607`, `127-128`, `3484-3571`) |
| Exclusive publication | `PASS` | same-directory `create_new`, file sync, atomic no-overwrite hard link, temporary removal, directory sync, rollback on failure (`892-935`); overwrite fixture passed |
| Scientific census/arithmetic controls in source | `PASS_SOURCE_ONLY` | arbitrary-precision aggregate and exact DP routes, term/orbit reconciliation, target/term/direction/digest mutants; no scientific branch was executed |
| Admission mutation coverage | `FAIL` | built-in self-test omits the decision-bearing G-0139 semantic mutations |
| Claim/promotion boundary | `PASS` | no family-completeness, unrestricted, all-n, theorem, or T2 promotion in the fixed output claim string |

## Permitted non-scientific execution

Only the three preregistered modes were invoked on the exact executable:

- `--self-test`: exit 0, `G-0140 Stage A self-test PASS`.
- `--preflight-static`: exit 0,
  `G-0140 Stage A outcome-blind static preflight PASS`.
- `--preflight-ancestor`: exit 0 after 9.462779549 seconds, reporting 135
  terms, 100 accumulated rows, and disclosed first32 reconciled.

No `--preflight`, default scientific invocation, Cargo test, scientific
replay, solver, enumerator, or Pool128 construction was run. The exact command
records are in `SELF_TEST_RECEIPT.json`.

## Obligation list before a new source audit

1. Make G-0139 admission fail closed on the exact subject commit, evidence
   class, same-lineage and outcome-aware disclosure, claim boundary, source-
   audit anchor, fixed-input custody, and transitive-custody obligations.
2. Add built-in must-fail G-0139 fixtures for every decision-bearing field;
   the exact real receipt remains the positive arm.
3. Require `G0140_MANIFEST_PATH` itself to equal reachable committed Git bytes
   and establish the intended preregistration → producer → source audit →
   manifest ancestry before full preflight or scientific execution.
4. Rebuild and freeze source plus executable at a new exact commit, then run a
   new outcome-blind W2 source audit. Do not reuse this FAIL receipt as source
   clearance.

## No-claim boundary and residual risks

This FAIL identifies pipeline-admission defects. It does not refute the
G-0135 residual, show that the current real G-0139 receipt is incorrect, assess
any future G-0140 result, establish or exclude a Pool128 member, settle the
frozen family, prove a MAX11 lower bound, settle unrestricted two-hidden-layer
representation, establish minimality, prove an all-n statement, or supply a
Lean theorem.

The review remains T1 and same-campaign. Hashes and Git are local custody
signals, not signatures. The scientific algorithm was inspected only for the
bounded source obligations above; outcome correctness remains for the future
scientific run and a separate result audit after the source gate is repaired.

## Anti-ceremony and honesty disposition

The audit receipt is a legitimate runtime gate, not status theater:
`validate_source_audit` is intended to consume it before Stage A can proceed.
The report, checker, and receipts are the explicitly requested, replayable
evidence for that gate. Their active-gate role ends when a repaired producer is
frozen and receives a superseding source audit; the historical evidence should
remain immutable.

For the bounded work window, the tally is `USER=0`, `ENABLER=1`, and
`PROCESS=0` as independent work items. The one enabler is this source/custody
adjudication, which prevented an uncleared scientific run and produced two
specific repair obligations. Preregistration, custody receipts, and the
checker are supporting evidence inside that work item, not separately counted
deliverables. No task was closed by this reviewer. Disposition: `HEALTHY_GATE`.

Honesty inventory: no target source, target self-test, acceptance gate,
threshold, golden, or specification was edited or weakened; no mock substituted
for the subject; no stderr or failing result was suppressed; no scientific mode
or future manifest/output was opened; no subagent was used; and T1
same-lineage limitations remain explicit. The six-fixture denominator was
fixed before inspection, all six outcomes are reported, and the static
source-model limitation is disclosed above. A bounded `cass` search in this
workspace found zero matches for `weaken the test`, `make the test pass`, `skip
this test`, `regenerate the golden`, `mark it done`, and the task-derived
`G-0139 semantic admission`; that is no corroborating history, not proof of
absence. The anti-ceremony worksheet was applied during closeout after the
substantive audit and first artifact draft; it did not alter the verdict or
evidence. The strongest re-executable evidence is `python3 -B
artifacts/reviews/G-0141-g0140-stage-a-source/audit_source.py`, together with
the exact source locations cited above.

`scientific_manifest_observed=false`

`scientific_output_observed=false`

`scientific_replay_run=false`
