# G-0124 preregistration — isolation-aware rooted Reynolds gap kernel

Registered on 2026-08-31 after inspecting the frozen G-0120 null witness, but
before constructing any isolation-aware semantic column, computing any new
rank, fitting any new coefficient, or evaluating any `Gap10 -> Gap11` value.

## Decision forced by the old obstruction

The first thirteen rows of the published G-0120 witness all come from
`GapCert_6 -> Gap_7` and satisfy

```text
rank_Q(A_13)       = 12,
rank_Q([A_13 | b]) = 13.
```

Consequently, allowing the same seventeen orbit weights to depend on arity,
degree, or transition cannot repair even this one fixed-arity system.  Changing
raw sums to orbit averages only rescales the seventeen columns by nonzero
fixed-arity factors and cannot change their span.  Those apparently small
relaxations are therefore rejected without a new scientific run.

The unique primitive integer left relation of this 13-row obstruction, with
first nonzero entry positive, is

```text
lambda = (
   24877879652,    5644990098,   18735931395,
   36075148648, 1774428225462, -486075915678,
   72061959924,  -30238018092,  349051285883,
  196759610464,   -4358895750,    -622183212,
     311091606
)

lambda^T A_13 = 0,
lambda^T b    = -74661985440 != 0.
```

This relation is derived entirely from the already serialized G-0120 witness.
It is a design input, not an outcome of the experiment below.

## One new source statistic

For a source pair `t=(A_t,B_t)` on the `n` old labels, define

```text
q_n(t) = n - | V(A_t) union V(B_t) |,
```

where `V` contains every endpoint of every loop or nonloop edge in either
branch.  Thus `q_n(t)` is the number of old labels isolated in both source
branches before the new distinguished root is adjoined.  It is an integer,
is invariant under old-label relabelling and branch swap, and is computed from
the source pair alone.  The subsequently adjoined root is not counted.

No provenance bit, coefficient sign, graph hash, source index, target residual,
selected support, or fitted partition may enter the kernel.  In particular,
all source terms with the same `q_n(t)` are treated identically, regardless of
whether they came from `n C_n` or `-Ind_n(C_(n-1))`.

## Frozen nested parameter family

Let `o(e,f;*)` be exactly the seventeen unordered rooted edge-pair orbits from
G-0120.  For a source term `t`, append `e` to its left branch and `f` to its
right branch, use the same raw ordered-edge-pair sum and full Reynolds
symmetrization as G-0120, and test the following two nested stages.

### Stage A — additive isolation main effect (18 parameters)

```text
w(t,e,f) = gamma_o + delta q_n(t).
```

There are seventeen orbit intercepts `gamma_o` and one common isolation slope
`delta`.  Equivalently its new semantic column is the sum of the seventeen
orbit-specific `q` columns.

### Stage B — orbit-by-isolation affine interaction (34 parameters)

Run Stage B only if Stage A is exactly inconsistent:

```text
w(t,e,f) = gamma_o + eta_o q_n(t).
```

There are seventeen intercepts and seventeen slopes.  This is the complete
first-degree tensor product of the old rooted-orbit flag with the single
source statistic `q`; it is not a per-source fit.

If Stage A is consistent, Stage B is not evaluated.  If Stage A is
inconsistent, Stage B is the sole preregistered escalation.  The total family
budget is therefore at most 34 rational parameters.  No quadratic term,
second source statistic, arity coefficient, provenance split, extra orbit,
normalization change, or post-outcome rescue is allowed in G-0124.

## Exact lower-transition gate

Use exactly the three frozen source representations and all bindings from
G-0120:

```text
GapCert_6  =  6 public C6  - Ind_6(public C5),
GapCert_8  =  8 public C8  - Ind_8(public C7),
GapCert_10 = 10 public C10 - Ind_10(G-0115 395-term C9).
```

For each stage, stack the complete exact ordered-cone systems

```text
R(GapCert_6) = G_7 = x_(7)-x_(6),
R(GapCert_8) = G_9 = x_(9)-x_(8).
```

Every primitive hinge coordinate must be zero and every linear coordinate
must match.  The decision is over `Q`; modular or floating arithmetic may not
decide it.

Before a full solve, report the exact old-witness sensitivities
`lambda^T psi` for every newly admitted column.  If they are all zero, the old
13-row witness certifies immediate nonmembership for that stage.  A nonzero
sensitivity only kills the old witness; it is not evidence of membership and
the complete stacked solve remains mandatory.

If a stage is consistent, choose the deterministic RREF solution with every
free variable set to zero, serialize it, and replay both complete lower
normal forms exactly.  Only the first consistent stage may open the holdout.
If both stages are inconsistent, serialize a small exact rank witness for
Stage B and stop G-0124.

## Frozen MAX11 holdout rule

Before one lower stage passes and its exact coefficient vector is serialized,
the producer must not construct, price, rank, solve, or semantically evaluate
any isolation-aware `GapCert_10 -> Gap_11` column.  The already published
G-0120 replay of `GapCert_10` itself is not an isolation-aware holdout read.

After a lower pass, apply the unchanged chosen law to all

```text
797 * 66^2 = 3,471,732
```

raw lifts of `GapCert_10`.  No refit, coefficient change, feature change,
support threshold, or alternate solution is permitted.  Exact success requires

```text
R(GapCert_10) = G_11 = x_(11)-x_(10)
```

in the complete global ordered-cone normal form.  If this gap identity passes,
compile

```text
C11 = (Ind_11(public C10) + R(GapCert_10)) / 11
```

and exactly replay the serialized finite graphical certificate as MAX11: zero
primitive-hinge residual and linear vector `(0,...,0,1)`.  A lower pass, an old
witness sensitivity, a finite evaluation panel, or a modular replay is not a
MAX11 result.  If the frozen holdout fails, record the complete exact residual
and stop; there is no holdout refit.

## Frozen controls

1. Bind and independently verify the G-0120 result and its reduced 13-row
   ranks before using its witness.  Recompute the primitive left relation and
   `lambda^T b` exactly.  Replacing `b` by zero must collapse the augmented
   rank.
2. Re-run the G-0120 public-certificate, source-gap, rooted-classifier,
   raw-count, quotient-reconciliation, literal-permutation, and mutation
   controls unchanged.
3. On fixed planted source pairs, `q_n(t)` must be invariant under two old-label
   relabellings and branch swap.  Adding one unused old label must increase it
   by exactly one; adding an edge incident to an isolated old label must
   decrease it by exactly one.  A mutant that counts the newly adjoined root as
   an old isolated label must be rejected by the direct definition check.
4. Each lower source multiset must contain at least two distinct `q` values;
   otherwise the new statistic is semantically constant there and the family
   stops as uninformative.
5. Stage A's single slope column must equal the exact sum of Stage B's
   seventeen orbit-slope columns.  Setting every `q` value to zero must recover
   the old G-0120 matrices and their inconsistency witness exactly.
6. Replacing `q` everywhere by `q+c` for fixed integer `c` must preserve the
   exact column span of both stages.  This checks that only affine isolation
   information, not an arbitrary choice of origin, drives the decision.
7. Any accepted lower solution must fail complete replay after deleting its
   first semantically active nonzero coefficient and after a one-numerator-unit
   mutation at the common coefficient denominator.
8. Any compiled MAX11 certificate, if reached, must reject a one-unit mutation
   of its first nonzero emitted coefficient.
9. The result writer is fail-closed, path-contained to this workspace, and
   uses exclusive creation.  The result binds the preregistration, producer,
   all inherited sources, row orders, matrices, targets, and exact witnesses by
   SHA-256.

## Stop rule and interpretation

- Stage A null, Stage B null: stop.  The result eliminates only isolation-
  affine kernels with at most 34 parameters on these frozen representations.
- Lower pass, holdout fail: stop.  The result is a failed arity transport, not
  a MAX11 theorem.
- Exact holdout and compiled replay pass: emit a candidate MAX11 graphical
  certificate for independent clean-room replay; do not call the all-`n`
  campaign target solved.

No G-0121/G-0123 master result may be inspected or used anywhere in G-0124.

## No-claim and cousin boundary

A null does not reject general rooted flag algebras, nonlinear source laws,
other source representations, the unrestricted MAX10 lift span, the complete
degree-five graphical dictionary, or MAX11 representability.  A lower pass is
only a recurrence on two frozen source representations.  Even an exact MAX11
certificate would not prove representation completeness, width efficiency,
trainability, approximation theory, or the charter's all-`n` statement.

## Bound inputs

```text
1f43bc85f8124e3147499527e6bd522e901c91d391b14d1d9c4fe12416ef8b79  artifacts/math/G-0120/PREREGISTRATION.md
988a354bf797e138c720c24694b0c2f3c6da31874b7ca3dab027dbb937469846  artifacts/math/G-0120/rooted_reynolds_gap.py
918de947cd2fb0bbc49849cbe76253b28f282c4f553c46525c73d6e98a6c9754  artifacts/math/G-0120/rooted_reynolds_gap_result.json
29d7c922dd917832d32c55c26ba8aa5f0056f3be78c8b18d1a9676f468009cd7  artifacts/math/G-0120/verify_rooted_reynolds_gap_result.py
d63f08e9e641109154d0e16f0d84d04a0ad4edd4402b8ffe5d01985de9163f71  artifacts/math/G-0094/cleanroom_star_quotient.py
698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694  literature/repos/max-relu-certificates/certificates/certificate_5_2.json
026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83  literature/repos/max-relu-certificates/certificates/certificate_6_2.json
b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be  literature/repos/max-relu-certificates/certificates/certificate_7_3.json
68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3  literature/repos/max-relu-certificates/certificates/certificate_8_3.json
10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4  literature/repos/max-relu-certificates/certificates/certificate_10_4.json
628a836542339a522fde173f13749bad29f150bdff69e7f66aeae26f786e963e  artifacts/math/G-0115/unrestricted_full_semantic_certificate_v1.json
```
