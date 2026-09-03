# relu-depth-frontier-research-kbg — weighted-lift recursion test at 9 → 10 (and 10 → 11)

## Question

Bead `ksi` showed that the *lift family*

```
L(cert_{n-1}) = { (A_t + e, B_t + f) : t a term of the pinned degree-four
                  certificate at n-1;  e, f distinct non-loop edges on [n] }
```

spans `MAX_n` on the sorted cone at both 9 → 10 and 10 → 11.  Spanning is cheap;
the interesting question is whether the *coefficients* can be inherited.  This
bead tests the recursion-shaped ansatz

* **H1 (factorized).**  The coefficient of the raw extension `(t, e, f)` is
  `c_t * w_tau`, where `c_t` is the pinned upstream coefficient of term `t` at
  `n-1` and `tau` is the *attachment type* of `(e, f)` relative to `(A_t, B_t)`.
  Unknowns: one weight per attachment type.
* **H2 (per-parent).**  The coefficient is `c_t * w_{t,tau}`, i.e. it may depend
  freely on the pair (parent term, attachment type).  Unknowns: one per realized
  `(t, tau)`.

Both reduce to a membership question.  With `col(W)` the exact integer column of
the symmetrized atom for the signed graph `W = B - A` after cancelling common
edge occurrences, the class sum of a type `tau` is

```
S_tau = sum over raw extensions (t, e, f) of type tau of  c_t * col(W(A_t+e, B_t+f)),
```

accumulated by signed-`W` orbit with multiplicity, and the question is whether
the target `b` (`MAX_n` on the sorted cone: 1 on the last linear row, 0 on every
other row, the convention of `tools/exactlift/exactlift.py`) lies in
`span{S_tau}`.

## Outcome

**Every hypothesis tested fails.**  `H1` is `NON_MEMBER` at all eight
taxonomies at 9 → 10 and again, with numerically identical ranks, at 10 → 11.
`H2` is `NON_MEMBER` at the base taxonomy at 9 → 10.  Every verdict is exact
over `Q`, carried by an exact rational dual; nothing here is modular-only.

The failures are not near misses in the rank sense — `rank [S | b] = rank S + 1`
in every single case — and they are not caused by the family being too small,
since bead ksi's rank-17,127 result says this same family spans the target when
its columns are free.

The planted negative (collapse every attachment type into one class) is
`NON_MEMBER`, as it had to be.  Because `H1` never returned `MEMBER`, there are
no weights `w_tau` to report, and the follow-up questions the bead attached to a
`MEMBER` outcome (the minimal passing coarsening, a closed form in `n`) do not
arise.

## Attachment-type taxonomy

Fix a parent term with pair `(A_t, B_t)`, both multisets of four non-loop edges
on `[n-1]`.  Write `V_A = V(A_t)`, `V_B = V(B_t)`, `V = V_A u V_B`.  The
extension appends `e` to the `A` branch and `f` to the `B` branch, with `e != f`
non-loop edges on `[n]`.  Every key below is invariant under `S_n` relabelings
that fix the parent, which is what makes a class sum well defined.

`T3` is the finest key used and every other level is a function of it, so all of
them are coarsenings of one partition and their class sums are sums of the `T3`
class sums.  `T3` records thirteen incidence features:

| field | values | meaning |
|---|---|---|
| `\|e ∩ V\|`, `\|f ∩ V\|` | 0,1,2 | how many endpoints of each new edge already lie in the parent's support |
| `\|e ∩ f\|` | 0,1 | whether the two new edges share a vertex (`e = f` is excluded by construction) |
| `e ∈ A_t`, `f ∈ B_t` | bool | whether the new edge repeats an occurrence of *its own* branch |
| `e ∈ B_t`, `f ∈ A_t` | bool | whether it repeats an occurrence of the *opposite* branch, i.e. cancels inside `W` |
| `\|e ∩ V_A\|`, `\|e ∩ V_B\|`, `\|f ∩ V_A\|`, `\|f ∩ V_B\|` | 0,1,2 | which branch's own vertex set each endpoint touches |
| shared vertex in `V_A`, in `V_B` | bool | when `e` and `f` meet, whether the meeting point touches each branch |

The coarser levels are

| level | key | classes (both rungs) |
|---|---|---:|
| `T3` | all thirteen fields | 455 |
| `T2` | `(\|e ∩ V\|, \|f ∩ V\|, \|e ∩ f\|, e ∈ A_t, f ∈ B_t, e ∈ B_t, f ∈ A_t)` | 63 |
| `T2b` | `T1` plus branch-blind edge roles `(e ∈ A_t ∪ B_t, f ∈ A_t ∪ B_t)` | 28 |
| `T1` | `(\|e ∩ V\|, \|f ∩ V\|, \|e ∩ f\|)` — the base taxonomy | 16 |
| `T1s` | `T1` made unordered in `(e, f)` | 11 |
| `Tv` | `(#fresh vertices used by e ∪ f, \|e ∩ f\|)` | 9 |
| `Tn` | `#fresh vertices used by e ∪ f` | 5 |
| `T0` | one class — **the planted negative** | 1 |

The justification for `T1` as the base is that the sorted-cone column depends
only on `W`, and `W' = W_t + f - e`; the three `T1` fields are exactly the data
that decides how the two new edge occurrences sit against the already-active
vertex set and against each other.  `T2`/`T2b` add the multiset information that
decides whether an added occurrence cancels or reinforces inside `W`; `T3` adds
which branch each endpoint belongs to.  `Tv`, `Tn`, `T1s` are the coarser
directions.  The realized class counts are identical at 9 → 10 and 10 → 11,
which is what makes the two rungs directly comparable.

Two of the eighteen combinatorially conceivable `T1` keys are unrealizable and
do not appear: `(0,2,1)` and `(2,0,1)`, since a shared vertex of `e` and `f`
would have to lie in `V` and in the complement of `V` at once.

## Data provenance

| file | role | SHA-256 |
|---|---|---|
| `subjects/max-relu-known/certificates/certificate_9_4.json` | 337 pinned degree-four MAX9 terms and coefficients | `4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88` |
| `subjects/max-relu-known/certificates/certificate_10_4.json` | 402 pinned degree-four MAX10 terms and coefficients | `10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4` |
| `artifacts/math/n11-lift-test/n9-lift-n10-family-universe.json.gz` | bead-ksi 9 → 10 lift family, 114,814 signed-`W` orbits | `c22d925e66ab83ae31eb873346ef3709a17753e3b0c36fc03e2d3b12d2123cb3` |
| `artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz` | G-0027 degree-five universe at n=11, 754,017 records | `8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8` |
| `artifacts/math/n11-lift-test/max10-lift-g0027-order.json` | the 163,740 G-0027 records the 10 → 11 family lands on | (bead ksi) |

Columns are generated by `tools/colgen/target/release/max11-colgen emit-universe`
in its exact integer mode, with `n` and the branch degree read from the universe
file.  The published bead-ksi builder deduplicated orbits, so the raw-extension
→ orbit map is **recomputed here with multiplicities** by
`build_lift_taxonomy.py`; its census reproduces the published denominators
exactly (337 × 1,980 = 667,260 raw extensions onto 114,814 orbits at 9 → 10;
402 × 2,970 = 1,193,940 onto 163,740 at 10 → 11).

## Method, and what is exact

* Coefficients are cleared to integers by the global denominator
  `D = lcm` of the 337 (resp. 402) coefficient denominators — `21,772,800` at
  9 → 10 and `304,819,200` at 10 → 11.  Scaling every class sum by the same `D`
  does not change the span, so all arithmetic below is over `Z`.
* Class sums are accumulated by **streaming** colgen's exact column output in
  chunks, never materializing the matrix.  Accumulation is plain `int64`,
  guarded by the a-priori bound `(sum of |class weights|) × (max |column
  coefficient|)`, which is checked against a 62-bit headroom and recorded in
  `class_sums_*.json`.  At 9 → 10 that bound is `9.3e14` against a `4.6e18`
  headroom, so every stored entry is an exact integer.
* Ranks are modular at `p = 1,000,003` and `p = 1,000,033`, with entries reduced
  as integers *before* the float64 streaming echelon step (the entries exceed
  `2**53`, so the reduction order matters).  A modular rank is a lower bound for
  the rational rank.
* **Verdicts are exact.**  `NON_MEMBER` carries an exact rational dual `y`
  supported on `rank + 1` rows with `y^T S_c = 0` on every class and `y . b != 0`,
  both checked by `class_sum_test.exact_product_matches`, i.e. modulo a set of
  primes whose product exceeds twice a proved bound on the residual.  A dual
  supported on a subset of rows extends by zero, so a `NON_MEMBER` obtained on a
  row sketch is exact for the full row space as well.
* `H1` is decided on the **complete** row set of the family.  `H2` has too many
  unknowns to hold a full-row matrix, so it is decided on a deterministic
  `splitmix64` hash-selected row sketch together with all linear rows.  This
  keeps `NON_MEMBER` exact; it would only weaken a `MEMBER`, which did not occur.

## Results — 9 → 10

Row space: 87,658 rows (87,648 primitive hinge directions + 10 linear).  The
family has 114,814 orbits, of which 114,470 carry a nonzero class weight.

| hypothesis / taxonomy | unknowns | rows | rank S (p=1,000,003) | rank [S\|b] | rank S (p=1,000,033) | rank [S\|b] | verdict | certificate |
|---|---:|---:|---:|---:|---:|---:|---|---|
| H1/T3 | 455 | 87,658 | 451 | 452 | 451 | 452 | NON_MEMBER | dual on 452 rows |
| H1/T2 | 63 | 87,658 | 63 | 64 | 63 | 64 | NON_MEMBER | dual on 64 rows |
| H1/T2b | 28 | 87,658 | 28 | 29 | 28 | 29 | NON_MEMBER | dual on 29 rows |
| H1/T1 | 16 | 87,658 | 16 | 17 | 16 | 17 | NON_MEMBER | dual on 17 rows |
| H1/T1s | 11 | 87,658 | 11 | 12 | 11 | 12 | NON_MEMBER | dual on 12 rows |
| H1/Tv | 9 | 87,658 | 9 | 10 | 9 | 10 | NON_MEMBER | dual on 10 rows |
| H1/Tn | 5 | 87,658 | 5 | 6 | 5 | 6 | NON_MEMBER | dual on 6 rows |
| H1/T0 | 1 | 87,658 | 1 | 2 | 1 | 2 | NON_MEMBER | dual on 2 rows |
| H2/T1 (sketch rows) | 2,890 | 5,420 | 2,788 | 2,789 | 2,788 | 2,789 | NON_MEMBER | dual on 2789 rows |

Every cell agrees at both primes.  In every `H1` row the class sums are
themselves independent (`rank S` equals the class count) except at `T3`, where
455 class sums have rank 451, i.e. the finest attachment taxonomy carries four
exact linear dependencies; and in every row `rank [S | b] = rank S + 1`, so the
target is outside the span by exactly one dimension.  For comparison, the same
114,814-column family spans the target with rank 17,127 when its columns are
free (bead ksi), so the whole loss is caused by tying coefficients to the
attachment type.

`H2/T1` puts one free unknown on each of the 2,890 realized (parent term,
attachment type) pairs.  Its rank is 2,788, well below the 5,420 sketch rows, so
the sketch is not what limits it, and its exact dual extends by zero to the full
row space: **`H2/T1` is an exact `NON_MEMBER` for the complete row space, not a
sketch artifact.**

`H2/T2b` (6,419 unknowns) was started and then abandoned: with 6,419 classes
against 5,420 sketch rows the matrix has more columns than rows, its rank
saturated the sketch, and the resulting `MEMBER`-on-sketch verdict carries no
information about the full row space while its exact certificate was still
running after an hour.  It is not reported.  Nothing follows from its absence:
`H2/T2b` refines `H2/T1`, so it is a strictly weaker hypothesis and its verdict
is not implied by the `H2/T1` failure.

## Results — 10 → 11

Row space: 243,122 rows (243,111 primitive hinge directions + 11 linear).  The
family has 163,740 orbits, of which 163,125 carry a nonzero class weight, and
the parents are the 402 pinned degree-four MAX10 terms.

The bead asked for this rung modulo two primes.  It was in fact run **exactly**:
the a-priori accumulator bound is `3.58e16` for `H1` and `3.97e16` for `H2`
against a `4.6e18` int64 headroom, with `max |column coefficient| = 55,108,800`,
so the class sums are exact integers and the reported ranks and certificates are
the same kind of object as at 9 → 10.

| hypothesis / taxonomy | unknowns | rows | rank S (p=1,000,003) | rank [S\|b] | rank S (p=1,000,033) | rank [S\|b] | verdict | certificate |
|---|---:|---:|---:|---:|---:|---:|---|---|
| H1/T3 | 455 | 243,122 | 451 | 452 | 451 | 452 | NON_MEMBER | dual on 452 rows |
| H1/T2 | 63 | 243,122 | 63 | 64 | 63 | 64 | NON_MEMBER | dual on 64 rows |
| H1/T2b | 28 | 243,122 | 28 | 29 | 28 | 29 | NON_MEMBER | dual on 29 rows |
| H1/T1 | 16 | 243,122 | 16 | 17 | 16 | 17 | NON_MEMBER | dual on 17 rows |
| H1/T1s | 11 | 243,122 | 11 | 12 | 11 | 12 | NON_MEMBER | dual on 12 rows |
| H1/Tv | 9 | 243,122 | 9 | 10 | 9 | 10 | NON_MEMBER | dual on 10 rows |
| H1/Tn | 5 | 243,122 | 5 | 6 | 5 | 6 | NON_MEMBER | dual on 6 rows |
| H1/T0 | 1 | 243,122 | 1 | 2 | 1 | 2 | NON_MEMBER | dual on 2 rows |

**The 10 → 11 numbers are identical to 9 → 10 at every level**: the same class
counts, the same ranks, the same `rank [S | b] = rank S + 1`, and the same four
linear dependencies among the 455 `T3` class sums.  Whatever the obstruction is,
it is not an accident of one arity.

`H2` at 10 → 11 (one free unknown per realized (parent term, attachment type)
pair, decided on the 30,620-row sketch) was still running when this file was
written and is not reported here; the `H1` verdicts above stand on their own and
do not depend on it.

## Controls

| control | outcome | file |
|---|---|---|
| census reproduction | the recomputed raw-extension → orbit map hits the published denominators exactly (667,260 raw extensions, 114,814 orbits at 9 → 10; 1,193,940 and 163,740 at 10 → 11) and every raw extension stays inside the family | `lift_taxonomy_map_*.json` |
| independent replay | three `T3` class sums were re-emitted by a fresh `colgen` invocation and rebuilt from scratch; each agreed with the streamed accumulator on **all 87,658 coordinates**, zeros included, and a planted one-unit mutation was rejected | `replay_control_9to10.json` |
| dual non-degeneracy | the rebuilt `T1` dual (17 rows) pairs nonzero with all 4,101 sampled family columns and the `T3` dual (452 rows) with 4,037 of 4,101 — a dual orthogonal to the whole family would contradict bead ksi's spanning result and would indicate a bug | `dual_control_9to10.json` |
| planted negative | `T0`, one class for every attachment type, is `NON_MEMBER` | table above |
| exactness bound | accumulated entries are bounded a priori by `9.29e14` (`H1`) and `1.03e15` (`H2`) against a `4.6e18` int64 headroom, with `max |column coefficient| = 5,501,952` | `class_sums_9to10.json` |
| two primes | every rank cell agrees at `p = 1,000,003` and `p = 1,000,033` | table above |

## Interpretation

Inheriting the parent coefficient and paying only an attachment-type price does
not produce `MAX_10`: at every one of eight taxonomies, from a single class up
to 455 classes distinguishing thirteen incidence features, the target sits
exactly one dimension outside the span, and letting the price also depend freely
on the parent term does not help.  The obstruction is not a shortage of columns,
because bead ksi's rank-17,127 result says this same family spans the target
when its 114,814 columns are free, and the dual control confirms that the
separating functionals still pair nontrivially with individual family columns.
It is also not merely a shortage of classes: the `H2` failure at 9 → 10 uses
2,890 free unknowns, within a factor of two of the `C11` coarsening that *did*
pass in `artifacts/math/class-sum-n9-n10`, which suggests the missing
information is qualitative — that earlier work found membership returns only for
class functions that see the isomorphism type of the unsigned union graph, and
no attachment-type key of the parent-plus-two-edges kind sees that.  The practical
consequence for the all-`n` construction track is that a uniform recursion whose
coefficient factorizes through a bounded local attachment taxonomy is ruled out
at these two rungs, and any surviving inductive scheme has to let the new
coefficient depend on global isomorphism data of the extended signed graph.
None of this bears on whether `MAX_n` has a degree-five certificate at all; it
bears only on the shape such a certificate can have.

## Claim boundary / no-claim

These are results for two named finite families only: the bead-ksi lift of the
pinned MAX9 degree-four certificate into the n=10 degree-five loopless
signed-`W` quotient, and the corresponding lift of the pinned MAX10 certificate
into G-0027 at n=11.  A `MEMBER` verdict here would have been the existence of a
recursion-shaped certificate *at that rung*, not a theorem; a `NON_MEMBER`
verdict rules out that shape *at that rung* for the stated taxonomies and does
not rule out other ansatzes, other taxonomies, other degrees, or membership of
the unrestricted family.  Nothing here is an unrestricted two-hidden-layer depth
lower bound, and nothing here contradicts or establishes the existence of a
degree-five MAX11 certificate.

## Files

| file | contents |
|---|---|
| `build_lift_taxonomy.py` | 9 → 10 raw-extension → orbit map with multiplicities and attachment types |
| `build_lift_taxonomy_10to11.py` | the same one rung up, indexed by position in the frozen bead-ksi order file |
| `accumulate_class_sums.py` | streaming exact class-sum accumulation at 9 → 10 |
| `accumulate_class_sums_10to11.py` | streaming class-sum accumulation at 10 → 11 |
| `test_lift_recursion.py` | modular ranks and exact `MEMBER` / `NON_MEMBER` decisions |
| `replay_control.py` | independent re-emission and rebuild of chosen class sums |
| `dual_control.py` | rebuilds the `NON_MEMBER` duals and pairs them with individual family columns |
| `render_tables.py` | renders the verdict tables in this file from the JSON outputs |
| `lift_taxonomy_map_*.json` | census, class counts, and taxonomy labels |
| `class_sums_*.json` | row counts, exactness bounds, row-key hash |
| `lift_recursion_*.json` | ranks, verdicts, certificates |
| `replay_control_9to10.json`, `dual_control_9to10.json` | control reports |

## Reproduction

```bash
.venv/bin/python artifacts/math/lift-recursion/build_lift_taxonomy.py --workers 6
# then, in a loop over --start/--limit chunks of the family universe:
#   tools/colgen/target/release/max11-colgen emit-universe \
#     --universe artifacts/math/n11-lift-test/n9-lift-n10-family-universe.json.gz \
#     --threads 7 --start S --limit 4000 --format binary --output chunks/cS.bin && touch chunks/cS.done
.venv/bin/python artifacts/math/lift-recursion/accumulate_class_sums.py --chunks chunks
.venv/bin/python artifacts/math/lift-recursion/test_lift_recursion.py --h2-levels T1
.venv/bin/python artifacts/math/lift-recursion/replay_control.py
.venv/bin/python artifacts/math/lift-recursion/dual_control.py
```

The intermediate `class_sums_*.npz` files are **not committed** (74 MB at 9 → 10,
363 MB at 10 → 11); they are regenerated by the accumulator above, and the
committed `class_sums_*.json` records their row-key SHA-256 and exactness
bounds.  The 10 → 11 rung was run on the authorized remote box at 16 colgen
threads; its column stream is 163,740 exact columns totalling roughly 150 GB,
consumed and deleted chunk by chunk.
