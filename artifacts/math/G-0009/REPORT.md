# G-0009 research report

## Executive result

G-0009 derived one exact lift operator and tested two small, principled MAX11
families outside G-0008's same-component search.

The strongest positive result is the common-edge identity

    Phi_N(A+e,B+e) = Phi_N(A,B) + 2(N-2)! F_2^(N),

where `Phi_N` is the unnormalized full permutation symmetrization and `e` is
any fixed loopless edge.  Its location is irrelevant after symmetrization.
The identity preserves two-hidden-layer ReLU compilability.

The strongest negative result is deliberately bounded:

> On the frozen 886-row system (364 orbit evaluations, 511 selected hinge
> coefficients, and 11 linear coefficients), every one of the 3,615
> cross-component columns and every one of the 4,916 beta2 common-edge columns
> lies in the rational column span of G-0008's 9,804 same-component baseline.

This follows because the baseline is a literal submatrix of each union and
the exact rational rank remains 694 after either family is appended.  It is a
finite-system redundancy statement, not global functional redundancy, not a
lower bound for arbitrary pair atoms, and not a resolution of MAX11.

The preregistered widening gate required genuine new held-out span.  Both
families added zero held-out and joint rank, so the larger 183,064-item raw
independent-chord family was not enumerated.

## Mathematical objects

For `h_ij(x)=max(x_i,x_j)`, a degree-`k` pair atom is

    phi_(A,B)(x) = max(
        sum_(i,j in A) h_ij(x),
        sum_(i,j in B) h_ij(x)
    ),

where `A` and `B` contain `k` unordered coordinate pairs.  Its unnormalized
symmetrization is

    Phi_N(A,B)(x) = sum_(sigma in S_N) phi_(sigma A, sigma B)(x).

The graph quotient permits a common vertex relabeling and one global
`A <-> B` swap.  Edge ordering inside a side is immaterial.  In the colored
union multigraph, every edge occurrence is counted, including an edge shared
by both colors.  For `e` edge occurrences, `r` active vertices, and `c` active
components, the cycle rank is `beta=e-r+c`; ambient isolates are omitted from
`r` and `c`.

## Exact common-edge lift

Let

    U = sum_(a,b in A) h_ab(x),
    V = sum_(a,b in B) h_ab(x),
    h = h_e(x).

Pointwise,

    max(U+h,V+h) = h + max(U,V).

After summing over all `N!` coordinate permutations, the source term is
`Phi_N(A,B)`.  Every unordered target edge receives exactly `2(N-2)!`
preimages of `e`, proving

    Phi_N(A+e,B+e)
      = Phi_N(A,B) + 2(N-2)! F_2^(N),

where

    F_r^(N)(x) = sum_(S subset [N], |S|=r) max_(i in S) x_i.

If a degree-`k` certificate satisfies

    sum_t c_t Phi_m(A_t,B_t) = MAX_m,

then permutation counting and `sum_t c_t=1/(k m!)` give

    sum_t c_t Phi_N(A_t+e,B_t+e)
      = (N-m)! F_m^(N)
        + 2(N-2)!/(k m!) F_2^(N).

The coefficient sum follows by evaluating all coordinates at one.  The
attestation records each proof obligation and an exhaustive exact-Fraction
MAX5-to-MAX6 check over all 28 nondecreasing six-tuples from `{-2,0,3}` and
all `6!` permutations.  The two aggregate lifts obtained from the audited
MAX9 hybrid and public MAX10 certificates have rational rank two; adjoining
MAX11 raises the ordered-chamber rank to three.  Thus those two controls
alone cannot produce MAX11.

Every lifted summand is still

    max(sum of five pairwise ReLUs, sum of five pairwise ReLUs).

The pairwise ReLUs occupy hidden layer one, the branch maximum occupies
hidden layer two, and rational certificate coefficients appear only at the
linear output.

## Frozen candidate families

### Cross-component family

The public MAX10 certificate contains 252 full-support two-component forest
terms.  For every source term, vertex 11 is attached by an A-colored edge to
one component and by a B-colored edge to the other, in both component
orientations.

- raw generated candidates: 9,200;
- exact graph classes: 3,615;
- active vertices: 11;
- connected components: 1;
- colored multigraph beta: 0;
- all uncolored unions: simple loopless trees.

This family is invariantly disjoint from G-0008: cross-component unions are
connected beta=0 trees, whereas G-0008's same-component lifts leave the
other source component disconnected and have beta=1.

### Beta2 common-internal-edge family

For each of the same 252 source forests, choose a loopless edge wholly inside
one active component and append that same edge to A and B.  Vertex 11 remains
an ambient isolate.

- raw generated candidates: 6,740;
- exact graph classes: 4,916;
- active vertices: 10 plus one ambient isolate;
- active components: 2;
- colored edge occurrences: 10;
- colored multigraph beta: 2.

The common-edge theorem implies a stronger structural fact: for a fixed
source atom, all allowed edge placements define the same global symmetrized
function.  Therefore the 4,916 graph classes collapse globally to at most
252 source-indexed functions.  Exact replay on the 886 stored rows finds no
within-source disagreements and exactly 252 distinct source columns.  Only
the within-source equality is globally proved; distinctness between the 252
source functions is established only on the stored rows.

### Quotient authority and limit

Both quotients use typed incidence graphs.  A NetworkX Weisfeiler-Lehman hash
is only a bucket accelerator; exact NetworkX VF2 isomorphism inside each
bucket is the equality authority.  The equivalence is all vertex relabelings
and one global color swap.

The counts are complete for the generated lists derived from the pinned 252
MAX10 terms.  They are not counts of all abstract MAX11 trees or beta2 atoms.
There is one quotient implementation and no independent enumerator.

## Frozen evaluation systems

### Orbit grid

The 364 orbit rows are all `S_11` orbits of `{0,1,2,3}^11`, indexed by the
multiplicity profile of levels 0, 1, 2, and 3.  Each row is an exact sum over
all distinct assignments having that profile.  Integer targets are the
corresponding distinct-assignment sums of MAX11.

### Adaptive held-out challenge

The held-out block contains:

- 511 lexicographically sorted primitive hinge directions;
- 11 ordered-cone linear-coordinate rows.

It has zero direction overlap with the first G-0008 cut selection.  However,
it is the complete second G-0008 cut batch, derived from the first solution's
residual.  It is therefore an adaptive residual challenge, not an IID test,
not a statistically meaningful holdout, and not preregistered independently
of G-0008's failure.

The joint system concatenates 364 orbit rows and 522 held-out/linear rows for
886 rows total.  Candidate coefficients use the internal normalization
`a=11!*certificate coefficient`; hinge targets are zero and the linear target
is `11!*e_11`.

## Exact ranks

Two finite-field ranks (primes 1,000,003 and 1,000,033) agree in every case,
but they are diagnostics only.  Each reported rational rank is certified by:

1. a modularly selected square minor that is nonzero over Q;
2. exact `fmpq` reconstruction of every nonpivot row from the pivot rows;
3. exact replay across every candidate column;
4. an exact target solve and replay across every row.

This proves the ranks of the stored integer matrices without materializing a
huge all-rational wide matrix.

### Cross-component results

| Rows | Family | Columns | rank_Q(A) | rank_Q([A|target]) | Target in span? |
|---|---|---:|---:|---:|---|
| orbit | same baseline | 9,804 | 192 | 192 | yes, finitely |
| orbit | cross alone | 3,615 | 179 | 180 | no |
| orbit | same + cross | 13,419 | 192 | 192 | yes, finitely |
| held-out | same baseline | 9,804 | 506 | 506 | yes, finitely |
| held-out | cross alone | 3,615 | 381 | 381 | yes, finitely |
| held-out | same + cross | 13,419 | 506 | 506 | yes, finitely |
| joint | same baseline | 9,804 | 694 | 694 | yes, finitely |
| joint | cross alone | 3,615 | 556 | 557 | no |
| joint | same + cross | 13,419 | 694 | 694 | yes, finitely |

The cross family adds zero rank to the same-component baseline on all three
row systems.

### Beta2 results

Here `baseline` means `same + cross`; the preceding table proves that it has
the same finite spans and ranks as `same` alone.

| Rows | Family | Columns | rank_Q(A) | rank_Q([A|target]) | Target in span? |
|---|---|---:|---:|---:|---|
| orbit | baseline | 13,419 | 192 | 192 | yes, finitely |
| orbit | beta2 alone | 4,916 | 125 | 126 | no |
| orbit | baseline + beta2 | 18,335 | 192 | 192 | yes, finitely |
| held-out | baseline | 13,419 | 506 | 506 | yes, finitely |
| held-out | beta2 alone | 4,916 | 216 | 217 | no |
| held-out | baseline + beta2 | 18,335 | 506 | 506 | yes, finitely |
| joint | baseline | 13,419 | 694 | 694 | yes, finitely |
| joint | beta2 alone | 4,916 | 252 | 253 | no |
| joint | baseline + beta2 | 18,335 | 694 | 694 | yes, finitely |

The beta2 family adds zero rank to the baseline on all three row systems.

## Explicit sparse duals

Let `R_(a,b,c,d)` denote the orbit row summing an atom over every distinct
assignment with `a,b,c,d` coordinates at levels `0,1,2,3`, respectively.

Every cross-component candidate column satisfies the exact equation

    (2480/3) R_(0,0,0,11)
      - 7 R_(0,0,3,8)
      - 5 R_(0,0,4,7)
      + R_(0,2,2,7) = 0.

For MAX11, the left-hand pairing is

    (2480/3)*3 - 7*495 - 5*990 + 5940 = 5 != 0.

Thus the target is outside the cross-only span already on four orbit rows.

Every beta2 common-edge candidate column satisfies

    -(824/15) R_(0,0,0,11) + R_(0,0,2,9) = 0,

whereas MAX11 gives

    -(824/15)*3 + 165 = 1/5 != 0.

Thus the target is outside the beta2-only span already on two orbit rows.

`scripts/verify_duals.py` reconstructs both full 886-row matrices, validates
their stored byte hashes, clears denominators, replays annihilation across all
3,615 or 4,916 candidate columns, and checks the nonzero target pairing.  The
machine-readable output includes full row semantics.

These duals exclude the target only from each named standalone family.  They
do not exclude unions with other atoms or arbitrary two-hidden-layer ReLU
networks.

## Stopping rule and negative result

Before the beta2 evaluation, the next widening was frozen as independent A
and B internal chords on the same 252 sources, with 183,064 raw candidates
before quotienting.  The gate for executing it was genuine new span on the
held-out or joint rows.

Observed gains were exactly zero:

    cross held-out gain = 0
    cross joint gain     = 0
    beta2 held-out gain  = 0
    beta2 joint gain     = 0

The family was therefore not widened.  This prevents a failed discriminator
from turning into an unbounded post-hoc search.

## Failures and engineering correction

An initial attempt to compute an exact rank by converting an entire wide
matrix to rational big integers reached approximately 13.5 GB and was stopped
without producing a claim.  The replacement compact certificate uses one
exact square minor plus complete exact row-span replay.  All ranks in the
frozen reports come from the replacement method.

No exact global MAX11 combination was obtained.  Finite target membership of
the baseline is not sufficient: a global certificate would require solving
and then replaying every hinge and linear coefficient exactly.

## Epistemic limits

- The common-edge algebra is an ordinary mathematical proof, supported by an
  exhaustive small-`n` exact test but not yet formalized in Lean.
- Candidate enumeration and quotienting have only one NetworkX/VF2 route.
- Orbit and hinge columns reuse the G-0006/G-0008 evaluator lineage.  Exact
  arithmetic protects against rounding error, not a shared implementation bug.
- The 511-row challenge is adaptive and cannot be described as an independent
  statistical holdout.
- Rank equality establishes column-span redundancy only after restriction to
  the stated 886 rows.
- The generated families are certificate-derived slices, not complete MAX11
  topology strata.
- Same-lineage agent review is challenge evidence, not independent
  mathematical replication.
- No campaign claim ledger entry is created or promoted here.

## Smallest future discriminator

If the research lead later reopens this branch, the smallest frozen family
that breaks common-edge additivity is the 183,064-raw independent A/B
internal-chord family.  It should be attempted only with an independent atom
evaluator or a genuinely new-span prefilter.  A more globally meaningful but
larger route remains the complete full-support colored-tree universe proposed
in G-0007.  Neither route was executed in G-0009.

