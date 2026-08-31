# G-0140 preregistration — rank-aware exact CEGIS after G-0135

## Decision target

This study asks whether a deterministic, rank-aware continuation of the frozen
163,740-column degree-five family yields either:

1. a rational family member whose complete ordered-chamber normal form is
   exactly MAX11; or
2. an exact rational separator for the frozen family.

The study starts from the committed G-0135 412-row member and its committed
nonzero global residual. It does not test completeness of the family, minimal
width, an unrestricted lower bound, or an all-`n` statement.

## Outcome-aware starting facts

These facts were observed before this protocol was written and are disclosed:

- G-0135 Stage-C result:
  `artifacts/math/G-0135/full_family_master_result_v3.json`, SHA-256
  `ef1cbdf3abfd32326c35e511057a3450b4942ae9aa901ead8e8b86133c564db8`;
  result `FULL_FAMILY_412ROW_EXACT_Q_MEMBER`, 204 target-sufficient selected
  columns, and 135 nonzero terms. Its reported rank 204 is **not** a certified
  rank of the complete `412 x 163740` family matrix: the column-generation loop
  stopped when the target entered the selected span.
- G-0135 Stage-D result:
  `artifacts/math/G-0135/new_member_global_replay_v1.json`, SHA-256
  `d576e142f213cd1f6b125246d22a766894ada4ade23de575ac5b14c9fd18f875`;
  result `EXACT_RESIDUAL_BATCH_CONTINUE`, 5,388,768,000 labelled
  permutations, aggregate hinge support 147,062, and 146,950 nonzero hinge
  directions.
- Its signed-lexicographically first nonzero hinge direction is
  `[0,0,0,0,0,0,1,-2,-2,1,2]`, with the exact coefficient recorded in the
  Stage-D result.
- All 100 accumulated hinge directions and all 11 linear residuals are zero.
- The first 32 residual directions and their two stream digests are already
  public in Stage D. Their exact rank contribution to the 412-row system has
  not been measured at preregistration time.
- Earlier deterministic batches required 20 and 28 additional selected columns
  before their finite targets entered the selected spans. Those numbers do not
  establish full-matrix row-rank gains. They motivate measuring the complete
  matrix honestly; they are not evidence of convergence to zero.

The G-0139 result audit is a mandatory admission gate. No G-0140 scientific
stage may run unless its committed receipt independently returns PASS for the
G-0135 Stage-D residual, censuses, first nonzero direction and coefficient,
selection digests, and custody. G-0139 is same-lineage T1 evidence and must not
be described as independent external replication.

## Frozen constants and order

- `N = 11`.
- Frozen family records: 163,740, in canonical sequence order.
- Existing rows: 412, in the exact G-0135 order.
- Existing target-sufficient selected columns: 204. The complete 412-row matrix
  rank is unknown at preregistration time.
- Existing accumulated hinge directions: 100, in the G-0135 Stage-D order.
- Residual pool size: `P = 128`.
- Maximum newly admitted rows: `K = 32`.
- Every direction order is ordinary signed-`i8` tuple lexicographic order.
- Every appended hinge target is the exact integer zero.

No residual magnitude, sign, apparent sparsity, modular rank, solver support,
or post-result preference may reorder the pool.

## Stage A — exact replay and deterministic Pool128

Recompute the complete arbitrary-precision ordered-chamber normal form of the
135-term G-0135 Stage-C member. The implementation may reuse the audited
normal-form specification but must not import the G-0135 Stage-D output as its
computed residual.

Before emitting a new pool, require exact agreement with every G-0135 Stage-D
anchor: member identity, term and labelled-permutation censuses, all 100
accumulated zeros, all 11 linear zeros, aggregate/nonzero support counts, full
aggregate and nonzero-stream digests, first nonzero hinge, and the already
published first-32 direction and coefficient digests. Any disagreement is
`INVALID_NO_SCIENTIFIC_RESULT`.

From the full exact residual map, remove zero coefficients and all 100
accumulated directions, sort by signed tuple order, and take the first 128.
Each pool item is the primitive active direction and its canonical nonzero
signed-decimal coefficient. Fewer than 128 eligible residuals is a protocol
failure, not permission to change `P` after inspection. Emit independent
direction-byte and coefficient-decimal-LF digests.

## Stage B — exact all-column Pool128 pricing

For every one of the 128 directions, compute its exact signed-`i64` coordinate
on every canonical family record, producing a `128 x 163740` direction-major
matrix. Reuse of a record's increment table across directions is allowed.

For every priced row, its arbitrary-precision dot product with the 135-term
G-0135 member must equal Stage A's exact residual coefficient. Record all row
digests, nonzero counts, signed extrema, the complete matrix digest, record and
direction order, and end-of-run input rehashes. No row may be omitted based on
rank or price.

## Stage C — complete-matrix certification, exact rank admission, and solve

Let `A c = b` be the frozen G-0135 412-row system, and let `H` be the ordered
128-row Stage-B block. First form the logical integer matrix

`M = [A; H]`, of shape `540 x 163740`.

The implementation may stream immutable blocks instead of materializing `M`,
but all rank claims refer to this complete matrix, not the G-0135 selected-
column minor.

### C1. Complete exact column basis of M

Construct a set `S` of canonical column indices and certify that `M[:,S]` is an
exact `Q`-basis for the complete column space of `M`:

1. Frozen modular primes may propose an ordered pivot set. Their union is
   sorted and deduplicated; modular arithmetic never supplies a negative or
   terminal decision.
2. Reduce the proposed columns to an exact independent `Q` basis using the
   frozen exact RREF/pivot convention.
3. Compute an exact basis `L` of the left annihilator of `M[:,S]`.
4. Scan all 163,740 columns in canonical sequence order. If any annihilator
   has nonzero exact price, append the lexicographically first violating column
   to `S`, require an exact unit rank increase, recompute `L`, and rescan from
   column zero.
5. Terminate only when every row of `L` has exact zero price on every family
   column. Then `S` spans every column of `M` over `Q`. If the exact rank is
   540, the empty left annihilator plus a nonzero exact/modular 540-column minor
   is already a complete basis certificate.

Every completion pass records the exact rank, chosen column, annihilator
dimension, full scan census, and decimal-LF price digest. An omitted final
column and a false modular-zero fixture must be rejected.

### C2. Exact prefix-rank transcript and row selection

Because `S` spans the complete column space of `M`, restriction to `S`
preserves the exact row rank of every row prefix. Compute over `Q`

`r_t = rank([A; H_0; ...; H_{t-1}][:,S])` for `t = 0,...,128`.

Require every increment `r_(t+1)-r_t` to be zero or one. Select, in pool order,
the first 32 indices whose increment is one. A zero increment is an exact
full-family row dependence, not a modular guess. Emit the complete 129-rank
transcript, selected and skipped indices, exact pivot rows/columns, and a
replayable nonzero-minor certificate.

If fewer than 32 increments occur, emit all rank-growing rows and the bounded
outcome `FIXED_POOL128_EXACT_RANK_GAIN_LT32`; do not expand the pool inside
G-0140. Otherwise emit `EXACT_RANK32_SELECTED`, with final selected-system rank
exactly `r_0 + 32`.

For every skipped row, derive its exact dependence on the preceding accepted
system. If that dependence implies a nonzero target while the appended hinge
target is zero, derive a primitive exact left separator, replay it against all
163,740 frozen columns, require nonzero target pairing, and terminate as
frozen-family nonmembership. Compatible dependencies must imply target zero.

### C3. Reopened exact full-family solve

If admission remains consistent, append only the admitted rows, preserve all
prior rows, and solve over `Q` while reopening all 163,740 columns in canonical
order. The complete column basis `S` may warm-start the solve, but the target
decision, rational member or separator must still be replayed on every selected
row and against the complete frozen family. At membership, replay every row
over `Q`, clear denominators primitively, and replay the integer identity.

Modular elimination may propose work order or certify a positive nonzero
integer minor. It may not select or discard a direction, certify completeness,
declare dependence, decide membership/nonmembership, or support a terminal
outcome. On every modular/exact mismatch, exact arithmetic wins and the
mismatch is recorded.

No row deletion beyond exact compatible Pool128 dependencies, support freeze,
zero-price-column deletion, modular terminal decision, preferred-sparsity
search, or reuse of the prior target scale is permitted.

## Stage D — complete global replay

If and only if Stage C returns a member, compute its complete exact ordered-
chamber normal form. The only scientific branches are exact global zero or an
exact nonzero residual. A residual may report the next deterministic prefix
for a separately preregistered study, but G-0140 must not silently continue.

## Terminal outcomes

Exactly one scientific outcome may be published:

1. `GLOBAL_EXACT_ZERO`: a complete exact identity for a concrete frozen-family
   member. This triggers clean-room reproduction, network compilation,
   statement-match review, and Lean formalization.
2. `FROZEN_163740_FAMILY_EXACT_Q_NONMEMBER`: a primitive exact separator,
   discovered either during rank admission or the reopened solve, that
   annihilates all 163,740 frozen columns and pairs nontrivially with the
   target.
3. `EXACT_RESIDUAL_CONTINUE`: an exact expanded-row member whose complete
   global normal form remains nonzero.

Audit, custody, source, resource, census, or mutation failures are
`INVALID_NO_SCIENTIFIC_RESULT` and have no mathematical interpretation.

## Mandatory controls

- Positive fixtures for normal-form pricing, transpose/order, exact rank
  growth, compatible dependency, incompatible dependency/separator, rational
  solve, and denominator clearing.
- Reject coefficient-plus-one, omitted term/orbit/record, row reordering,
  direction reordering, residual-decimal mutation, target-scale carryover,
  truncated record census, false modular dependency, and separator coordinate
  mutation.
- Bind preregistration, all transitive inputs, sources, executables, source-
  audit receipts, G-0139, stage outputs, runtime/toolchain, and Git commits in a
  one-shot manifest committed before scientific execution.
- Refuse output overwrite and rehash every bound input at the end of each
  stage.
- Outcome-blind source audit precedes execution; a terminal result receives a
  separate clean-room result audit.

## Claim boundary and stopping rule

An exact zero proves only the explicit concrete frozen-family identity and the
network compiled from it. A separator excludes only the frozen 163,740-column
family under the accumulated exact rows. A residual refutes only the returned
member. None alone proves family completeness, unrestricted two-hidden-layer
impossibility, minimal width, or an all-`n` theorem.

Lean work starts only after `GLOBAL_EXACT_ZERO` and must state the concrete
network under the repository's actual semantics. A generic compiler theorem
conditional on an unproved identity does not complete the research target.
