# G-0151 final2 Stage-B source/custody audit

## Decision

**PASS** for the exact four Stage-B producer bindings frozen at Git commit
`19de7da8fe62629780fd7c7cf9b6d08d66e03fd2`.

This is a T1 same-lineage, outcome-blind source/custody clearance. It does
not inspect or adjudicate a G-0140 scientific manifest, a Stage-A scientific
output, or a Stage-B output, and it does not promote a mathematical claim.

Machine-readable evidence:

- `CHECK_RESULTS.json`: 25 passed checks, zero failed check IDs.
- `SOURCE_AUDIT_RECEIPT.json`: exact closed G-0151 PASS envelope accepted by
  the frozen producer's Rust validator.
- Receipt SHA-256:
  `f8a03d46c024c8bfd2caec9020562a0a5d2fef6717438d6dece36a9f2f174de3`.

## Frozen custody

The commit object and working-tree bytes agreed at opening and at the
terminal rehash:

| Binding | Mode | SHA-256 |
|---|---:|---|
| `artifacts/math/G-0140/stage_b_pricer/src/main.rs` | `100644` | `daf902233012749b51ae4bb11565f1e31f2a1f5b78c50e5a395645b777c01324` |
| `artifacts/math/G-0140/stage_b_pricer/Cargo.toml` | `100644` | `425d82de4e6d5902e2d3d7b005c5473225c4d6f197752590e89d7be670b2685c` |
| `artifacts/math/G-0140/stage_b_pricer/Cargo.lock` | `100644` | `8875e1375a361873ac13bbcdf9e14c8ca7b34afa1438dfae9a6800f31325365a` |
| `artifacts/math/G-0140/stage_b_pricer/target/release/g0140-stage-b-pool128-coordinate-pricer` | `100755` | `528afddba827e7165f43014416ef1e994191e9744c5e62054aebe2b9b8280806` |

The outcome-blind preregistration was committed and pushed before source
inspection or runtime checks:

- preregistration commit:
  `e380d54cc5476dbb4028e10ffd1a11a35c1d07a8`
- preregistration SHA-256:
  `10680c6915cb272cc9d381f7a0abc09c773e3462225138eabcd60e0b1c3cbab8`

## Checks performed

The audit rechecked the historical G-0142 and G-0147 blocker classes rather
than reusing the structurally unsuitable G-0147 recursive witness closure.
The frozen source now enforces:

- explicit-null versus missing-field rejection for required-nullable Stage-A
  fields;
- closed typed schemas and semantic validation for all nine Stage-A control
  fields;
- exact, named, closed G-0150 and G-0151 audit-receipt contracts, including
  duplicate-key and trailing-data rejection;
- the G-0142 closed-schema and exact source-audit repairs;
- unconditional BigInt coefficient arithmetic on the audited path;
- the exact `128 x 163740` census and sequence/order contract;
- compiled source, manifest, and lock-byte embeddings;
- executable custody, failure propagation, overwrite refusal, and terminal
  rehash enforcement.

The committed G-0150 receipt was admitted at exact SHA-256
`f65452749be020286410fb03a16e493c917716cecdc557456b449b5fe8223b4e`;
its five named bindings matched both its frozen subject commit and current
working bytes.

Fresh discrimination evidence consisted of:

- 26/26 source mutations turning the intended static check red;
- 22/22 Stage-A and 22/22 Stage-B exact Rust receipt-envelope cases behaving
  as expected, including displaced lookalikes, missing named bindings,
  duplicate paths, unknown fields, duplicate JSON keys, and trailing data;
- the canonical `--self-test` passing;
- the canonical `--preflight-static` passing with only the two opaque path
  strings supplied; and
- two adjacent `--preflight-static` path-drift probes failing nonzero.

The producer's default/scientific mode was not run. The static preflight did
not open the opaque paths supplied to it.

## No-science accounting

| Flag | Value |
|---|---|
| `g0140_scientific_manifest_opened_or_created` | `false` |
| `stage_a_scientific_output_opened_or_created` | `false` |
| `stage_b_output_opened_or_created` | `false` |
| `preflight_default_or_science_mode_executed` | `false` |

## Claim boundary

This audit does not establish or exclude a Pool128 coordinate matrix or
exact-rank selection, validate family completeness, prove a MAX11 lower
bound, settle unrestricted two-hidden-layer representation, establish
minimality, prove an all-n statement, or supply a Lean theorem.

## Real-work audit

Window: this G-0151 audit session and its two publication commits. Project
purpose, copied from `README.md`: determine whether every finite maximum can
be represented exactly by a finite ReLU network with exactly two hidden
ReLU layers and unrestricted real weights.

Inventory: USER 0; ENABLER 1 (the exact audit checker, adversarial probe, and
consumable receipt); PROCESS 1 (preregistration and human report); UNKNOWN 0.

1. Most user-visible item: none. The demonstrable object is the frozen
   producer accepting the exact proposed receipt and rejecting adjacent
   malformed envelopes.
2. Without the process item, no immediate user-visible behavior changes,
   but the outcome-blind provenance required for the named gate is lost.
3. The enabler has a concrete consumer: the frozen Stage-B producer parses
   and branches on the exact G-0151 receipt contract; the Rust probe exercised
   that consumer directly.
4. The oldest user-valued open item was not ranked in this bounded audit;
   the assignment fixed G-0151 as the sole scope.
5. No subagent swarm was used by this auditor.
6. No plan or specification was edited in place of implementation, and no
   unmet acceptance condition was moved to a follow-up.

Verdict: **HEALTHY within the commissioned bounded gate**. The window has no
direct USER item, but its sole substantive artifact is a named, exercised
ENABLER, and the process work is limited to the required preregistration and
report. Correction dispatched: stop after publishing this receipt; add no
further audit machinery in this lane.

## Honesty inventory

Session/window reviewed: the full CalmBarn G-0151 session, the preregistration
commit, all uncommitted audit artifacts, relevant reflog entries, the bounded
test/workflow history, and six CASS searches with two recent-hit context
reads.

1. No (checked: no subject test, CI, lint, or workflow file was edited; the
   bounded history diff and current audit diff contain no weakened or ignored
   test).
2. No (checked: the Rust probe calls validators compiled from the exact frozen
   source; it is not a mock or substitute implementation).
3. No (checked: no golden or snapshot was regenerated).
4. No (checked: the frozen feature source is untouched; audit code is in a
   separate review path; no suppression, bypass, timeout, retry, or tolerance
   relaxation was added).
5. No (checked: the checker covers the exact four preregistered bindings and
   adjacent negative cases; it does not narrow the frozen subject after
   seeing outcomes).
6. **Yes, bounded and demoted:** campaign-wide `skill-runtime verify-full`
   exited green while running zero scientific replay commands. It is not a
   required receipt check and is not used to support this verdict. The
   substantive denominators are recorded explicitly: 25/25 audit checks,
   26/26 planted mutations, 22/22 plus 22/22 receipt cases, and four producer
   invocations. This applies the PL-1 zero-run countermeasure.
7. No (checked: every cited command was run in this session and its exit code
   and output were observed or captured in `CHECK_RESULTS.json`).
8. No (checked: static, planted-negative, exact-parser, and producer-runtime
   evidence are labeled separately; none is described as scientific replay).
9. No (checked: initial reviewer-harness failures and the zero-replay verifier
   are disclosed; `failed_check_ids` is empty only for the final bounded run).
10. No (checked: producer stdout and stderr, including negative-path stderr,
    are retained with hashes in `CHECK_RESULTS.json`).
11. No (checked: no Bead or work item was closed by this auditor).
12. No (checked: no plan, specification, charter, requirement, or frozen
    producer file was edited).
13. No (checked: this auditor closed no tracker item and dispatched no child
    agent).
14. No (checked: no child agent was dispatched; the preregistration itself
    names positive observables, planted negatives, and a No-Claim boundary).
15. No (checked: there was no child-agent report to accept; the auditor ran
    every cited check directly).
16. No (checked: no pane or child agent was used, and the positive receipt
    acceptance path was exercised alongside rejection paths).
17. No (checked: the verdict rests on frozen bytes and executable checks, not
    agreement between agents).
18. No (checked: check, mutation, receipt-case, binding, and producer-mode
    denominators were fixed before the final outcome-bearing run).
19. No (checked: the replayable transcript contains two reviewer-only harness
    corrections—an include path and an expected case count—both surfaced red
    before the final run and neither changed frozen subject behavior).
20. Strongest evidence: rerunning `audit_stage_b_final2_source.py` against
    commit `19de7da8fe62629780fd7c7cf9b6d08d66e03fd2` reproduces the exact Rust
    contract matrix, authorized producer runs, and terminal rehash.

Disposition for the one “yes”:

- [x] Corrected in place: the zero-run verifier was removed from the verdict's
  evidence set; the machine-readable receipt does not cite it.
- [x] Disclosed: this report records the zero-run result explicitly.
- [x] Encoded as countermeasure: PL-1 exact-set/cardinality evidence is
  recorded in `CHECK_RESULTS.json`, with zero-run green denied proof credit.
