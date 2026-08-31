# G-0120 preregistration — rooted Reynolds recurrence for top gaps

Registered on 2026-08-31 after the frozen G-0119 algebraic recurrence was
rejected, but before implementing this producer and before computing any
rooted-orbit fit, rank, residual, or MAX11 semantic value.

## Exact semantic reduction

For a symmetric function on `n` variables define Reynolds induction by

```text
Ind_n(f)(x_1,...,x_n) = sum_(i=1)^n f(x_1,...,x_hat_i,...,x_n).
```

If `M_n=MAX_n` and `x_(n) >= x_(n-1)` are the two largest order statistics,
then

```text
Ind_n(M_(n-1)) = (n-1) x_(n) + x_(n-1),
G_n := n M_n - Ind_n(M_(n-1)) = x_(n) - x_(n-1).
```

Thus an exact certificate for the top gap `G_11`, together with the public
MAX10 certificate, gives

```text
MAX11 = (Ind_11(MAX10) + G_11) / 11.
```

This is an exact identity, not an inference from lower arities.  The experiment
asks whether the gap certificates admit a rooted Reynolds recurrence that the
MAX certificates themselves did not expose.

## Frozen source gap certificates

If `C_n` is a symmetrized graphical certificate for `MAX_n`, interpret every
term of `C_(n-1)` on `n` labels with label `n` initially isolated.  Under the
full `S_n` symmetrization this termwise embedding is exactly `Ind_n(C_(n-1))`.
The source representation is frozen as

```text
GapCert_n = n C_n - Ind_n(C_(n-1)).
```

Use exactly these three source representations:

```text
GapCert_6  =  6 * public C6  - Ind_6(public C5),
GapCert_8  =  8 * public C8  - Ind_8(public C7),
GapCert_10 = 10 * public C10 - Ind_10(G-0115 395-term C9).
```

The G-0115 degree-four identity is used literally for `C9`; it is not replaced
by the public 337-term certificate after seeing an outcome.  Duplicate terms
are retained with exact multiplicity unless exact full-atom aggregation is
performed transparently.

## Frozen rooted edge-pair kernel

To raise `GapCert_n` from degree `k` on `n` labels to degree `k+1` on
`N=n+1` labels, first adjoin one distinguished isolated root `* = N`.  Append
one loop-or-nonloop edge `e` to the left branch and one edge `f` to the right
branch, then apply the full `S_N` Reynolds symmetrization.

The weight depends only on the orbit of the unordered pair `{e,f}` under the
stabilizer `S_n` of the root.  Global branch swap makes `{e,f}` unordered.  The
kernel has exactly the following 17 rooted orbits and one arity-independent
rational weight `gamma_o` per orbit:

```text
RR                 two root loops
RS                 root loop + spoke
RL                 root loop + old loop
RE                 root loop + old nonloop
SS_same            identical spokes
SS_distinct        spokes to two distinct old vertices
SL_hit             spoke + old loop at its old endpoint
SL_miss            spoke + old loop elsewhere
SE_hit             spoke + old nonloop incident to its old endpoint
SE_miss            spoke + disjoint old nonloop
LL_same            identical old loops
LL_distinct        old loops at distinct vertices
LE_hit             old loop + incident old nonloop
LE_miss            old loop + disjoint old nonloop
EE_same            identical old nonloops
EE_share           distinct old nonloops sharing one endpoint
EE_disjoint        disjoint old nonloops.
```

Here `R` is the root loop, `S` a root-to-old spoke, `L` an old loop, and `E`
an old nonloop.  The operator is the raw-multiplicity sum

```text
R_gamma(GapCert_n)
  = sum_source_terms c_t sum_(e,f in E_N)
      gamma_orbit(e,f;*) Phi_N(A_t+e, B_t+f).
```

There is no dependence on the source graph, source index, signed degrees,
target residual, G-0115 selected support, column order, or graph hash.  There
is no orbit averaging, arity factor, affine-in-degree interpolation, or second
normalization convention.  The same 17 constants are used at all arities.

## Joint lower-transition gate and stop rule

Before inspecting either transition separately, stack the complete exact
ordered-cone systems

```text
R_gamma(GapCert_6) = G_7 = x_(7)-x_(6),
R_gamma(GapCert_8) = G_9 = x_(9)-x_(8).
```

Every primitive hinge coordinate must be zero and the complete linear vectors
must be `e_7-e_6` and `e_9-e_8`.  Solve once over `Q` for the same 17 weights.
Modular arithmetic may locate pivots only; every decision and witness is
replayed in characteristic zero.

If the stacked target is not in the 17-column span, serialize a small exact
integer or rational rank witness and stop this family.  Do not inspect or
report a transition-specific fit, add rooted or source features, introduce
degree dependence, or change raw sum to averaging.

If the joint system is consistent, choose the deterministic RREF solution with
all free variables zero, serialize it, and replay both complete lower normal
forms exactly.  Only that serialized law may reach MAX11.

## Frozen MAX10-to-MAX11 test

Apply the unchanged 17 weights to all raw lifts of `GapCert_10`.  No parameter,
root convention, orbit classifier, coefficient, support threshold, or
normalization may change.  Exact success requires

```text
R_gamma(GapCert_10) = G_11 = x_(11)-x_(10)
```

in the complete global ordered-cone normal form.  Then compile

```text
C11 = (Ind_11(public C10) + R_gamma(GapCert_10)) / 11
```

as a finite mixed-degree graphical certificate and replay every serialized
term exactly: all MAX11 primitive hinge coordinates zero and the eleven linear
coordinates exactly `(0,...,0,1)`.  A passing gap panel, finite evaluation set,
hinge-only check, or modular replay is insufficient.

If the target gap replay fails, stop and record the complete exact residual.
No refit on MAX11 is allowed.

## Frozen controls

1. Replay C5, C6, C7, C8, C10, and the G-0115 395-term C9 identity exactly;
   mutate the first nonzero coefficient of each by one numerator unit at its
   certificate denominator and require failure.
2. Replay `GapCert_6`, `GapCert_8`, and `GapCert_10` before lifting: zero
   internal hinges and complete linear vectors `e_n-e_(n-1)`.  Independently
   replay the termwise induction formula as `(n-1)x_(n)+x_(n-1)`.
3. The rooted orbit classifier must return exactly the 17 names above, be
   invariant under two fixed permutations of old labels and edge swap, and
   reconcile all `|E_N|^2` ordered edge pairs at `N=7,9,11`.
4. Moving the distinguished root while leaving the edge pair fixed must be
   detected on a planted spoke pair.  Collapsing the root distinction to the
   unrooted common/share/disjoint/loop classifier must also be detected.
5. Literal permutation enumeration and the exact DP must agree on fixed rooted
   degree-two and degree-three atoms.  A branch edge mutation must change the
   exact normal form.
6. If a joint law exists, deleting its first semantically active nonzero weight
   and mutating one emitted coefficient by one numerator unit must each break a
   complete lower replay.
7. A compiled MAX11 identity, if reached, must reject a one-unit mutation of
   its first nonzero emitted coefficient.

## Frozen counts

```text
GapCert_6 source rows:    4 +   3 =   7; raw lifts at N=7:      7 * 28^2 =       5,488
GapCert_8 source rows:   69 +  57 = 126; raw lifts at N=9:    126 * 45^2 =     255,150
GapCert_10 source rows: 402 + 395 = 797; raw lifts at N=11:   797 * 66^2 =   3,471,732
```

Every raw count and all 17 orbit subtotals must reconcile before semantic rank
access.

## Bound inputs

```text
698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694  certificate_5_2.json
026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83  certificate_6_2.json
b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be  certificate_7_3.json
68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3  certificate_8_3.json
10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4  certificate_10_4.json
628a836542339a522fde173f13749bad29f150bdff69e7f66aeae26f786e963e  G-0115/unrestricted_full_semantic_certificate_v1.json
d63f08e9e641109154d0e16f0d84d04a0ad4edd4402b8ffe5d01985de9163f71  G-0094/cleanroom_star_quotient.py
```

## No-claim boundary

A lower-transition null rejects only this 17-orbit, arity-independent rooted
raw-sum kernel.  It does not reject other Reynolds operators, other gap
representations, source-dependent laws, the MAX10 lift span, the complete
degree-five graphical dictionary, or MAX11 representability.  A lower pass is
still not evidence for MAX11 until the frozen law and compiled certificate pass
the full exact global replay.  Even a MAX11 certificate would not prove the
all-`n` campaign target or a completeness theorem for arbitrary networks.
