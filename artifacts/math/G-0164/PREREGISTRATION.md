# G-0164 preregistration — direct all-128 exact-basis member and global replay

Date: 2026-09-01

## Question and epistemic boundary

This study asks whether the single deterministic rational member obtained by
solving the certified 349-column basis of the complete G-0140 540-row system
has an exactly zero complete ordered-chamber residual for MAX11.

The finite-system member is fixed before its coefficients are computed.  It is
not chosen for sparsity, coefficient size, residual behavior, or any observed
global outcome.  Finite membership is not a MAX11 identity.  A nonzero global
residual refutes only this one member of a large affine finite-row solution
space; it does not refute every member, the frozen family, or unrestricted
two-hidden-layer representation.

## Outcome-aware starting facts

The following facts were known before this protocol was frozen:

- G-0140 Stage A replayed all 5,388,768,000 labelled permutations of the
  135-term G-0135 member and found 146,950 nonzero hinge directions.  Receipt:
  `artifacts/math/G-0140/pool128_global_replay_v1.json`, SHA-256
  `13735a5c6fc987864c97d8c466863f0de376e5dc8fe446381fdc2d1ebd302e4c`.
- G-0140 Stage B priced every one of the first 128 deterministic residual
  directions on all 163,740 family records.  Receipt:
  `artifacts/math/G-0140/pool128_coordinate_prices_v1.json`, SHA-256
  `7a923266e812bdd29fad2ecdf2d6b5cf2be85e4aacab3f92fe82bfd3b89f5c81`.
- G-0140 Stage C certified over exact Q that the complete 412-row base matrix
  has rank 221, that all 128 appended rows grow rank by exactly one in order,
  and that the complete 540-row matrix has rank 349.  Its 349 certified basis
  columns span all 163,740 family columns.  Receipt:
  `artifacts/math/G-0140/pool128_exact_rank_selection_v1.json`, SHA-256
  `d2a847b2d39b9111804cac1c3e4f9cc9f1fa152598c5a98610b7c5cc68cb9ba6`.
- The G-0135 target is feasible on the first 412 rows.  Since every appended
  zero-target row grows the ordinary matrix rank by one, the augmented rank can
  grow by at most one and therefore stays equal to the ordinary rank at every
  prefix.  Thus the all-128 finite target is already known to be feasible over
  Q in the frozen family.  The unknown scientific outcome is global zero, not
  finite feasibility.
- No coefficient of the deterministic all-128 member and no part of its global
  residual has been computed or inspected at preregistration time.

## Frozen deterministic construction

Constants:

- `N = 11`
- family records: 163,740 in canonical sequence order
- base rows: 412
- appended Pool rows: all 128 in Stage-A/Stage-B order
- total rows: 540
- targets: the immutable 412-entry unscaled G-0135 target followed by 128
  exact zeros
- exact matrix rank: 349

Let `M` be the complete `540 x 163740` integer coordinate matrix and `b` its
540-entry target.  Read, without modification or outcome-dependent selection,

- `S = complete_column_basis.basis_sequences`, and
- `R = complete_column_basis.nonzero_minor.coordinate_rows`

from the exact G-0140 Stage-C receipt.  Require `|S| = |R| = 349`, the stored
rank and complete-spanning certificate, base/full ranks 221/349, increments
exactly `[1] * 128`, growing Pool indices exactly `0..127`, and no dependent
Pool indices.

Reconstruct only `B = M[:,S]` using the audited inherited G-0135 column loader
for the first 412 entries and the complete committed Stage-B matrix for the
last 128 entries.  Require these frozen digests before solving:

- `S` as unsigned-64 little-endian:
  `c9ec5dbb017e2f735a115ca2eb757adf4d93f072a287f08286c2776b29ec08b3`
- row-major `B` as signed-128 little-endian:
  `7451a36e42c479819b6f9ae28ec8c2f7b23360ddc5203b17cf9e3417d1ac9d10`
- row-major square `B[R,:]` as signed-128 little-endian:
  `f06bf820562a96575274bd8358b7ca0eef695e3e991034072deecf97823d3606`
- `b` as signed-128 little-endian:
  `a30ec0a4ff135350f217363831c6ffd2ee0a44f74b4d14549aa3b88da3967874`

Solve exactly over Q, once and only once,

`B[R,:] x = b[R]`.

The order of `S` and `R` is immutable.  No alternative basis, nullspace
adjustment, optimization, column generation, pricing, rank discovery,
coefficient bound, or residual-aware retry is permitted inside G-0164.

## Finite member controls and output

The solver must:

1. replay `B x = b` exactly on all 540 rows;
2. independently convert every FLINT rational through canonical numerator and
   denominator integers;
3. clear denominators and divide the joint coefficient/scale gcd primitively;
4. replay `sum_j c_j B[i,j] = scale * b_i` with arbitrary-precision integers
   on all 540 rows;
5. require positive scale, 349 coordinates, ordered support projected from
   `S`, and joint gcd one;
6. add one to the first nonzero integer coefficient and require a nonzero
   finite residual;
7. reject reuse of the old G-0135 target scale; and
8. rehash every bound input at the end before exclusive output publication.

The finite receipt schema/result are frozen as:

- schema `max11-g0164-all128-direct-basis-member-v1`
- result `ALL128_DIRECT_BASIS_EXACT_Q_MEMBER`

It must record `rank = augmented_rank = 349`, `S`, `R`, all 349 canonical
rational coordinates, primitive integer coordinates and scale, ordered nonzero
terms, both finite replay transcripts/digests, the mutation control, complete
input snapshot, resource use, and the explicit claim boundary that only the
540-row finite system has been solved.

Any solve failure, rank/augmented-rank mismatch, digest mismatch, nonzero finite
replay, mutation-control failure, input drift, or output collision is
`INVALID_NO_SCIENTIFIC_RESULT`.  It is not evidence of nonmembership because
it would contradict already-certified inputs or the implementation contract.

## Complete global replay

Only after the finite member receipt exists may a separately frozen and
outcome-blind source-audited producer compute its complete exact
ordered-chamber normal form.  It must reuse the audited G-0140 Rust normal-form
engine without semantic changes, validate all 349 member coordinates and all
540 finite rows independently, enumerate the full labelled-permutation census,
subtract the denominator-scaled MAX11 target exactly, and rehash inputs at the
end.

The only valid scientific branches are:

1. `GLOBAL_EXACT_ZERO`: complete exact zero for this explicit member.  This is
   eligible for independent clean-room reproduction, network compilation,
   novelty/statement review, and Lean formalization.
2. `EXACT_RESIDUAL_CONTINUE`: a complete exact nonzero residual for this one
   deterministic member.  Record the full censuses/digests and a deterministic
   residual prefix, then stop G-0164.  Do not silently optimize in its affine
   nullspace or choose another member.

Source, custody, census, arithmetic, mutation, resource, or end-rehash failures
are `INVALID_NO_SCIENTIFIC_RESULT` and have no mathematical interpretation.

## Audit and custody gates

- Commit this preregistration before writing or executing the scientific
  solver.
- Freeze and independently audit the exact solver source before scientific
  execution.  Source audit is outcome-blind and may use only synthetic
  fixtures plus bound source/runtime identities; it may not inspect or create
  the finite member output.
- Bind exact G-0140 A/B/C bytes, G-0135 loader/core/cache, runtime locks, this
  preregistration, solver, solver audit, replay sources/binary, replay audit,
  and their Git ancestry in one-shot manifests before their respective runs.
- Refuse overwrite and rehash every input at the end.
- A claimed global zero requires a fresh result-aware clean-room audit and an
  exact statement-match review before theorem promotion.

## Stopping rule

G-0164 stops after its first complete global replay.  Global zero advances to
clean-room verification.  Nonzero residual updates the probability of this
deterministic basis choice only and motivates a separately preregistered
nullspace-optimization or structurally diversified-pool study.  It cannot be
reported as a lower bound, frozen-family nonmembership, unrestricted
nonrepresentability, minimality, an all-n theorem, or a Lean theorem.
