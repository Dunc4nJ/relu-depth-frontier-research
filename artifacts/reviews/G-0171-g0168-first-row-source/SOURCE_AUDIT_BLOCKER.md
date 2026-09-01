# G-0171 source/custody audit blocker — G-0168 exact first row

## Verdict

`SOURCE_CUSTODY_AUDIT_FAIL_NO_PASS_RECEIPT`

The frozen producer cannot satisfy the outcome-blind audit contract sealed in G-0171. No
`SOURCE_AUDIT_RECEIPT.json` was emitted. No G-0168 scientific manifest, scientific input, output,
or rank outcome was opened or created, and no outcome-bearing mode was run.

This is a source/custody null, not a scientific result. It does not decide either G-0168 branch or
change any mathematical standing.

## Exact frozen bindings

| Object | Commit | Path | SHA-256 | Observation |
|---|---|---|---|---|
| Scientific preregistration | `982efb2d78a7c8ca886efb9f81fa563024bdc4c1` | `artifacts/math/G-0168/PREREGISTRATION.md` | `335b82ad402ca0ccc9ca6b0124fd4f1cc133bb2d6854912a326f4e142d11b11b` | Git-object bytes rehashed; exact match |
| Audit preregistration | `024df31be1ec5fd63120ff1f37ba4811a2b9d83f` | `artifacts/reviews/G-0171-g0168-first-row-source/PREREGISTRATION.md` | `575f02a882fb8af583768f3e7b99e4d5210837049c93ef4829355ecb5cbdf15f` | committed and remotely confirmed before source inspection |
| Producer | `076da1db303b27c3b57721a258c7298ed5c6f882` | `artifacts/math/G-0168/first_row_exact_admission.py` | `e959a744a27c36be40f8de9a427921ab1ab21ffbf8added32945195b8ae77d9a` | supplied hash, Git-object hash, isolated-copy hash, and working-byte hash agree |

The producer commit has the scientific-preregistration commit as its sole parent. The audit
preregistration is a later commit. The source was inspected only after the audit preregistration
was pushed.

## Permitted executions actually observed

- Source-only Python compilation: `PASS`.
- The first source-only self-test attempt under ambient `/usr/bin/python3` stopped at import with
  `ModuleNotFoundError: No module named 'flint'`; this is not represented as a source failure.
- Source-only `--self-test` under the pinned campaign virtual environment, CPython `3.13.7` and
  python-flint `0.9.0`: `PASS` with both synthetic scientific branches, the witness-only member
  case, duplicate-key rejection, and trailing-data rejection.
- `strace` of the passing self-test found no open/create of G-0140, G-0164, G-0170, the G-0168
  scientific manifest, or the G-0168 scientific output. Its only writes were the two temporary
  malformed-JSON fixtures, which were removed.
- `--static-preflight` was not run: source lines 1358-1360 show that it calls
  `validate_static_inputs()` and therefore opens frozen scientific inputs, while the sealed audit
  boundary at preregistration lines 50-61 permits only source-only synthetic/static execution and
  keeps those paths unopened. The producer also exposes `--static-preflight` at lines 1397-1409,
  not the sealed `--preflight-static` mode name.

Observation flags for this audit are therefore:

```text
scientific_manifest_observed = false
scientific_input_observed = false
scientific_output_observed = false
scientific_run_executed = false
rank_outcome_observed = false
```

## Contract blockers

### C1 — the frozen producer cannot parse the sealed receipt contract

The audit preregistration fixes the exact receipt shape and 28 required-check names at lines
288-355. The producer instead hard-codes a disjoint 16-name check set at source lines 140-157 and
a different envelope at lines 1001-1056:

- producer expects `audit_preregistration`; the seal requires `preregistration`;
- producer omits required `rank_outcome_observed`;
- producer reviewer has exactly `agent_name` and `model`; the seal requires `agent_name`,
  `program`, `model`, `same_model_lineage`, and `fresh_context`;
- producer subject is a fixed four-entry object; the seal requires the source commit plus complete
  `source_bindings` and `transitive_build_bindings` arrays;
- producer claim-boundary and no-claim strings differ from the exact sealed strings; and
- none of the producer's 16 required-check identifiers equals any of the sealed 28 identifiers.

Because source line 1045 requires literal equality with the producer's legacy check object, a
receipt conforming to G-0171 must be rejected by the producer. Changing the receipt to make the
producer accept it would violate the pre-outcome seal. This alone prohibits `PASS`.

Minimal source-only reproduction:

```text
sealed_count 28
implemented_count 16
sets_equal False
sealed_missing_in_source <all 28 sealed names>
source_extra_vs_seal <all 16 producer names>
```

Unmet preregistered checks include
`exact_source_and_transitive_build_bindings_verified`,
`strict_closed_schema_parsing_verified`, and
`live_receipt_validation_verified`.

### C2 — integer `1` passes as every required JSON boolean

Source line 1045 checks the whole required-check object with ordinary Python dictionary equality.
In Python, `1 == True`; the validator never applies `type(value) is bool` to each check. A receipt
whose sixteen check values are JSON integers `1` therefore passes this predicate, contrary to the
hostile parser requirement at audit-preregistration lines 351-355.

Minimal source-only reproduction against the frozen module:

```python
integer_mutant = {name: 1 for name in module.SOURCE_AUDIT_REQUIRED_CHECKS}
print(integer_mutant == module.SOURCE_AUDIT_REQUIRED_CHECKS)
```

Observed output:

```text
True
```

This leaves `hostile_receipt_parser_matrix_verified` and
`strict_closed_schema_parsing_verified` false.

## Evidence-quality blockers

### E1 — rank-growth output omits the sealed zero-prefix Schur digest

The seal requires the canonical scan to bind visited count, first witness identity, and a canonical
prefix transcript/census digest at audit-preregistration lines 164-173. The producer constructs and
updates `residual_digest` at source lines 1229 and 1259-1260, but passes it only into the all-zero
dependency branch at lines 1284-1295. The rank-growth output at lines 1302-1354 includes scan count
and witness data but not that running digest.

The source-only rank fixture confirms the omission:

```text
result FIRST_ROW_EXACT_RANK_GROWTH
witness_sequence 2
has_running_prefix_digest False
```

The fixed loop and exact witness remain useful, but they do not satisfy the explicit durable
prefix-binding requirement. Independent reproducibility does not authorize waiving a predeclared
artifact field. `canonical_first_exact_reduced_price_scan_verified` is false.

### E2 — dependency branch asserts the member bridge without replaying `A c = s b`

The seal requires exact replays of both `A c = s b` on all 540 old rows and `h c = r` before the
dependency separator may report the target bridge (audit-preregistration lines 198-217).

The producer's `exact_dependency_branch` signature at source lines 616-624 receives neither the
matrix nor member coefficients. Lines 625-655 check only the scalar identity
`d r = s (w^T b)` and then set `member_bridge_identity_verified` to true. Its scientific call at
lines 1287-1295 likewise supplies no `A`, basis matrix, or `c`. The prior member's report flags are
therefore inherited instead of replayed on this branch.

A source-only fixture deliberately supplied a member with the right scalar bridge but the wrong
old-row target:

```python
A = [[1, 0, 1], [0, 1, 1]]
b = [1, 1]
h = [2, 3, 5]                 # h = [2,3]^T A
c = [4, -1, 0]                # h c = 5 = [2,3]^T b
# A c = [4,-1] != [1,1]
result, branch = module.synthetic_model(A, b, h, c, 1)
```

Observed output:

```text
Ac [4, -1]
b [1, 1]
Ac_equals_b False
result FIRST_ROW_EXACT_INCOMPATIBLE_DEPENDENCY
member_bridge_identity_verified True
```

Thus the unchanged production logic can certify the dependency bridge while its stated member
premise is false. `dependency_separator_target_bridge_verified` is false.

## Disposition and resolving step

No passing JSON receipt exists or was attempted. The exact source remains read-only.

The cheapest resolution is a new producer revision that, without changing this preregistration:

1. implements the exact sealed receipt envelope, strings, five false flags, binding arrays, and 28
   strict boolean names, with per-value boolean type checks and hostile mutations;
2. publishes the running exact Schur prefix digest in the rank-growth branch;
3. replays `A c = s b` over all 540 rows and `h c = r` before the dependency bridge flag; and
4. provides a genuinely source-only static-preflight mode matching the sealed name and boundary.

That revision must be frozen at a new commit/hash and audited as a new immutable subject. The
scientific manifest and run remain prohibited until that audit passes.
