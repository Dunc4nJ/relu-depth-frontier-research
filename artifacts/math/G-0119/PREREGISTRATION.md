# G-0119 preregistration — algebraic signed-degree degree-raising operator

Registered on 2026-08-31 before implementing the producer and before computing
any membership, rank, residual, fitted coefficient, or MAX11 semantic value for
this family.

## Exact target and cousin boundary

The campaign target remains a finite exact two-hidden-layer ReLU identity for
`MAX11` on all of `R^11`.  This experiment asks whether one *fixed algebraic
operator* on a source certificate transports both known lower degree raises and
then, without any refit, transports the public degree-four MAX10 certificate to
an exact degree-five MAX11 identity.

The following do not count as success: fitting the 395 G-0115 coefficients,
fitting MAX8-to-MAX9 alone, agreement on sampled points or sampled rows,
hinge-only cancellation without the complete linear vector, modular membership
without a characteristic-zero lift, or membership in a source-derived span
with untied orbit coefficients.  Even an exact degree-five graphical MAX11
identity would settle only the MAX11 first rung; it would not prove the
all-`n` target or a normal-form theorem for arbitrary two-hidden-layer networks.

## Frozen operator

Let a source term be the pair of edge multisets `(A,B)`, with rational source
coefficient `c`, on `n` labels and branch degree `k`.  Put `N=n+1`, extend the
source by one isolated label, and range independently over every loop-or-nonloop
edge `e,f` in

```text
E_N = {(i,j): 1 <= i <= j <= N}.
```

Write `W = chi_A - chi_B` in the integer edge-occurrence space and
`U = chi_e - chi_f`.  Let `D` be the unsigned endpoint-incidence map, with a
loop contributing **one**, not two, to its endpoint.  Define the four integer
pairings

```text
a = <W,U>                 edge-multiplicity alignment
b = <D W,D U>             signed-degree alignment
q = <U,U>                 added-edge difference norm
r = <D U,D U>             endpoint-incidence difference norm.
```

The basis is frozen to exactly the following twelve monomials, in this order:

```text
1, a, b, a^2, a*b, b^2, q, r, a*q, b*q, a*r, b*r.
```

No topology signature, source index, target residual, selected G-0115 support,
column number, graph hash, or absolute coordinate label enters the basis.  For
unknown rational vectors `alpha,beta in Q^12`, the raw descriptor weight is

```text
w_k(W,U) = sum_j (alpha_j + k beta_j) p_j(W,U).
```

The operator is the raw-multiplicity sum

```text
T_k(C_n) = sum_source_terms c_t sum_(e,f in E_N)
           w_k(W_t, chi_e-chi_f) Phi_N(A_t+e, B_t+f).
```

This is a 24-parameter affine-in-degree recurrence.  Raw sum is the only
aggregation convention.  There is no orbit averaging and no later change of
normalization.

Simultaneous relabelling permutes edge and incidence coordinates, while global
branch swap sends `(W,U)` to `(-W,-U)`; all twelve monomials are therefore
invariant.  These invariances are implementation controls, not fitted facts.

## Frozen calibration and stopping rule

Build the complete exact ordered-cone normal forms for these two transitions:

```text
public MAX6,  k=2  -> N=7, degree 3;
public MAX8,  k=3  -> N=9, degree 4.
```

The two full systems are stacked before inspecting either membership result.
Solve over `Q` for the same 24 values `(alpha,beta)`, targeting zero on every
primitive hinge coordinate and the full linear vectors `e_7` and `e_9`.
Rank and augmented rank are exact characteristic-zero ranks.  If the joint
system is inconsistent, stop this family, serialize an exact inconsistent row
or minor witness, and do not enlarge, prune, rescale, or otherwise adapt the
basis.  A separate MAX9-only solution, if one exists, is not inspected and is
not a transport result.

If the joint system is consistent, choose the deterministic RREF solution with
all free variables set to zero, serialize every rational parameter, and replay
both complete normal forms from the serialized law.  Only then freeze the law
for the target transition.

## Frozen MAX10-to-MAX11 replay

Apply the unchanged serialized law at `k=4` to every raw one-edge-per-branch
lift of all 402 public MAX10 terms.  No coefficient, basis monomial, loop
convention, orbit representative, support threshold, or normalization may be
changed.  Success requires an independently serialized finite degree-five
certificate and an exact global ordered-cone replay with:

```text
all complete MAX11 primitive hinge coordinates = 0;
all eleven linear coordinates                  = (0,...,0,1).
```

Anything less is a null for this frozen recurrence.  No finite evaluation set
is admissible as a substitute for the complete normal form.

## Exact arithmetic and reconciliation

Source coefficients are scaled by their exact denominator LCM, so every
generated basis column is an integer vector.  Integer accumulation must prove
an a priori no-overflow bound before using fixed-width arithmetic; otherwise it
must use arbitrary-precision integers.  Modular arithmetic may be used only to
locate pivots or a witness and must be replayed over `Q` before any decision.

Raw counts, signed-`W` fibers, common-loop/common-nonloop contributions, and
feature sums must reconcile exactly.  Within a cancelled signed-`W` fiber, the
nonlinear semantic row is shared, while common edges are restored as their
explicit symmetric linear contribution.  The implementation must never call
signed-`W` equality complete atom equality.

## Controls frozen before outcomes

1. Recompute the public MAX6, MAX8, and MAX10 identities in exact ordered-cone
   normal form; a one-numerator-unit mutation of their first nonzero
   coefficient must fail.
2. Replay the exact 395-term G-0115 MAX9 certificate against the bound complete
   matrix and reject a one-unit coefficient mutation.  This is a machinery
   control, not calibration data.
3. Two fixed simultaneous coordinate relabellings must preserve all twelve
   features and the emitted aggregate semantics.  Relabelling the source while
   holding `(e,f)` fixed and relabelling only `e` must each be detected on
   planted descriptors for which an added endpoint meets source support.
4. Global branch swap must preserve every feature and aggregate column.
5. A planted implementation mutant that counts loops twice in `D` must be
   detected by the feature control.  The scientific run always counts a loop
   once.
6. If a joint law exists, deleting its first nonzero parameter, changing the
   first source coefficient by one numerator unit, and changing one emitted
   coefficient by one numerator unit must each break complete exact replay.
7. Literal permutation enumeration and the bound dynamic program must agree on
   fixed degree-two and degree-three atoms before the DP is used at scale.

## Bound inputs

```text
026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83  certificate_6_2.json
68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3  certificate_8_3.json
10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4  certificate_10_4.json
628a836542339a522fde173f13749bad29f150bdff69e7f66aeae26f786e963e  G-0115/unrestricted_full_semantic_certificate_v1.json
2fa23b8346858e85b4689a36c795ddac6d109ff42535d2238502b3c64117a148  G-0115/parity_lift_representatives_v1.jsonl.gz
f1a4f7fb1a449d2f1ef8a41fc948c1fb893039ae3f8d432b691d4ae1cfbdff1e  G-0115/unrestricted_full_semantic_matrix_v1.npy
8e4f59489d2eb87813f2020f60e5f61ca8caef6f3d2b5b30941b14fd3a8d569b  G-0115/unrestricted_full_semantic_matrix_v1.json
e400d35b6eb73a3e8821ed32c4c02742d46a15276aa2832b494dc9322d57f93d  G-0115/semantic_repair.py
d63f08e9e641109154d0e16f0d84d04a0ad4edd4402b8ffe5d01985de9163f71  G-0094/cleanroom_star_quotient.py
```

## Negative-claim boundary

Joint nonmembership rejects only this twelve-monomial, affine-in-degree,
raw-sum algebraic operator.  It does not reject other signed-degree
polynomials, other equivariant semantic operators, the untied lift spans, the
complete degree-five graphical dictionary, or unrestricted MAX11
representability.  A null triggers a separately preregistered, genuinely
different structural route; it does not license post-hoc basis expansion.
