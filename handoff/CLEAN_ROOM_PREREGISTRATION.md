# EXP-0002 — clean-room MAX5–MAX10 reproduction preregistration

**Registered:** 2026-08-29T05:38:00Z · **Route:** H-0001 · **Gap:** G-0001 ·
**Claim under test:** C-0003@1 · **Mode:** confirmatory only after Stage A review

This experiment qualifies known-result machinery before any MAX11 search. It cannot support MAX11,
the completeness of the certificate family, or the universal conjecture. Replaying known work is a
control and reconstruction result, not frontier progress by itself.

## Independence and contamination boundary

The clean-room implementation author receives a fresh conversation context and may read only:

- this preregistration and the campaign charter/specification/epistemics;
- `subjects/max-relu-known/certificates/*.json` and `SUBJECT_MANIFEST.sha256`;
- retained paper passages/source cards for REF-0001 and REF-0002;
- public mathematical/library documentation needed for a fresh implementation.

The author must not open, import, copy, diff, or indirectly summarize:

- `literature/repos/max-relu-certificates/verify_certificate.py`;
- code derived from that verifier, including another agent's implementation;
- the quarantined `imports/target-selection-2026-08-27/` scripts;
- execution output from the upstream verifier before freezing the clean-room code.

The research lead and experiment designer have inspected upstream code, so neither may author the
clean-room implementation. The worker must disclose every file read. Touching a forbidden input makes
the independence result `cannot-verify`; mathematical findings may be retained with that attribution.
Implementation independence is T1 and shares the paper's hinge-normal-form method; it is not T2/T3.

## Frozen subject

Subject manifest: `subjects/max-relu-known/SUBJECT_MANIFEST.sha256`, SHA-256
`70851ae4fdd20ddc53a87b7817effd8efb983d721e518bcf6ef8c5a9edf848f2`.

| n | k | terms | byte SHA-256 | normalized JSON SHA-256 | term-permutation contributions |
|---:|---:|---:|---|---|---:|
| 5 | 2 | 3 | `698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694` | `757d8f0dc23729a54059044a464ea2795486b20f3b2de2465f4cd5647691846f` | 360 |
| 6 | 2 | 4 | `026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83` | `b5e5ca7eb0e69a88d988285e847da6816b7eda07aff5664fef2b3b527e14daaa` | 2,880 |
| 7 | 3 | 57 | `b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be` | `bc2ec7ed82d98f24d1480a72d0899e2c8d4c7075fb3a167616c860d815931448` | 287,280 |
| 8 | 3 | 69 | `68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3` | `5db584c920faf7298ef4e069d073e418f26fd6ef1c30ac62260e3f72b9af9961` | 2,782,080 |
| 9 | 4 | 337 | `4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88` | `1741b37cc316f704897d541f70a118642d07a6ca3af41c71fe929a6d2ab5f423` | 122,290,560 |
| 10 | 4 | 402 | `10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4` | `354f9fab7bdf02b71ad55bbfcdbb8fb962bb479376d4b8fa2762711721c29473` | 1,458,777,600 |

Aggregate contract: six files, 872 terms, 1,584,140,760 labelled term-permutation
contributions. `scripts/audit-certificate-corpus.py` checks only this input contract; it is not a
certificate verifier.

The parser must enforce exact registered `n`, term count and `k`; two equal-length ordered multisets
per term; genuine integer (not Boolean) endpoints `1 <= a <= b <= n`; legal loops and repetitions;
exact nonzero rational coefficients; no float conversion; unnormalized summation over all `n!`
permutations; byte and normalized-content hashes; and refusal on unknown keys or extra files.

## Mathematical object and hypotheses

For each registered certificate, test exactly over all real inputs:

```text
G_n(x) = sum_t lambda_t sum_{sigma in S_n}
  max(
    sum_{(a,b) in A_t} max(x_{sigma(a)}, x_{sigma(b)}),
    sum_{(a,b) in B_t} max(x_{sigma(a)}, x_{sigma(b)})
  )
       = MAX_n(x).
```

- CR-H1: every pristine registered certificate satisfies the exact global identity.
- CR-H2: a fresh implementation reaches the verdict without upstream verification code.
- CR-H3: the algebraic atom identity compiles separately to the exact finite, skip-free,
  two-hidden-ReLU-layer architecture.
- CR-H4: all six subject-bound controls accept known truth and reject planted defects.
- CR-H5: every registered contribution/shard is accounted for; timeout, cache miss, skip, or absent
  shard cannot become success.

Failure of any hypothesis rejects the combined reproduction claim. Partial success is labelled by
arity and by identity-versus-compiler layer.

## Clean-room verification contract

Implement a fresh exact integer/sparse path, not a transcription of upstream code:

1. compute the coefficient-denominator LCM and integerize all coefficients;
2. on the ordered cone `x_1 <= ... <= x_n`, convert every labelled side to its exact integer linear form;
3. expand each outer maximum into a base linear form plus a ReLU hinge;
4. canonicalize every hinge by exact sign, GCD, and primitive orientation;
5. accumulate a sparse integer hinge map and integer linear vector;
6. accept only when every hinge coefficient is exactly zero and the linear vector is exactly `L e_n`;
7. canonically serialize and hash the complete residual state and census.

Agreement on sampled points is never acceptance. Equality on the ordered cone plus the explicitly
checked symmetrization transport is the global-identity argument. A later upstream replay is a separate
route and must not be shown to the clean-room author before code freeze.

## Separate architecture bridge

The scalar no-skip identities are:

```text
max(x_i,x_j) = ReLU(x_i-x_j) + (ReLU(x_j)-ReLU(-x_j))
max(U,V)     = ReLU(U-V)     + (ReLU(V)-ReLU(-V)).
```

They imply a lazy finite indexed network with first width at most `choose(n,2)+2n`, three second-layer
neurons per labelled atom block, affine output, and zero biases. The exact symbolic bounds are:

| n | first width <= | labelled blocks <= | second width <= |
|---:|---:|---:|---:|
| 5 | 20 | 360 | 1,080 |
| 6 | 27 | 2,880 | 8,640 |
| 7 | 35 | 287,280 | 861,840 |
| 8 | 44 | 2,782,080 | 8,346,240 |
| 9 | 54 | 122,290,560 | 366,871,680 |
| 10 | 65 | 1,458,777,600 | 4,376,332,800 |

`Formalization.Basic.max_eq_three_relu` kernel-checks the scalar identity. It does not yet formalize
the finite indexed compiler, symmetrization, or any certificate. Identity verification can pass while
CR-H3 remains open; no architecture claim is laundered across that gap.

## Six exact controls

Every control artifact records both arms, normalized subject IDs, implementation/environment hashes,
counts, timing, RSS, verdict and complete output digest.

| method | honest/positive arm | hostile/null arm |
|---|---|---|
| `known-answer` | hand-derived MAX2 fixture and all pristine registered subjects pass | exact global coefficient scaling by 2, target unchanged, is rejected |
| `sweep-plant-recovery` | fresh relabelled valid MAX10 subject in the final deterministic shard is recovered | final shard removed produces explicit incomplete/red, never clean |
| `empty-region-null` | neighboring registered nonempty path is exercised | a preregistered `A=B` loop-only family, analytically symmetric-linear and not MAX for n>=2, returns no witness |
| `census-reconciliation` | files, 872 terms, shards and 1,584,140,760 contributions reconcile with zero unclassified | one omitted/duplicated contribution is detected independently |
| `trivial-witness-null` | a valid shape-correct subject passes | empty, zero, random, metadata-mismatched, loop-linear and exact corruptions fail |
| `metamorphic-invariance` | relabelling, side swap and pair/term reorder preserve; positive target-and-coefficient scaling preserves | coefficient scaling by `1+2^-128` with target fixed flips acceptance |

Bundled skill demos do not discharge these controls. A control that cannot fail or fires on both arms
is red. Cache keys must include normalized subject bytes and mutation ID.

## Detection floor and no-claim boundary

- Arithmetic verdict: exact rational/integer zero versus nonzero; no tolerance.
- Demonstrated perturbation potency: relative coefficient change `2^-128` on the registered subjects.
- Census floor: one missing registered contribution is detectable by independent manifest arithmetic.
- Checked domain: only the six pinned rational subjects, registered transformations, and scalar compiler
  identities. Global equality is algebraic, not sampled.
- No inference about irrational candidates, other formats, MAX11, ansatz completeness, arbitrary
  two-hidden-layer networks, width practicality, or universal `n`.

The honest eventual wording is: “exact for every parsed rational in this registered corpus; mutation
potency demonstrated down to `2^-128`.” Parser refusal or resource exhaustion bounds that sentence.

## Stages, resource ceilings and stops

### Stage A — implementation only

Fresh-context worker writes parser, exact accumulator, unit tests, canonical residual format and control
harness. It may run hand-derived MAX2/parser tests but **must not run the six registered subjects**.
Stop and hand back for lead inspection. Ceiling: 60 minutes, 4 CPU-hours, 4 GiB RAM, 1 GiB scratch.

### Stage B — small known arities after lead approval

Freeze code/environment/subject hashes as a new implementation claim, then run MAX5–MAX8 and all
controls that do not require MAX10. Any code change returns to Stage A/freeze. Ceiling: 60 minutes,
8 CPU-hours, 8 GiB RAM, 2 GiB scratch.

### Stage C — MAX9/MAX10 after Stage B review

Run sharded exact verification, MAX10 plant/census controls, and the independent upstream route.
Ceiling for the clean-room path: four wall-clock hours on at most eight workers; whole two-route
battery: 24 CPU-hours, 16 GiB RAM, 10 GiB scratch. Timeout, OOM, missing shard, hash drift, or
incomplete census is `aborted/cannot-verify`, never certificate rejection. Retry requires a new logged
experiment after a hash-bound work reduction, optimized enumerator, or enlarged approved budget.

Any forbidden-file access, float coercion, silent truncation, hash mismatch, or ambiguous permutation
normalization stops immediately. No cache reuse across metamorphic arms unless cache behavior itself is
preregistered and the normalized mutation identity is in the key.

## Required artifacts

Stage A: contamination declaration and read log; source/tests; parser contract; implementation notes;
MAX2/control unit artifacts; exact commands; timing/RSS; handoff. Stages B/C additionally require:
implementation-claim hashes; environment and subject manifests; per-subject canonical residual/census;
per-control JSON with both arms; shard reconciliation; upstream transcript; lazy architecture manifest;
Lean build/trust/statement-match record; replay command; ledger evidence/review records.

Artifacts land under `artifacts/cleanroom/EXP-0002/`. The research lead inspects Stage A before any
registered subject is executed and independently adjudicates every later result.

## Outcome interpretation

- All routes/controls pass: G-0001 may close after independent replay and ledger verification; T2 is
  still unavailable, so no `REFEREED` promotion.
- Clean room fails/upstream passes or vice versa: freeze and reconcile; no mathematical refutation.
- Identity passes/compiler remains open: only the algebraic identity was replayed.
- Partial arities pass: report exactly those arities.
- Any gate fails: machinery remains unqualified.
- Resource null: only this bounded implementation failed to finish under this budget.
- No outcome bears on MAX11 or unrestricted certificate-family completeness.
