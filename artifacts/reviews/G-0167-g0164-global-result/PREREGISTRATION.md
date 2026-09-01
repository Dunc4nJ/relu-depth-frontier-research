# G-0167 outcome-blind preregistration

- Auditor: `PurpleBison` (`codex`, GPT-5 lineage)
- Locked at: `2026-09-01T04:00:58Z`
- Subject mode: read-only W2 claim/result audit, mathematics domain
- Audit subtree: `artifacts/reviews/G-0167-g0164-global-result/`
- Frozen manifest anchor: `bd64ece4a5ad17c77e80f3f2f2dfd2a0b27da243`
- Frozen result anchor: `1a16346519c11d4616a10a2738a70aa935643053`
- Frozen result path: `artifacts/math/G-0164/all128_global_replay_v1.json`

## Blindness declaration and prior exposure

Before this file was written, the auditor did **not** open, hash, parse, grep, count, query, or
otherwise inspect the frozen result path at either commit or in the working tree. The auditor did
see (a) the task text, including the phrase “first nonzero residual,” and (b) the subject commit
line `G-0164 record exact global residual` in a routine pre-edit `git log`. Therefore this is blind
to the result bytes, values, schema, claimed classification, branch location, and digests, but it
is not direction-blind: the assignment itself suggests that a nonzero residual may exist. No
method below may be weakened, strengthened, or selected in response to the observed result.

The manifest has likewise not been opened. Its path will be selected after this lock by the exact
rule below, not by favorable contents.

## Consumer, gate, and retirement

The consumer is the G-0167 orchestrator. This preregistration gates any PASS/FAIL adjudication of
the frozen G-0164 result and prevents post-result selection of methods or tolerances. The observed
defect class is result-conditioned checking/self-certification in finite computational claims.
This artifact retires when the two frozen anchors above are withdrawn or superseded; it does not
govern a later result commit.

## Exact subject and claim boundary

The only positive claim eligible for PASS is:

> At the two frozen Git anchors, the delivered G-0164 artifact is a complete, internally
> reconciled, exactly classified census of the manifest-declared 128-prefix finite replay, in the
> manifest-declared prefix order, with all binding digests correct; and an independent exact route
> reproduces the finite replay semantics and the earliest nonzero residual (if one exists).

The audit does **not** establish an unrestricted ReLU-depth theorem, an obstruction outside the
128 declared branches/prefixes, correctness of unexecuted producer modes, novelty, community
acceptance, or any claim beyond the manifest's exact coefficient field, conventions, input
objects, and finite domain. A finite clean census remains a boundary claim. A nonzero residual is
classified only under the manifest's stated residual semantics; it is not silently promoted to a
different mathematical statement.

## Frozen-object selection and custody rules

1. Resolve both supplied strings as commits with `git cat-file -e <sha>^{commit}`. Failure is FAIL.
2. Require the result commit's first parent to equal the manifest anchor exactly. Failure is FAIL.
3. Select the manifest by listing only the paths added or modified by the manifest anchor versus
   its first parent. Exactly one regular JSON path under `artifacts/math/G-0164/` must identify
   itself by basename as a global replay manifest. Zero or multiple candidates is FAIL; no
   content-driven fallback is allowed.
4. Require the selected manifest blob to exist at the manifest anchor and to be byte-identical at
   the result anchor. Require the result path to be absent at the manifest anchor and present as a
   regular blob at the result anchor.
5. Require the result commit diff against its first parent to add the frozen result path and not
   modify the producer, manifest, source inputs, or any other proof-bearing G-0164 file. Any such
   mutation is FAIL. Non-proof metadata changes, if any, will be listed and treated as a custody
   limitation rather than silently ignored.
6. Extract blobs by Git object ID into a fresh temporary directory. Never validate the mutable
   working-tree copy. Record commit IDs, blob IDs, byte lengths, and SHA-256 digests in the receipt.
7. Recompute every manifest/result source pin against the exact frozen blob it names. Missing,
   ambiguous, mutable-only, path-escaping, or mismatched bindings are FAIL.

## Parser and schema rules

The independent validator will use Python standard-library parsing with duplicate-key rejection
and rejection of `NaN`, `Infinity`, and `-Infinity`. It will perform no numeric string-to-number
coercion. Integers used as counts/indices must be JSON integers (not booleans). Exact values may be
integers or explicitly structured/string rationals only when the manifest contract declares that
encoding; denominators must be positive and nonzero and values are reduced before comparison.
Floating-point values are permitted only for non-proof-bearing resource/timing metadata. A float
in a count, index, prefix, coefficient, digest input, or residual is FAIL.

Required fields and nesting will be taken only from the frozen manifest's declared output
contract and frozen mathematical specification, never from the result's convenient shape. The
validator may tolerate and list unknown inert metadata, but an unknown field that affects branch
identity, ordering, arithmetic, classification, or custody is FAIL. Missing fields, wrong types,
conflicting redundant summaries, or a schema version not bound by the manifest are FAIL.

## Branch-total and census acceptance rules

All of the following are mandatory:

1. The manifest-declared domain cardinality is exactly 128.
2. The independently derived expected prefix/branch sequence contains exactly 128 unique entries.
3. The result contains exactly one terminal row for every expected entry and no other row.
4. Identity is by the manifest's semantic prefix/branch key, not merely array position. Duplicate
   keys, missing keys, out-of-domain keys, duplicate indices, index holes, or alias encodings fail.
5. Every branch is terminally classified. `skipped`, `unknown`, `unclassified`, `timeout`,
   `aborted`, `error`, or an unrecognized status is not accepted as coverage.
6. Recomputed category counts sum to 128. Every reported subtotal and branch-total must equal the
   recomputed values. A self-reported total of 128 does not cure duplicates or holes.
7. Accepted + rejected (or the manifest's exhaustive, disjoint terminal category partition) must
   equal enumerated; skipped/failed/unclassified must be zero. If the manifest's partition is not
   disjoint and exhaustive, the result is not a complete census and fails.

There is no tolerance, majority rule, or “127/128 is close enough” path.

## Exact residual and global-classification rules

For each branch, the validator will reconstruct the manifest-defined residual object in exact
arithmetic. A residual is `ZERO` iff every exact component is zero after normalization. It is
`NONZERO` iff at least one exact component is nonzero. Approximate magnitudes, printed decimals,
solver status, and producer-authored labels cannot decide this classification.

The derived global class is:

- `ALL_ZERO` iff all 128 branches are `ZERO`;
- `HAS_NONZERO` iff at least one branch is `NONZERO`;
- `INVALID` if any branch is absent, duplicated, malformed, or not exactly decidable.

The reported global class, zero/nonzero counts, and any named witness must agree with this derived
class. The “first nonzero” is the minimum nonzero branch under the independently derived frozen
prefix order, never the first row encountered in an arbitrary result array. Its prefix, index,
exact residual, and any component/witness locator must all match the independent calculation.

## Prefix ordering and digest rules

1. Derive the expected prefix sequence from the manifest's declarative enumeration rule and the
   frozen mathematical specification in a newly written audit implementation. Do not import,
   execute, copy, or call producer enumeration code. If the manifest merely lists prefixes but
   provides no independently checkable ordering rule, ordering is unverified and the audit FAILS.
2. Require result row order, declared indices, and semantic prefix keys all to equal the derived
   sequence. Sorting the result before validation is forbidden because it would hide a reorder.
3. Recompute raw SHA-256 for every bound file. Recompute canonical prefix/row/aggregate digests
   using the manifest-declared byte encoding exactly. If the digest preimage or canonicalization
   is unspecified or ambiguous, the digest gate FAILS; no guessed encoding may be chosen because
   it happens to match.
4. Require each per-prefix digest, rolling/aggregate digest, and final digest to match both its
   recomputed preimage and every redundant manifest/result pin. A digest match does not substitute
   for arithmetic replay or census reconciliation.

## Independent replay methods

The audit subtree will contain a newly written validator/replayer. It will:

1. read only blobs extracted from the frozen commits and declarative source data they bind;
2. use exact integer/rational arithmetic (`int`, `fractions.Fraction`, or an equivalently exact
   independently implemented representation);
3. independently enumerate the complete 128-prefix finite domain and reconstruct its accounting;
4. independently recompute the manifest-defined finite replay output sufficiently to classify all
   branches; and
5. independently rederive the earliest nonzero residual through a direct route that does not call
   the producer or trust the producer's residual/classification fields.

The audit may inspect frozen producer source after the lock for statement/binding comparison, but
the replay route may not import it, execute it, translate it line-for-line, or invoke any
production `--run` command. If full exact recomputation is infeasible within the audit envelope,
the receipt must say exactly which branches/components were independently recomputed; structural
census checks alone cannot earn PASS for the arithmetic claim. The minimum strategically
sufficient recomputation is the full finite accounting plus the reported earliest nonzero
residual and its immediate predecessor (or all 128 zero residuals if the class is `ALL_ZERO`).

## Positive, mutant, and hostile controls

The validator must first pass an independently constructed tiny known-answer fixture containing
at least one exact zero and one exact nonzero residual. Each hostile copy below must then produce a
nonzero exit and the expected failure category; controls run only on temporary copies, never on
the subject blobs:

1. delete one branch row;
2. duplicate one row while preserving the apparent row count;
3. swap two adjacent rows without changing their indices;
4. change a branch total/subtotal to 127 or 129;
5. change a prefix or index to an alias/out-of-domain value;
6. flip the earliest nonzero residual/classification to zero (or, for `ALL_ZERO`, plant a nonzero);
7. alter one exact residual component without updating summaries;
8. alter a per-prefix or aggregate digest;
9. alter the reported global class or earliest-witness locator only;
10. inject a duplicate JSON key in a proof-bearing object;
11. inject `NaN` or a float into a proof-bearing integer/rational field;
12. truncate the JSON document;
13. recompute naive totals after a row reorder, to show that ordering checks are not merely count
    checks; and
14. point a manifest binding at a same-named mutable working-tree file or path outside the frozen
    commit.

At least one control must be a label-preserving algebraic mutation and at least one must be an
equality-destroying mutation. A control that unexpectedly passes convicts the validator and makes
the overall verdict FAIL, even if the original artifact passes.

## Verdict rule and independence limit

Overall `PASS` requires every mandatory custody, schema, binding, census, ordering, digest,
classification, exact-replay, known-answer, and hostile-control gate above to pass. Any failed or
unresolved mandatory gate yields overall `FAIL`; there is no “PASS with caveats.” The receipt will
separately list observations that are outside this boundary.

This is a fresh-context, disjoint-implementation audit but not authenticated T2 review: the
auditor is GPT-5-lineage and the producer lineage has not yet been established. Agreement can
support at most a bounded independent-replay statement; it cannot create `REFEREED`,
`PROVED_HERE`, or `PROVED` standing.

## Prohibited actions

- Never rerun the production `--run` command.
- Never edit the producer, manifest, result, source inputs, campaign ledger, or generated views.
- Never repair a defect while auditing it.
- Never select a fallback parser, ordering, digest encoding, tolerance, or residual definition
  because it makes the frozen output pass.
