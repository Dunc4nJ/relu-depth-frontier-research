# relu-depth-frontier-research-2q7 — class-sum span test at n = 9 and n = 10

## Question

The saved loopless systems store one integer column per `S_n x` side-swap orbit of a
loop-free pair `(A, B)`.  A column is `(lin, h)`: a linear part indexed by the `n`
sorted-cone coordinates and a sparse hinge part indexed by primitive ambiguous directions.
`MAX_n` on the sorted cone is the target `b` that is `1` on the last linear row and `0` on
every other row (the convention of `tools/exactlift/exactlift.py`).  Membership of `b` in
the span of the individual columns is already known at both arities.

This experiment replaces the columns by **class sums**

```
S_c = sum_{W in class c} col_W        W = B - A after cancelling the common edges
```

and asks whether `b` is still in the span.  A MEMBER verdict at a coarse `phi` means a
certificate exists whose coefficients depend only on `phi(W)` — the shape a uniform all-`n`
construction would have.  A NON_MEMBER verdict rules that shape out at that `n`.

## Outcome

Every rung of the requested ladder fails at both arities, and so does C9, the common
refinement of its two finest rungs.  Membership returns only for coarsenings that also see
the isomorphism type of the unsigned union graph.  The coarsest passing coarsening is C11
(4,605 classes at n=9, 5,363 at n=10, against 6,197 and 7,203 signed-graph orbits); the
finest failing one is C9 (1,501 and 1,706 classes).  C9 and C11 are incomparable in the
refinement order, so the pass/fail boundary is not a single cut through the ladder.

Every verdict in this file is exact.  MEMBER carries an exact rational solution verified on
every row; NON_MEMBER carries an exact rational dual vector.  Ranks are modular, as stated
per row of the tables below.

## Data provenance

| file | role | SHA-256 |
|---|---|---|
| `handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz` | n=9 saved system, 10,976 columns | `729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991` |
| `handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz` | n=10 saved system, 12,248 columns | `bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18` |
| `artifacts/math/exact-witness-n9-n10/recovered_n9_witness.json` | exact n=9 witness, used for the C0 and C0w certificates | `fa7f80281c9795e5a755cb490d5d9e4ae862ef43493c89ff1f7270b281053b13` |
| `artifacts/math/exact-witness-n9-n10/recovered_n10_witness.json` | exact n=10 witness, used for the C0 and C0w certificates | `bc7a60476c4d06e72d2da0013c1a156ec69e81b6b7fb378536e311cfb4fe88f2` |

Both system hashes are the ones recorded in `artifacts/math/exact-witness-n9-n10/RESULT.md`.
Only template pairs `(A, B)` are stored, so `W` is recomputed here by multiset cancellation
of the common edges.  The loader fails closed if a record is unbalanced, has a loop, or has
a linear part of the wrong length; none did.

Structural facts recomputed here and used below:

| | n = 9 | n = 10 |
|---|---:|---:|
| stored records | 10,976 | 12,248 |
| rows (hinge + linear) | 6,335 (6,326 + 9) | 16,719 (16,709 + 10) |
| distinct `S_n` orbits of `W` | 6,197 | 7,203 |
| distinct columns | 6,196 | 7,202 |
| carrier records (`W` empty, `A = B`) | 11 | 11 |
| records with the same `W` have identical columns | yes | yes |

The column therefore depends on `W` alone, which is what makes the class-sum question well
posed.  The one-column gap (6,197 orbits versus 6,196 columns, and 7,203 versus 7,202) is a
single accidental coincidence between two non-isomorphic signed graphs, not a failure of
that dependence.

## Coarsenings

`positive` is the graph `B \ A`, `negative` is `A \ B`, the *union* graph is their unsigned
union, a vertex is *active* if either covers it, and *shared* counts the vertices both
cover.  An isomorphism type is a nauty certificate of the graph with its isolated vertices
dropped, so equal labels mean isomorphic graphs.

The saved system keeps one record per `S_n x` side-swap orbit of the **unordered** pair
`{A, B}`, so `W` is defined only up to the flip `W -> -W`, which exchanges the positive and
negative parts.  Every key below is made invariant under that flip by taking the smaller of
the two orientations.  Without this, a record's class would depend on whichever orientation
nauty happened to store and `phi` would not be a function of the atom at all; the ordered
forms of C1, C2, C3, C4 and C5 requested in the task are exactly these flip-canonical keys.

| key | definition | classes n=9 | classes n=10 |
|---|---|---:|---:|
| C0 | identity on stored records (control) | 10,976 | 12,248 |
| C0w | identity on the `S_n` isomorphism type of `W` | 6,197 | 7,203 |
| C10 | C9 together with the isomorphism type of the unsigned union graph | 4,985 | 5,790 |
| C11 | C1 together with the isomorphism type of the unsigned union graph | 4,605 | 5,363 |
| C9 | common refinement of C1 and C3 | 1,501 | 1,706 |
| C3 | vertex-type multiset `{(d_plus(v), d_minus(v)) : v active}` | 1,016 | 1,148 |
| C1 | (unordered pair of isomorphism types of positive and negative, shared vertices) | 319 | 379 |
| C2 | unordered pair of isomorphism types of positive and negative | 86 | 86 |
| C4 | unordered pair of degree sequences (positive, negative) | 65 | 65 |
| C5 | (active vertices, components of the union, cycle rank of the union, unordered pair of cycle ranks of positive and negative) | 53 | 60 |
| C8 | (active vertices, uncancelled edges per side) | 19 | 21 |
| C6 | active vertices only | 8 | 9 |
| C7 | total collapse to one class (planted negative) | 2 | 2 |

C0w, C9, C10 and C11 are additions to the requested ladder.  C0w is the natural control one
step below the record identity.  C9, C10 and C11 were added because every requested rung
failed and the live question became how much of `W` a class function has to see.  The
carrier records are always their own class, in every coarsening including C7 — that is why
C7 has two classes and not one.

The ladder is a poset, not a chain.  Machine-checked partition containment, identical at
both arities and stored in `refinement_n9.json` and `refinement_n10.json`:

```
C10 refines C11, C9, C3, C1, C2, C4, C5, C8, C6, C7
C11 refines C1, C2, C4, C5, C8, C6, C7
C9  refines C3, C1, C2, C4, C8, C6, C7
C3  refines C4, C8, C6, C7
C1  refines C2, C4, C8, C6, C7
C2  refines C4, C7
C5  refines C8, C6, C7
C8  refines C6, C7
C4, C6 refine C7
```

C1 and C3 are incomparable, C5 sits under none of C1, C2, C3, C4, and C9 and C11 are
incomparable.

## Method, and what is exact

The class-sum matrix `S` has one column per class and one row per element of the saved row
universe.  A class sum adds the columns of the **stored records** in the class, which is
the object the question is about: a certificate whose coefficient for an atom is
`x_{phi(W)}` contributes `sum_c x_c S_c` with `S_c` the record sum.  The variant that
weights each signed graph once rather than once per stored pair is reported separately
below.

* **Ranks are modular.**  `rank S` and `rank [S | b]` are computed at `p = 1000003` and
  `p = 1000033` with a streaming reduced-row-echelon routine in float64 arithmetic kept
  exact (every accumulated dot product stays below `2**53`; the code raises rather than
  round).  A modular rank is a lower bound for the rational rank.  The two primes agree in
  every cell of both tables.
* **Exact rank where it is cheap.**  For coarsenings with at most 400 classes an integer
  basis of `ker S_R` over the modular pivot rows `R` is computed with FLINT and verified
  against *every* row of `S`.  That supplies the matching upper bound and pins the rational
  rank.  Above 400 classes the tables give the modular value, and the exact statement is
  `rank_Q(S) >= that value`.
* **Verdicts are exact and do not depend on the ranks.**  MEMBER is certified by an exact
  rational `c` with `S c = b` checked on every row.  NON_MEMBER is certified by an exact
  rational `y`, supported on `rank + 1` rows, with `y^T S = 0` on every class and
  `y^T b != 0`.  Both are integer identities checked modulo a set of primes whose product
  exceeds twice a proved bound on the residual, so a passing check is a proof rather than a
  probabilistic test.  Each JSON records the bound in bits, the prime count, and the
  modulus in bits.

## Results

### n = 9 — 10,976 records, 6,335 rows (6,326 hinge + 9 linear)

| coarsening | classes | rank S (p=1000003) | rank [S\|b] | rank S (p=1000033) | rank [S\|b] | exact rank | verdict | certificate |
|---|---:|---:|---:|---:|---:|---:|---|---|
| C0 | 10,976 | 1,506 | 1,506 | 1,506 | 1,506 | modular only | MEMBER | primal, support 415 |
| C0w | 6,197 | 1,506 | 1,506 | 1,506 | 1,506 | modular only | MEMBER | primal, support 415 |
| C10 | 4,985 | 1,505 | 1,505 | 1,505 | 1,505 | modular only | MEMBER | primal, support 573 |
| C11 | 4,605 | 1,504 | 1,504 | 1,504 | 1,504 | modular only | MEMBER | primal, support 596 |
| C9 | 1,501 | 1,080 | 1,081 | 1,080 | 1,081 | modular only | NON_MEMBER | dual on 1,081 rows |
| C3 | 1,016 | 795 | 796 | 795 | 796 | modular only | NON_MEMBER | dual on 796 rows |
| C1 | 319 | 298 | 299 | 298 | 299 | 298 | NON_MEMBER | dual on 299 rows |
| C2 | 86 | 86 | 87 | 86 | 87 | 86 | NON_MEMBER | dual on 87 rows |
| C4 | 65 | 65 | 66 | 65 | 66 | 65 | NON_MEMBER | dual on 66 rows |
| C5 | 53 | 51 | 52 | 51 | 52 | 51 | NON_MEMBER | dual on 52 rows |
| C8 | 19 | 18 | 19 | 18 | 19 | 18 | NON_MEMBER | dual on 19 rows |
| C6 | 8 | 8 | 9 | 8 | 9 | 8 | NON_MEMBER | dual on 9 rows |
| C7 | 2 | 2 | 3 | 2 | 3 | 2 | NON_MEMBER | dual on 3 rows |

### n = 10 — 12,248 records, 16,719 rows (16,709 hinge + 10 linear)

| coarsening | classes | rank S (p=1000003) | rank [S\|b] | rank S (p=1000033) | rank [S\|b] | exact rank | verdict | certificate |
|---|---:|---:|---:|---:|---:|---:|---|---|
| C0 | 12,248 | 2,166 | 2,166 | 2,166 | 2,166 | modular only | MEMBER | primal, support 424 |
| C0w | 7,203 | 2,166 | 2,166 | 2,166 | 2,166 | modular only | MEMBER | primal, support 424 |
| C10 | 5,790 | 2,161 | 2,161 | 2,161 | 2,161 | modular only | MEMBER | primal, support 515 |
| C11 | 5,363 | 2,154 | 2,154 | 2,154 | 2,154 | modular only | MEMBER | primal, support 905 |
| C9 | 1,706 | 1,285 | 1,286 | 1,285 | 1,286 | modular only | NON_MEMBER | dual on 1,286 rows |
| C3 | 1,148 | 927 | 928 | 927 | 928 | modular only | NON_MEMBER | dual on 928 rows |
| C1 | 379 | 358 | 359 | 358 | 359 | 358 | NON_MEMBER | dual on 359 rows |
| C2 | 86 | 86 | 87 | 86 | 87 | 86 | NON_MEMBER | dual on 87 rows |
| C4 | 65 | 65 | 66 | 65 | 66 | 65 | NON_MEMBER | dual on 66 rows |
| C5 | 60 | 58 | 59 | 58 | 59 | 58 | NON_MEMBER | dual on 59 rows |
| C8 | 21 | 20 | 21 | 20 | 21 | 20 | NON_MEMBER | dual on 21 rows |
| C6 | 9 | 9 | 10 | 9 | 10 | 9 | NON_MEMBER | dual on 10 rows |
| C7 | 2 | 2 | 3 | 2 | 3 | 2 | NON_MEMBER | dual on 3 rows |

The C0 control reproduces the recorded ranks exactly: 1,506 of 10,976 columns at n=9 and
2,166 of 12,248 at n=10.  C0w has the same rank because a class of C0w is a set of
identical columns, so its class sum is a scalar multiple of a single column and the span is
unchanged; its certificate is the recorded witness divided by the class multiplicities and
re-verified on every row.  The planted negative C7 is NON_MEMBER at both arities, as it had
to be.

### MEMBER solutions

| n | coarsening | support | denominator lcm | factorization |
|---|---|---:|---:|---|
| 9 | C0 | 415 | 326,592,000 | `2^9 · 3^6 · 5^3 · 7` |
| 9 | C0w | 415 | 1,358,408,301,992,501,760,000 | `2^12 · 3^7 · 5^4 · 7^2 · 11 · 13 · 17 · 19 · 23 · 59 · 79` |
| 9 | C10 | 573 | 13,584,083,019,925,017,600,000 | `2^13 · 3^7 · 5^5 · 7^2 · 11 · 13 · 17 · 19 · 23 · 59 · 79` |
| 9 | C11 | 596 | 1,966,455,765,950,460,615,806,976,000 | `2^15 · 3^9 · 5^3 · 7^2 · 11^2 · 13^2 · 17 · 19^2 · 23 · 37 · 59 · 79` |
| 10 | C0 | 424 | 304,819,200 | `2^10 · 3^5 · 5^2 · 7^2` |
| 10 | C0w | 424 | 830,243,463,152,463,360,000 | `2^12 · 3^8 · 5^4 · 7^3 · 11 · 13 · 19 · 29 · 31 · 59` |
| 10 | C10 | 515 | 7,486,263,091,476,449,280,000 | `2^14 · 3^8 · 5^4 · 7^4 · 11 · 13 · 19^2 · 29 · 31` |
| 10 | C11 | 905 | 30,634,524,420,419,297,983,087,042,560,000 | `2^16 · 3^8 · 5^4 · 7^7 · 11 · 13 · 19^2 · 23 · 31 · 37^2 · 41 · 67` |

The C0 rows are the pinned witnesses (`2^9·3^6·5^3·7` and `2^10·3^5·5^2·7^2`), which is the
provenance check that this pipeline reads the same system the exact-witness work did.  The
class-uniform denominators are much uglier, and their extra prime factors are the class
multiplicities the coefficients get divided by; these are the solutions forced by the
modular pivot minor, not minimal-denominator ones.

The finest MEMBER coarsening below C0 is C11 in the refinement order along the chain
`C10 > C11 > C1`, with support 596 of 4,605 classes at n=9 and 905 of 5,363 at n=10.

## Robustness: unweighted class sums

A class sum that weights each signed graph once instead of once per stored pair (one
representative record per `W` orbit) gives identical verdicts.  Outputs are in `dedup-w/`.

| n | coarsening | classes | rank (weighted) | rank (unweighted) | verdict, both |
|---|---|---:|---:|---:|---|
| 9 | C0 | 10,976 / 6,197 | 1,506 | 1,506 | MEMBER |
| 9 | C10 | 4,985 | 1,505 | 1,505 | MEMBER |
| 9 | C11 | 4,605 | 1,504 | 1,504 | MEMBER |
| 9 | C9 | 1,501 | 1,080 | 1,079 | NON_MEMBER |
| 9 | C1 | 319 | 298 | 298 | NON_MEMBER |
| 9 | C7 | 2 | 2 | 2 | NON_MEMBER |
| 10 | C0 | 12,248 / 7,203 | 2,166 | 2,166 | MEMBER |
| 10 | C10 | 5,790 | 2,161 | 2,161 | MEMBER |
| 10 | C11 | 5,363 | 2,154 | 2,154 | MEMBER |
| 10 | C9 | 1,706 | 1,285 | 1,284 | NON_MEMBER |
| 10 | C1 | 379 | 358 | 358 | NON_MEMBER |
| 10 | C7 | 2 | 2 | 2 | NON_MEMBER |

## Interpretation

Every coarsening in the requested ladder fails at both arities, and so does C9, the common
refinement of its two finest rungs, so no certificate whose coefficients depend only on
those graph invariants exists at `n = 9` or `n = 10`.  Membership returns only once the
class function also sees the isomorphism type of the unsigned union graph, and even then
the passing coarsenings are mild ones — 4,605 and 5,363 classes against 6,197 and 7,203
signed-graph orbits — not the small class count a uniform construction would want.  The
failures are structural rather than mere rank deficiency: at C2 the class-sum matrix
already has full column rank and the target still leaves its span, with an exact dual
vector as the receipt.

## Reproduction

```bash
source .venv/bin/activate
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2

python artifacts/math/class-sum-n9-n10/class_sum_test.py --n 9 \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --witness artifacts/math/exact-witness-n9-n10/recovered_n9_witness.json \
  --outdir artifacts/math/class-sum-n9-n10
python artifacts/math/class-sum-n9-n10/class_sum_test.py --n 10 \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --witness artifacts/math/exact-witness-n9-n10/recovered_n10_witness.json \
  --outdir artifacts/math/class-sum-n9-n10

# refinement poset (add --refinement-only to either command above)
# unweighted variant (add --dedup-w and --outdir .../dedup-w,
#   --coarsenings C0 C10 C11 C9 C1 C7)
```

The n=9 run took 218 s and the n=10 run 813 s, both with two BLAS threads on a shared host.
Runs are deterministic: records are processed in file order, classes are ordered by their
canonical JSON label, and the pivot sets come from a fixed prime.  Outputs are
`class_sum_n{9,10}.json` (everything, including the structure block and provenance),
`class_sum_n{9,10}_{C*}.json` (one per coarsening, with class labels, class sizes, and the
MEMBER solution or the dual certificate), `refinement_n{9,10}.json`, and the same set under
`dedup-w/`.  Files over 400 KB were gzipped after the run and carry a `.gz` suffix; nothing
else was edited.

## No claim beyond n = 9 and n = 10

These results are for `n = 9` and `n = 10` only and do not imply anything at `n = 11` or
for all `n`.  A MEMBER verdict at a coarsening is the existence of a class-uniform
certificate for that `n`, not a formula.
