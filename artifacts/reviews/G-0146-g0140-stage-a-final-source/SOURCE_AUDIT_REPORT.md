# G-0146 final outcome-blind source/custody audit — G-0140 Stage A

## Verdict

**FAIL** for T1 source/custody clearance of frozen commit
`2157fd2a9776277354c45487ae1cbc0670ffc9b8`.

Both historical G-0141 blockers are repaired in the exact frozen full gate, and all three permitted
producer runtime modes pass. A new blocker remains: final source-audit admission is structurally
permissive. It accepts required path/SHA pairs found recursively anywhere in a PASS-like JSON
document rather than requiring the five named bindings in the subject structure. The same
source-modeled hostile receipt can omit the named subject bindings, move the pairs under unrelated
lookalike objects, add the explicitly prohibited `audit_git_commit`, and still satisfy the
implemented predicate.

This verdict is pipeline admission only. No G-0140 scientific manifest, candidate/scientific
input, or Stage-A scientific output was opened; no scientific replay ran; no mathematical claim
moved.

Preregistration commit: `381adc68e82f53f8bfee750793233b56b0a875b8` (short form `381adc6`),
pushed before frozen-source inspection or runtime execution. Preregistration SHA-256:
`b77a8bdac2346648797cc4aa2cde7b1ce798f90343e8b83474434fb80d0b04a9`.

## Exact frozen subject and working-byte custody

The frozen commit is a reachable Git commit and an ancestor of the audit work. Every required
working object is a regular, non-symlink file; its Git object ID and bytes equal the frozen commit;
and its independently computed SHA-256 matches the required anchor.

| Binding | Git mode / blob | Bytes | SHA-256 |
|---|---|---:|---|
| `artifacts/math/G-0140/stage_a_pool/src/main.rs` | `100644` / `43e60e7f0dd17a00dfc664b483c322b6e8db2ea7` | 145,142 | `5fd91773b1e16cc54d09c20c72ef729a333bef4c8b6804f24a525a4be8258790` |
| `artifacts/math/G-0140/stage_a_pool/src/engine.rs` | `100644` / `7440f2be7b9aad13548f305c64f41e2294861afc` | 15,390 | `b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c` |
| `artifacts/math/G-0140/stage_a_pool/Cargo.toml` | `100644` / `9ed3f8e7473abaaa3812e8afaaec90c3621219a5` | 348 | `eb20b76b6a133a9c6e18052822974287047c9d1bd92c3b4851d20cf2c1dafc26` |
| `artifacts/math/G-0140/stage_a_pool/Cargo.lock` | `100644` / `049848c82f23bb781c3ce6f0a6db2423adc7c6af` | 7,618 | `263f994a09ef9d687136e287e300cf7b63caa744015027c051eadd59189e0eae` |
| `artifacts/math/G-0140/stage_a_pool/target/release/g0140-stage-a-pool128-global-replay` | `100755` / `a062586517d3f1027617a3364c50e2e253b77481` | 2,185,240 | `366acb1e70a2699e3a26089263173f142af021b4a6379632e4786d460bf00f4a` |

The executable is an x86-64 PIE ELF with GNU/Linux interpreter and build ID
`66a39d603852e0d1e12ea0982f49599486d12b14`. This is exact-byte local Git custody, not a
path-independent reproducible-build or external-signature claim.

## Historical G-0141 repair disposition

### G-0141 F-1 — repaired for the exact frozen full gate

`main.rs:1115-1193` now:

1. pins the exact G-0139 receipt SHA-256 and exact receipt commit;
2. strict-parses the committed bytes;
3. requires exact subject commit/path/SHA and result;
4. requires the exact T1 same-lineage outcome-aware evidence class and claim boundary;
5. requires same-lineage and outcome-aware disclosure;
6. requires the exact Stage-D source-audit anchor;
7. requires entry/exit custody equality, fixed/transitive counts, and the two load-bearing fixed
   anchors; and
8. embeds seven must-fail semantic/custody mutants in `self_test`.

The exact baseline passes. One-at-a-time wrong subject commit, evidence class, lineage,
outcome-awareness, claim boundary, custody equality, and source-audit anchor all fail the extracted
semantic predicate. Any other changed G-0139 receipt byte also fails the full gate's hard-coded
receipt SHA/commit before it can be admitted.

Residual, not a frozen-runtime blocker: the semantic helper by itself checks only the length of the
92-entry transitive map, so a non-anchor transitive value mutant survives that helper. It cannot
survive this frozen full gate because the entire exact G-0139 receipt is digest- and commit-pinned
and embedded into the executable. A changed producer or changed pinned receipt would require a new
source audit.

### G-0141 F-2 — repaired

`validate_g0140_manifest` calls `git_commit_for_path(root, G0140_MANIFEST_PATH)` before parsing
(`main.rs:1572-1576`). `git_commit_for_path` obtains the last committed blob and compares its
SHA-256 to current regular, contained working bytes (`main.rs:878-901`). A generic temporary-Git
hostile control accepted committed working bytes and rejected changed working bytes. No actual or
synthetic G-0140 scientific manifest was opened or created.

## New blocking finding G0146-F1

### Final source-audit admission accepts recursive binding lookalikes

Severity: **BLOCKER**.

Decision code:

- `main.rs:1267-1294` validates selected envelope values from an untyped `serde_json::Value` but
  does not reject unknown source-audit fields.
- `main.rs:1297-1347` calls `collect_recursive_bindings` over the entire receipt.
- `main.rs:1327-1337` accepts each required producer path if *any* recursively discovered object
  has the matching path and SHA. It does not require the binding at a named subject pointer or
  require exactly the five declared binding objects.

The independently preregistered hostile fixture starts from a valid exact-contract receipt, then:

1. removes all five named objects from `subject.bindings`;
2. places the same correct path/SHA objects under `unrelated_receipt_lookalikes`;
3. adds the forbidden top-level `audit_git_commit`; and
4. adds another unknown envelope extension.

The exact source-modeled implemented predicate accepts that fixture. The producer-declared exact
nested-binding contract rejects it. This is discriminative rather than an all-red model:

| Control | Result |
|---|---|
| Exact baseline receipt | implemented predicate accepts; exact contract accepts |
| Remove one required path/SHA everywhere | rejects |
| Wrong required hash | rejects |
| Wrong subject commit | rejects |
| Set scientific-input-observed true | rejects |
| Displace all named bindings into unrelated lookalike objects | **implemented predicate accepts** |
| Add prohibited `audit_git_commit` to that lookalike | **implemented predicate still accepts** |

The outer manifest's exact receipt hash and Git-blob checks do not cure this defect: they can prove
that the hostile receipt was committed and bound exactly, but not that its five bindings occupy the
required semantic structure. This is the same bytes-versus-meaning distinction that made G-0141
F-1 blocking.

Method boundary: the checker does not dynamically inject the fixture into the private Rust
function. It extracts the exact frozen decision code and runs a source-exact Python predicate over
the fixture. This limitation is explicit; adding a test hook to the producer would violate W2
read-only custody, and invoking full/scientific preflight is prohibited. The source pattern is
direct and the checker asserts the load-bearing tokens and their absence before evaluating the
fixture.

## Other hostile paths

| Attack | Disposition |
|---|---|
| Duplicate JSON keys | PASS: recursive strict visitor rejects duplicates |
| Trailing second JSON value/garbage | PASS: `deserializer.end()` rejects it |
| Wrong primitive types for decision fields | PASS: exact string/bool accessors reject them |
| Unknown fields in typed G-0140 manifest | PASS: `deny_unknown_fields` |
| Unknown/lookalike fields in final source-audit receipt | **FAIL: G0146-F1** |
| Missing required producer pair entirely | PASS: rejected |
| Wrong producer path/SHA pair | PASS: rejected and current bytes rehashed |
| Renamed source-audit path | PASS: canonical constant path and manifest binding required |
| Path escape or symlink | PASS: normal contained components and non-symlink traversal required |
| Stale/different compiled source | PASS for exact binary: main, engine, Cargo manifest, and lock are embedded and compared; static preflight passed |
| Noncanonical executable path or uncommitted executable bytes | PASS: canonical current executable and Git working/blob equality required |
| Mutable input drift during replay | PASS source inspection: inputs, manifest, G-0139 audit, and executable are reloaded/rehashed at end and compared before exclusive publication |
| Missing/malformed prerequisite | PASS source inspection: fallible opens/parses/checks propagate nonzero failure; no warning-as-success branch found |
| Self-reference/circular field in audit receipt | **FAIL as contract enforcement: ignored unknown `audit_git_commit` is admitted by G0146-F1** |

## Exact commands and observed results

Checker SHA-256:
`c98eb6e9cc3f8cb136af66ce2ff99ad6393ec9d027955f739cc31e0502746d49`.

```text
$ python3 -B artifacts/reviews/G-0146-g0140-stage-a-final-source/audit_final_source.py --self-test
exit 0; stderr empty
status=PASS; 7/7 controls true, including positive baseline and must-fail missing/wrong arms

$ python3 -B artifacts/reviews/G-0146-g0140-stage-a-final-source/audit_final_source.py
exit 1; stderr empty
verdict=FAIL; blocker=G0146-F1

$ artifacts/math/G-0140/stage_a_pool/target/release/g0140-stage-a-pool128-global-replay --self-test
exit 0; stderr empty
G-0140 Stage A self-test PASS

$ artifacts/math/G-0140/stage_a_pool/target/release/g0140-stage-a-pool128-global-replay --preflight-static
exit 0; stderr empty
G-0140 Stage A outcome-blind static preflight PASS

$ artifacts/math/G-0140/stage_a_pool/target/release/g0140-stage-a-pool128-global-replay --preflight-ancestor
exit 0; stderr empty
G-0140 Stage A ancestor preflight PASS: 135 terms; 100 accumulated rows; disclosed first32 reconciled
```

Custody commands included `git ls-tree -l <frozen-commit> -- <five paths>`, `git hash-object` on
each working path, `sha256sum` on each working path, `stat` on each working path, and committed-blob
SHA comparisons. Every five-file check passed. No Cargo test, `--preflight`, default invocation,
scientific solver, scientific enumerator, or replay command was run.

## Obligations before re-audit

1. Parse the final G-0146 receipt into a dedicated typed structure with
   `#[serde(deny_unknown_fields)]` at every decision-bearing level.
2. Require exactly the five named `{path,sha256}` objects at their declared subject locations;
   reject displaced recursive lookalikes and duplicate path occurrences rather than searching the
   whole receipt for convenient matches.
3. Reject `audit_git_commit` explicitly (or via the typed unknown-field rule) and preserve the
   non-self-referential manifest-to-audit Git anchor.
4. Add built-in must-fail fixtures for displaced bindings, a missing named binding paired with a
   correct decoy elsewhere, duplicate correct path pairs, unknown envelope fields, and
   `audit_git_commit`.
5. Rebuild and freeze new source/executable bytes and obtain a fresh outcome-blind audit. This FAIL
   receipt must not be treated as source clearance.

## Evidence tier, no-claim boundary, and honesty disposition

Evidence class: `T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT`. Same model lineage is not T2
independence. Git hashes are local custody evidence, not signatures or a hostile multi-principal
boundary.

No source/custody clearance is granted. This audit does not adjudicate a G-0140 scientific
manifest or result, establish or exclude a Pool128 member, validate family completeness, prove a
MAX11 lower bound, settle unrestricted two-hidden-layer representation, establish minimality,
prove an all-n statement, or supply a Lean theorem.

Anti-ceremony disposition: **LEGITIMATE BOUNDED GATE**. The audit is one ENABLER work item with a
named runtime consumer and an observed incident class; its supporting files are not separately
counted as progress. It retires as an active gate after this exact frozen subject is adjudicated
and is superseded by a new audit if producer bytes change.

Honesty disposition: no producer, historical receipt, threshold, test, or acceptance criterion was
edited or weakened; no subagent was used; no stderr or failure was suppressed; the checker exits
nonzero on the FAIL; the source-model limitation and the non-blocking G-0139 semantic residual are
both disclosed. The full written inventory is in `HONESTY_INVENTORY.md`.

`scientific_manifest_observed=false`

`scientific_input_observed=false`

`scientific_output_observed=false`

`scientific_replay_run=false`
