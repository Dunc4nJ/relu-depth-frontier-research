# G-0114 preregistration — exact degree-raising identity gate

Frozen after reading the already-produced G-0112 relation-slice decisions and
before computing any coefficient-tied aggregate, constrained rank, or
cross-arity replay in this track.

## Question and no-claim

G-0112 shows that the *untied* span obtained by adding one arbitrary edge to
each branch of each public MAX6 atom contains MAX7.  In fact, its frozen slice
output says that the share-one-nonloop and disjoint-nonloop slices each suffice
separately.  That does **not** yet give an operator on the public MAX6
certificate: the sparse solutions may use source terms with unrelated
coefficients.

This gate asks whether a coefficient law tied to the source certificate exists
and is simple enough to transport to MAX10 -> MAX11.  A pass at 6 -> 7 is only
an exact lower-arity identity candidate.  It is not a MAX11 identity unless the
same frozen law is replayed exactly at 10 -> 11.

## Bound inputs

```text
abd389675a5aaa39b0f670c0a8cf9394c69f8cc6f37bc3ab58dd3d8409e9c022  G-0112/lower_n_relation_slices_v1.json
e2c66d41acfd0b0688dd63370ab9861422dde1fee833c278fb892c261cb2c292  G-0112/lower_n_general_edge_potency_v1.json
93ff0492a8f0839d30a7b7cab5ab83696d6f54e80048da2586b8ae4afdbafa3b  G-0112/lower_n_double_star_potency.py
bfa7a73bd44ae12a40277d33374956f0a285577d20b3ab6ca09ddc110d2bdf22  G-0112/lower_n_relation_slices.py
698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694  certificate_5_2.json
026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83  certificate_6_2.json
b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be  certificate_7_3.json
10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4  certificate_10_4.json
```

All semantic comparisons use the complete exact ordered-cone normal form.
No sampled evaluation rows are admissible evidence.

## Frozen tests, in order

For a source certificate `sum_t c_t Phi(P_t) = MAX_n`, let

```text
U_R = sum_t c_t sum_{(e,f) in R} Phi(P_t + (e,f)),
```

where raw ordered edge-pairs retain their combinatorial multiplicities and
`R` is one of common, share-one, disjoint, unequal, has-loop, or all.

1. **Uniform relation test.**  Compute every `U_R` exactly.  Record its hinge
   support and linear vector.  A single relation passes only if a nonzero
   rational scalar multiple is exactly MAX7.  The relation-only family passes
   if MAX7 is in the exact rational span of the six `U_R` vectors.
2. **Per-source scalar test.**  For share-one and disjoint separately, form
   `U_{t,R}` before multiplication by `c_t`.  Solve for MAX7 in their four
   dimensional spans.  A source-coefficient law passes only when some exact
   solution has coefficients proportional to the four frozen `c_t`; merely
   finding four untied scalars is recorded as source-stratum dependence.
3. **Local-incidence law.**  Aggregate raw lifts by a frozen local signature:
   added-edge relation; for each added endpoint its degree in the left and
   right source multigraph; whether it is isolated in the source union; and
   the equality pattern of the two added edges.  Source term `t` contributes
   `c_t` times the shared signature weight.  Decide exact rational membership.
   A pass is a 6 -> 7 candidate law, not transport evidence.
4. **Cross-arity falsifier.**  Any law produced by (1) or (3) is frozen and
   replayed without refitting on the public MAX5 -> MAX6 certificate.  Missing
   signatures are assigned weight zero; extra signatures do not get fitted.
   Failure on any exact linear or hinge row rejects universality across these
   two arities.  Success is necessary, not sufficient, for 10 -> 11.
5. **Shared-law existence check.**  To avoid mistaking failure of one arbitrary
   pivot solution for failure of the whole law class, stack the complete
   6 -> 7 and 5 -> 6 systems and decide whether *any one* set of relation-only
   weights, and then any one set of local-signature weights, satisfies both
   targets simultaneously.  This is an exact joint rational membership test;
   it is the decisive falsifier for the two frozen law classes.

If tests (1)--(3) all fail, the claim is a sharp null: G-0112 proves potency of
an untied source-derived dictionary but supplies no relation-only or stated
local-incidence degree-raising identity.  If a test passes only by using a
number of free signature weights comparable to the exact normal-form rank, it
is classified as a compressed solve, not a universal formula.

## Controls

- replay the public MAX5, MAX6, and MAX7 certificates exactly;
- branch swap must preserve every tested semantic column;
- changing one frozen source coefficient by one unit must break any passing
  tied identity;
- deleting one nonzero fitted signature weight must break any passing law;
- all reported rank/membership decisions are over Q and replay every row.
