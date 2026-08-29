# G-0014 semantic matrix audit

## Verdict

**PASS, within the finite-family claim boundary below.**  A fresh evaluator
regenerated and exactly compared every one of the `7,146 x 9,804 =
70,059,384` signed 64-bit integer coefficients in the registered cut matrix.
There were zero mismatched entries and zero mismatched columns.  The
regenerated C-order matrix digest exactly equals the frozen matrix-array
digest:

`aaa4f481f6e29f05ac226f2de44e3829563190fd6daddd8a66130e9257493b0c`.

This discharges the G-0014 graph-to-matrix semantic gate for the registered
family.  It does **not** prove that the family is complete, regenerate the
adaptive provenance of the frozen 7,135-direction list, audit the exact
rational dual arithmetic, or settle unrestricted two-hidden-layer `MAX11`.

## Bound evidence

The successful run was:

```text
/usr/bin/time -v python3 artifacts/math/G-0014/semantic_matrix_audit.py \
  --workers 6 --max-tasks-per-child 25 --progress-every 50
```

It exited zero after 1:31:10 wall time and wrote the machine report below.
All frozen input hashes were checked before and after the replay and were
unchanged.

| Object | SHA-256 |
|---|---|
| audit producer | `e2042e7508606d2da926f345cdf9d42a3c114ea83aee5ae23f84705e02c4775c` |
| machine report | `581a8d9b5a1cd28f1ee2896e119a262977084369d32550ca8523fd205596ec71` |
| pinned MAX10 source certificate | `10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4` |
| frozen quotient/classes | `3f24edd0b8928256e90fe41fbafd846b693efd37285065da907a1ffdf9561f48` |
| frozen direction selection | `e37b7637a9edf541ac5e1caf6bebd98f8d04b928ee1525bfaaa194474d5ef235` |
| frozen cut-matrix archive | `acfbb2b0f89e5cca6c72b396ec1c86e0558e3a5e759e5c7f2d29f5ba03f5e758` |
| frozen exact-dual object | `fe6768c8377aa1cc813dbd00805c807d4dd23f05ba246700503aa8598a951758` |

Authoritative artifacts:

- `semantic_matrix_audit.py` is the independently implemented evaluator. It
  imports no G-0006/G-0008/G-0010/G-0011 generator or solver module.
- `semantic_matrix_audit_v1.json` is the canonical machine report from the
  successful exhaustive run. It was not hand-edited.

## What was independently reconstructed

The audited atom is exactly

```text
max(sum_{uv in A} max(x_u,x_v), sum_{uv in B} max(x_u,x_v)).
```

The evaluator independently:

1. filtered 252 eligible terms from the pinned `MAX10` certificate and
   reconstructed the 16,000 same-component two-edge lifts;
2. reconstructed the colored-graph quotient with a local exact
   individualization/refinement canonical labeler, obtaining 9,804 classes;
3. verified the frozen representative of every class against the independently
   reconstructed partition and bound matrix column `j` to frozen class `j`;
4. validated all 7,135 frozen hinge directions as integral, nonzero,
   zero-sum, primitive, first-nonzero-positive, unique, lexicographically
   sorted, and active on the ordered cone;
5. derived signed adjacency/back-degree words, oriented primitive hinge
   coefficients, and all 11 linear coefficients; and
6. streamed every regenerated column against the frozen matrix while hashing
   the regenerated matrix independently.

The raw-list serialization with its required trailing newline has digest
`d1c6755e5585c5c4f3160589bcb21ca1a989161fb289946b9bbb935a0d6cd569`,
exactly matching the quotient artifact.  The quotient partition, mapped class
sizes, frozen representative bindings, and recorded raw-list hash all match.

Four synthetic controls (`n=4,5,6,7`) compare the dynamic program against
direct permutation enumeration, direct hinge/linear decomposition, and direct
ordered-grid evaluation of the pairwise-max atom.  An endpoint-sum semantic
mutant is explicitly rejected.  The controls passed again after the
exhaustive run.

The 5,270 exact-dual support rows bind to 51,667,080 of the regenerated
entries, all of which match.  This is a support-row binding check, not a replay
of the rational dual arithmetic.  The target check confirms the registered
ordered-chamber convention: every target coordinate is zero except row 7,145,
whose value is `11! = 39,916,800`.  It is a convention/theorem check rather
than an independently retrieved target artifact.

## Run history and lineage limits

Only the final successful run is evidence.  Earlier incomplete runs were
stopped before producing a report: one exposed an over-strong assumption
about numeric class labels, one exposed a raw serialization-order mismatch,
and one reached 2,550 columns before being stopped to avoid an out-of-memory
failure.  The successful producer uses partition-bijection semantics,
component-major raw ordering, and bounded worker recycling.

The raw ordering correction was informed by comparison with the frozen raw
hash.  Therefore this is not a blind reconstruction of serialization
provenance.  The semantic raw set, exact quotient, representative binding,
normal-form evaluator, and all matrix coefficients are nevertheless
independently recomputed.  This evidence remains same-host, same
CPython/NumPy, same-agent-lineage evidence (T1), not an independent T2 referee
replication.

## Real-work and honesty check

Window: this G-0014 subtask.  Core purpose: determine whether finite `MAX_n`
has an exact two-hidden-ReLU-layer representation, with `MAX11` as the first
unsettled retrieved rung.  Inventory: `USER=0`, `ENABLER=1` (the evaluator and
successful exhaustive replay), `PROCESS=2` (machine report and this audit),
`UNKNOWN=0`.  The computation dominates the work and is consumed directly by
the pending G-0015 theorem and G-0016 referee gate.  The process artifacts are
bounded to reproducibility and claim control; no new workflow machinery is
created.  Verdict: **HEALTHY for a research-proof gate**.  This audit retires
after theorem adjudication; it does not become a recurring ceremony.

Bounded honesty inventory:

1. No (checked: no test, CI, lint, or gate configuration was modified; the
   G-0014 directory is new and untracked in the current worktree).
2. No (checked: controls use direct enumeration/evaluation, not mocks,
   fixtures, stubs, or doubles).
3. No (checked: the frozen matrix and its digest were never regenerated or
   edited; the report records a fresh comparison).
4. No (checked: the audited matrix, quotient, selection, source certificate,
   and dual were read-only and hash-stable; no suppression, bypass, timeout,
   retry, or tolerance relaxation was introduced).
5. No (checked: there is no subject-specific branch, environment sniff, or
   reduced denominator; the global serialization-order correction is
   disclosed above and every matrix entry remained in scope).
6. No (checked: four positive control instances and one planted negative ran,
   followed by all 9,804 subject columns).
7. No (checked: every cited command and result above was executed and observed
   in this session).
8. No (checked: the report calls this a replay and this audit labels it T1,
   not live/blind/T2 confirmation).
9. No (checked: all aborted runs and every material residual limitation are
   disclosed above).
10. No (checked: the successful PTY captured normal output, errors, exit
    status, and `/usr/bin/time -v`; cited evidence did not discard stderr).
11. No (checked: no task was closed by this subtask; completion is reported
    only after the exhaustive gate passed).
12. No (checked: no specification, theorem statement, or acceptance condition
    was edited to fit the result).
13. No (checked: this subagent did not close its own or a peer's tracker item).
14. No (checked: dispatch required a full positive observable, mismatch-first
    failure, controls, hashes, and explicit no-claim boundary).
15. No (checked: no subordinate agent report was accepted; this evaluator and
    replay were executed locally by the assigned auditor).
16. No (checked: no refusal/error-path items or closure metrics were farmed).
17. No (checked: PASS rests on exact independent recomputation and byte
    equality, not agent agreement).
18. No (checked: the denominator `7,146 x 9,804` and full-matrix requirement
    were fixed before the successful run).
19. Yes: the raw serialization order was corrected after the frozen hash
    exposed the initial mismatch.  Correction and disclosure are the T1-only
    claim above; the RH-2 countermeasure is to forbid describing this as blind
    or T2-independent evidence and to retain the failed-run history.
20. Strongest evidence: re-execute the hash-bound producer and obtain zero
    mismatches plus regenerated matrix digest
    `aaa4f481f6e29f05ac226f2de44e3829563190fd6daddd8a66130e9257493b0c`.

A bounded CASS sweep for the standard honesty phrases plus G-0014-specific
terms found no hit in this project/session; generic hits belonged to unrelated
projects and were not treated as evidence here.
