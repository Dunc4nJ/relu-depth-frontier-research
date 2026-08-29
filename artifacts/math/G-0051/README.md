# G-0051 — memory-safe signed-mass ≤4 quotient design

## Bottom line

The signed-mass-4 computation must use the complete **99,858-row primitive
degree-four hinge universe**.  The 10,065 degree-three rows used by G-0050
embed into it but omit 89,793 valid mass-four directions.  No global
mass-four conclusion may be based on the smaller system.

The corrected finite subject is

| object | count |
|---|---:|
| proper-support columns, signed mass 1–4 | 136,035 |
| full-support columns, signed mass 1–4 | 1,468 |
| literal total | 137,503 |
| degree-four primitive hinge rows | 99,858 |

G-0050 already proves over `Q` that its 488 proper basis columns span all
3,307 proper signed-mass-≤3 columns.  Those columns have no degree-four-only
hinges, and the 10,065 degree-three directions are an exact subset of the
degree-four universe.  Subject to an explicit embedding replay, the
span-equivalent mass-≤4 computation can therefore retain

```text
488 low-mass proper basis columns
+ 3 low-mass full-support seeds
+ 134,193 signed-mass-4 columns
= 134,684 columns.
```

This saves only 2,819 columns; its real value is preserving an already exact
low-mass basis rather than rediscovering it.

## The decisive algebra

Let `H` be the `99,858 x C` integer hinge matrix on any selected column set,
and let `lambda` be the exact eleventh binary-finite-difference row.  It is
zero on every proper-support column.  A hinge-free combination with nonzero
MAX11 direction exists precisely when

```text
rank_Q([H; lambda]) = rank_Q(H) + 1.                 (1)
```

Equivalently, there is a coefficient vector `c` with

```text
H c = 0,       lambda c != 0.
```

This makes **column-subset positives one-sided and constructive**: a relation
on any selected subset remains a relation in the complete family after all
unselected coefficients are set to zero.  A negative on a subset says
nothing about omitted columns.

There is a second sufficient positive gate.  If the complete proper block
`H_P` has row rank 99,858 modulo one prime, it has row rank 99,858 over `Q`.
Every full-support hinge column is then in `col_Q(H_P)`, so any full seed with
nonzero `lambda` has a rational cancellation.  An explicit rational witness
and linear-part correction would still be required before claiming an
identity.

## Corrected resources

Dense materialisation is not the plan:

| stage | columns | int64 dense | one-prime uint32 dense |
|---|---:|---:|---:|
| signed-mass-4 full seeds only | 1,465 | 1.17 GB | 0.59 GB |
| all full seeds + G-0050 proper basis | 1,956 | 1.56 GB | 0.78 GB |
| plus every active-10 mass-4 proper column | 6,965 | 5.56 GB | 2.78 GB |
| plus every active-9 mass-4 proper column | 20,582 | 16.44 GB | 8.22 GB |
| complete span-equivalent subject | 134,684 | 107.59 GB | 53.79 GB |
| literal complete subject | 137,503 | 109.85 GB | 54.92 GB |

The row support census is

```text
support size:      3      4       5       6       7      8
row count:       825   8,250  28,182  38,346  20,790  3,465
```

A column on `r` active coordinates is zero on every row of support greater
than `r`.  This exact zero pattern supplies a descending-support filtration
for sparse elimination.

Bounded exploratory samples showed between 0 and 33,502 nonzeros per column,
with many columns in the hundreds or low thousands.  That makes a canonical
CSC stream plausible; it does **not** bound the complete nonzero count.  The
hash-selected preflight below produces a non-postselected planning estimate.

### Executed preflight and the G-0052 early-gate reduction

The bounded 80-column hash-selected preflight completed in 29.6 seconds.  Its
planning extrapolation—not a bound—was 1.668 billion mass-four nonzeros,
approximately 20.02 GB as `(row_u32,value_i64)` CSC or 13.35 GB as a one-prime
`(row_u32,value_u32)` stream.  It projected 7.28 single-worker hours and 54.6
idealised eight-worker minutes for semantic generation.  Therefore the
complete persistent CSC **fails the current 12 GiB launch gate** and S3 is not
authorised without a chunked-compression/matvec benchmark.

Frozen preflight:

- `preflight_benchmark_v1.json`, SHA-256
  `89faea4146e589c33548130bcb466696c873d7aaab7e0d602e602363f06c34e6`;
- producer SHA-256
  `c08cdc0520970995bf47ab64483f33845c9468d8fd9a1e1b01be2060c02baa1b`.

G-0052 subsequently completed the exact 1,465-seed census.  It found

```text
exact total seed nonzeros:       12,331,131
exact global nonzero-row union:      42,457 / 99,858
per-seed support: minimum 714, median 8,155, maximum 21,854
lambda: 1,111 nonzero seeds, 354 zero seeds
eight-worker semantic wall time: 331.2 seconds
```

Report SHA-256:
`23658ef43603cc775a2938789bd2792616a018b726d7272981c24186fd071b37`.
It independently asserts that every emitted hinge lies in the frozen
99,858-row universe.

For a **fixed selected column set**, restricting the rank matrix to the exact
union of its nonzero rows loses no equation: every omitted row is explicitly
zero on every selected column.  This is not row sampling.  Consequently S0
can use the exact `42,457 x 1,465` matrix—0.498 GB int64 or 0.249 GB for one
prime.  For S1, adjoining the 491 low-mass columns gives the rigorous worst
case

```text
42,457 seed-union rows + 10,065 degree-three rows = 52,522 rows,
```

so its exact dense matrix is at most `52,522 x 1,956`: 0.822 GB int64 or
0.411 GB for one prime.  The actual S1 union can only be smaller.  These two
early gates are now plausible exact dense-FLINT jobs; the full denominator is
still a sparse/streaming problem.

## Data path

The large matrix is never held as dense integers.

1. Enumerate and hash the 99,858 directions once.  Assert that all 10,065
   degree-three directions occur in this set.
2. Stream canonical G-0038 records in frozen sequence order.
3. Independently reconstruct each exact integer column as sorted
   `(row_u32, value_i64)` pairs.  Reject duplicate rows, explicit zeros,
   invalid directions, support violations, and nonzero `lambda` on proper
   support.
4. Write one append-only, hash-framed CSC object: `col_ptr_u64`, `row_u32`,
   `value_i64`, column descriptors, per-stratum digests, and exact `lambda`.
   One CSC traversal implements both `H*x` and `H^T*y`; a second CSR copy is
   unnecessary until a benchmark proves otherwise.
5. Reduce values modulo each prime while streaming.  Never persist two dense
   prime matrices.

The G-0050 488-column basis must receive a separate embedding control: replay
all 3,307 low-mass proper columns against it on every degree-three row and
verify that all 89,793 new degree-four-only rows are zero.

## Staged falsification and construction gates

Every stage uses **all 99,858 rows semantically**, either through an exact
sparse column or through a deterministic linear map of the complete row
vector.  A row sample may nominate a candidate but never certify it.

### S0 — mass-four full seeds only

Use the 1,465 signed-mass-4 full-support columns.  Reconstruct each column
against the complete 99,858-direction dictionary, reject any out-of-universe
hinge, and freeze the exact nonzero-row union.  G-0052 predicts 42,457 union
rows; the independent gate must regenerate and hash-bind that set.  Build the
exact union-restricted dense matrix at both frozen primes.

- If `rank_p(H)=1,465`, then `rank_Q(H)=1,465`; this exactly excludes a
  seed-only rational circuit.
- Otherwise compare the exact modular ranks of `H` and `[H;lambda]`.  A gain
  licenses extracting `c`; replay it against all 99,858 rows and require
  `lambda*c != 0`.
- Modular gain at two primes is still only a rational-lifting candidate.

### S1 — add the exact low-mass core

Append the three signed-mass-3 full seeds and the frozen 488-column proper
basis: 1,956 columns total.  Recompute the exact row union.  Its rigorous
upper bound is 52,522 rows, so the union-restricted dense matrix is at most
0.822 GB int64.  Repeat the exact two-prime rank/augmented-rank calculation.
This is the fastest serious gate.

### S2 — add mass-four proper columns by support leverage

Append complete columns in this frozen order:

```text
active vertices 10, 9, 8, 7, 6, 5, 4, 3, 2;
canonical G-0038 sequence order within each stratum;
checkpoints every 2,048 columns and at every stratum boundary.
```

High-active-support columns come first because only active-8-through-10
proper columns can address the support-8 row block.  At every checkpoint:

1. update the primary deterministic sketch basis;
2. test (1) over both primes;
3. validate any proposed relation on independent held-out sketches;
4. replay survivors exactly on all complete rows;
5. add the lexicographically first nonzero residual row to an actual-row
   CEGIS basis before retrying.

For a fixed column subset, each failed full replay adds a genuinely new row
constraint.  A successful replay is a real modular circuit.  This provides a
finite retry rule rather than repeated random fitting.

The deterministic sketch machinery begins at S2.  S0 and S1 should use their
complete exact nonzero-row unions directly unless the dense-rank benchmark
fails its memory/time control.

### S3 — complete denominator only if S0–S2 justify it

If no subset produces a replayed circuit, complete all 132,728 proper
mass-four columns.  Dense elimination is forbidden.  Benchmark two backends:

1. support-prioritised sparse PLUQ/Markowitz elimination for the actual-row
   CEGIS basis;
2. a pinned LinBox sparse/Wiedemann black-box harness over the CSC matvec.

LinBox documents memory-efficient Wiedemann methods for large sparse exact
systems, but an open 2026 upstream issue reports an out-of-bounds failure in
one finite-field black-box rank path.  It is therefore a candidate backend,
not trusted infrastructure, until it passes the controls below.  No solver
status is evidence without an extracted object and direct replay.

## Certification paths

### Positive modular candidate

1. Hash-bind its column support and coefficients.
2. Directly replay all 99,858 hinge rows and `lambda` at each prime.
3. Repeat at additional primes with a common pivot/support plan.
4. Reconstruct rational coefficients by CRT/rational reconstruction or solve
   the fixed subsystem exactly over `Q`.
5. Replay the rational vector against streamed integer columns on all rows.
6. Compute the remaining ordered-chamber linear vector and correct it using
   the frozen lower-order/base atoms; verify the final MAX11 normal form.
7. Run an independent semantic verifier with coefficient, endpoint, row,
   duplicate-key, and omitted-degree-four-row hostile controls.

Two-prime modular agreement is only a lifting license, never an identity.

### Complete negative

A modular no-gain result is not a rational obstruction.  A complete negative
requires an exact rational row dual `y` satisfying

```text
y^T H = lambda
```

on every one of the 134,684 span-equivalent columns, followed by a direct
streaming replay.  Alternatively, full column rank modulo a prime exactly
excludes a relation on a subset with at most 99,858 columns.  A failed search,
rank agreement at a few primes, or exhausted compute budget is not a negative
theorem.

## Benchmark/launch gate

Run only bounded preflight work first:

```bash
.venv/bin/python -B artifacts/math/G-0051/preflight_resource_estimator.py --self-test
.venv/bin/python -B artifacts/math/G-0051/preflight_resource_estimator.py \
  --preflight-only
.venv/bin/python -B artifacts/math/G-0051/preflight_resource_estimator.py \
  --preflight-only --sample-per-stratum 8 \
  --output artifacts/math/G-0051/preflight_benchmark_v1.json
```

The script hard-caps the semantic sample at eight columns per mass-four
stratum.  Before S0 is launched, the orchestrator must see:

- agreement with the G-0050 known rank-488/rank-491 control;
- planted positive, planted zero-`lambda` dependency, and full-rank negative
  controls;
- identical column/replay digests under 1-worker and multi-worker generation;
- estimated canonical CSC below 12 GiB and projected peak RSS below 24 GiB on
  the current no-swap host;
- no more than two hours projected eight-worker generation time;
- a measured sparse-matvec and small-rank benchmark, with both prime results
  agreeing on the controls.

If these gates fail, stop and redesign.  Do not silently fall back to the
10,065-row system or materialise the 110 GB dense matrix.

## Claim boundary

Even a certified relation would settle only the frozen fully symmetrised
loop-inclusive degree-five pair-orbit ansatz unless the resulting identity is
compiled into the declared two-hidden-layer architecture.  A complete
negative would remain a bounded ansatz theorem and would not refute arbitrary
two-hidden-layer real-weight networks.
