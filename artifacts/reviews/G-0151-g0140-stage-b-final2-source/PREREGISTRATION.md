# G-0151 Stage-B final2 source/custody audit preregistration

- Audit ID: `G-0151`
- Reviewer: `CalmBarn` (`codex`, `gpt-5`; fresh Agent Mail session)
- Registered UTC: `2026-08-31T20:41:40Z`
- Mode: bounded ENABLER source/custody and admission audit; no mathematics and no scientific execution
- Frozen subject revision supplied by the operator: abbreviated commit `19de7da` (the unique full commit will be resolved only after this preregistration is committed and pushed)
- Frozen subject paths, exactly:
  - `artifacts/math/G-0140/stage_b_pricer/src/main.rs`
  - `artifacts/math/G-0140/stage_b_pricer/Cargo.toml`
  - `artifacts/math/G-0140/stage_b_pricer/Cargo.lock`
  - `artifacts/math/G-0140/stage_b_pricer/target/release/g0140-stage-b-pool128-coordinate-pricer`

## Outcome-blindness statement

This document was written before reading any of the four frozen subject files, before executing the
subject binary, before inspecting any prior G-0151 artifact, and before running any audit checker.
The acceptance predicate, negative probes, evidence rules, and failure policy below are fixed before
the reviewer learns whether the revised producer passes them. Later findings may instantiate exact
field names and command syntax learned from the frozen source, but they may not weaken, remove, or
reinterpret a preregistered obligation. Any necessary change to this protocol is a disclosed deviation
and is itself a blocker unless it only strengthens a test without changing the acceptance predicate.

## Consumer, gate, observed defect, and retirement

- Consumer: the G-0151 orchestrator and the Stage-B producer's exact G-0151 source-audit admission
  branch.
- Gate: no consumable G-0151 PASS receipt may exist, and the revised Stage-B producer is not admitted,
  unless every mandatory check below passes against the exact frozen commit and exact four paths.
- Observed defect class: G-0147 found concrete source/admission blockers, including an optional-field
  ambiguity, opaque Stage-A control payloads, and structurally inadequate audit-receipt binding and
  parsing. This audit specifically retests those blockers rather than awarding credit for new ceremony.
- Retirement: this preregistration ceases to gate once the exact frozen G-0151 verdict is consumed or
  superseded by a newly preregistered audit of a different frozen subject revision. It must never be
  reused to admit changed bytes.

## Decision rule

`PASS` is the conjunction of every mandatory item in sections A through H. One false, untested,
ambiguous, non-reproducible, or custody-mismatched item forces `FAIL`. A `FAIL` artifact must be
explicitly non-consumable and must not imitate the producer-admissible PASS schema. Evidence from one
probe cannot silently stand in for a different obligation. Self-test success is necessary but not
sufficient.

On PASS, the emitted machine receipt must match the frozen producer's hard-coded G-0151 contract
exactly: exact schema identifier, exact canonical path, exact preregistration binding, exact claim and
no-claim strings, deny-unknown parsing, exactly four named subject bindings, and exactly the required
check keys—no aliases, no compatibility extras, no unregistered fields. The receipt is emitted only
after an end-of-run custody rehash remains identical.

## A. Frozen and working-tree custody

1. Resolve `19de7da^{commit}` to one full Git commit and record it. Refuse ambiguity or absence.
2. Verify each of the four exact paths exists at that commit with its Git mode, blob/object identity,
   byte count, and SHA-256 recorded. No fifth subject path may be substituted.
3. Hash the same four working-tree paths before any execution. Require byte identity with the frozen
   commit, including the canonical release executable. A locally rebuilt or alternate executable is
   not admissible.
4. Record repository HEAD and dirty state without treating unrelated concurrent files as subject
   changes. Any difference at one of the four subject paths is a blocker.
5. Rehash all four subject paths at the end and require equality with both the opening hashes and the
   frozen blobs. The audit must not modify the producer, its manifest, lockfile, or executable.

## B. Permitted execution boundary

Only these producer modes may execute:

- the canonical frozen executable with `--self-test`;
- the canonical frozen executable with `--preflight-static`, with the frozen panel and candidate
  supplied only as opaque path arguments and never opened by the reviewer or helper code.

The audit must not invoke bare/default execution, `--preflight`, any scientific mode, or any command
that writes Stage-B output. It must not open or create the G-0140 scientific manifest, Stage-A
scientific output, or Stage-B output. Temporary synthetic files may contain only audit receipts or
reviewer-authored non-scientific parser fixtures; they must not copy or decode scientific payloads.

## C. Revised typed Stage-A admission logic

The frozen Rust source and its executable self-test must jointly demonstrate all of the following.
Static type presence without semantic use is insufficient; a parsed field must affect a fail-closed
decision.

1. An explicitly present JSON `null` for `first_nonzero_linear` is accepted where the exact contract
   permits null.
2. Omission of `first_nonzero_linear` is rejected, including at every nested mutation-control location;
   `Option<T>` alone does not distinguish missing from explicit null and therefore does not satisfy this
   requirement without a presence-aware mechanism.
3. Each formerly opaque Stage-A control is represented by an exact deny-unknown type, not a generic
   JSON value/map or ignored blob.
4. Finite-census dimensions, digest, and mutant evidence are checked against exact expected semantics.
5. All 135 ordered term receipts are checked for exact cardinality, index/order continuity, and semantic
   binding rather than merely parsed.
6. Both global censuses are checked exactly, including their expected identities/counts/digests.
7. All five exact mutation controls are checked independently, including their nested required fields.
8. Census and selection booleans are required and checked for the exact truth values; truthiness,
   defaults, or omission are rejected.
9. Unknown fields at every revised typed layer are rejected.

Discriminative evidence must include positive controls and minimally changed negative controls. The
reviewer will prefer behavioral self-test/probe evidence over textual pattern matching and will map
each asserted branch to a concrete must-pass/must-fail case.

## D. G-0150 and G-0151 source-audit admission branches

Both branches must independently use their exact named bindings and fail closed. For each branch,
fresh synthetic audit-receipt probes will test, to the extent exposed by `--preflight-static`, one valid
shape plus minimally changed mutants for:

1. exact four named subject bindings accepted only at their canonical names and paths;
2. one binding displaced into another field/path;
3. one required binding missing while a plausible decoy/alias is present;
4. two named bindings resolving to the same path or otherwise duplicating a subject path;
5. an unknown root, binding, or required-check field;
6. an `audit_git_commit` field, which must be rejected rather than accepted as compatibility metadata;
7. a duplicate JSON key at the root and at a nested object;
8. valid JSON followed by trailing non-whitespace data;
9. a required named binding or required check omitted;
10. extra or renamed required-check keys.

Acceptance is based on observed exit status plus stderr/stdout diagnostics and absence of output side
effects, not on substring matches alone. If one branch cannot be reached behaviorally without violating
the no-science boundary, its exact parser/decision call graph and self-test cases must be audited, and
the limitation will be disclosed rather than papered over.

## E. Prior receipt and repair compatibility

1. Verify compatibility with the committed G-0150 PASS receipt whose operator-supplied SHA-256 is
   `f65452749be020286410fb03a16e493c917716cecdc557456b449b5fe8223b4e`.
2. Identify the exact committed receipt path from repository metadata/source bindings without accepting
   an uncommitted substitute, hash its bytes, and require the supplied digest exactly.
3. Recheck that the G-0142 repairs remain enforced in the revised producer. Earlier PASS labels or
   historical receipts are leads, not evidence; exact code paths and discriminative tests must support
   the result.

## F. Exact arithmetic, census, embeddings, and executable identity

1. Audit all decision-bearing integer paths for arbitrary-precision `BigInt` use or an equivalently
   proved lossless representation. Reject narrowing through fixed-width integers, floats, lossy string
   conversion, unchecked casts, or overflow-prone intermediates.
2. Require exact pool/candidate census dimensions `128 x 163740`, exact ordering, exact loop bounds, and
   no sampling, truncation, deduplication, or off-by-one substitutions.
3. Verify that compiled embeddings are the exact embeddings bound by the frozen source/receipts and are
   used in the decision path, not decorative constants or a bypassed payload.
4. Require execution of the exact frozen canonical release executable at the registered path; PATH
   lookup, debug builds, copied binaries, and locally rebuilt substitutes do not count.

## G. Operational fail-closed behavior

1. Every mandatory check must propagate failure to a nonzero process exit and suppress PASS/output
   emission; logging an error while continuing is a blocker.
2. Existing output/refusal targets must not be overwritten. The relevant branch must use atomic or
   otherwise fail-closed creation semantics, and a behavioral overwrite probe must leave sentinel bytes
   unchanged where that branch can be exercised without science.
3. Temporary/intermediate failures must not be converted to success.
4. The producer must rehash inputs/subject bindings at the end and refuse drift between opening and
   closing custody observations.
5. No hard-coded self-test fixture or receipt hash may bypass the generic typed decision path. Tests must
   perturb one relevant fact at a time and show the expected decision changes.

## H. Fresh discriminative checker standard

The G-0147 checker may be read only after this preregistration is frozen, as historical evidence of its
blockers. It will not be copied or reused unchanged. In particular, its recursive witness-closure rule is
preregistered as structurally all-red and is not an acceptance test here. The new checker/probe harness
must instead:

- target the revised typed Rust decision logic and its own self-test;
- enumerate individual obligations with independent booleans/evidence;
- include positive and planted-negative controls;
- distinguish parser rejection from later unrelated failures;
- preserve complete command, exit-status, stdout, and stderr evidence;
- avoid opening any prohibited scientific artifact;
- fail when a planted invalid case is accepted or a planted valid case is rejected.

## Evidence and reproducibility record

The final audit record will include: full frozen commit; audit commit; exact four opening/final subject
hashes; canonical executable hash; commands run and exit codes; self-test result; a probe matrix with
expected versus observed behavior; source locators for every static conclusion; G-0150 receipt path and
verified digest; the exact PASS/FAIL decision; receipt SHA-256 when a receipt exists; limitations and
deviations; and the four no-science flags below.

The checker and fixtures must live under
`artifacts/reviews/G-0151-g0140-stage-b-final2-source/` or an ephemeral directory, and may write only
review artifacts. The audit will commit only its own reserved directory and will not modify historical
receipts or producer files.

## Mandatory no-science flags

All four must be `false` for PASS:

1. `g0140_scientific_manifest_opened_or_created`
2. `stage_a_scientific_output_opened_or_created`
3. `stage_b_output_opened_or_created`
4. `preflight_default_or_science_mode_executed`

## No-claim

This audit can establish only that the exact four frozen producer artifacts at the resolved descendant
of `19de7da` satisfy the preregistered source/custody/admission contract under the permitted static and
self-test modes. It does not establish any mathematical claim, validate any Stage-A or Stage-B
scientific result, prove completeness/correctness of the search, confer research standing, or authorize
execution of the scientific producer path.
