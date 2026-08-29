# Exact obstruction for the same-component family and common-edge lifts

Status: **internally certified bounded theorem (same-family T1)**.  The exact
linear-algebra certificate and the exhaustive graph-to-matrix semantic
regeneration have passed their declared gates.  The result is confined to the
registered finite family below; no different-family or human T2 review has
been obtained.

<!-- G0015_MACHINE_SCOPE_V1 {"claim_boundary":"exact nonmembership for the registered 16000-raw/9804-class same-component family union the 6740 named beta2-common edge-multiset lifts","family_B_adds_new_symmetrised_functions":false,"family_B_quotient_classes":4916,"family_B_raw_occurrences":6740,"family_F_quotient_classes":9804,"family_F_raw_occurrences":16000,"field":"R","no_claim":"Does not settle unrestricted MAX11 or exclude cross-component, multi-edge, other pair-atom, asymmetric, or arbitrary finite two-hidden-layer real-weight ReLU-network representations.","premise_sha256":{"beta2_mapping_audit":"88ba04742803439713e3a9fd7c01171c3f6fe3a6edc64b8d99b19c546d4c009d","exact_audit":"9c26c0e6329804ee2a87ec9ef6b86cd935c91551ca503a97409368f41ac3676a","exact_dual":"fe6768c8377aa1cc813dbd00805c807d4dd23f05ba246700503aa8598a951758","semantic_audit":"581a8d9b5a1cd28f1ee2896e119a262977084369d32550ca8523fd205596ec71","source_certificate":"10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4"},"schema":"max11-bounded-theorem-scope-v1","statement":"MAX11 is not in the real span of the registered 16000-raw/9804-class same-component family union the 6740 named beta2-common edge-multiset lifts."} -->

## Registered family

For two finite loopless edge multisets `A` and `B` on eleven labelled
vertices, with each edge occurrence counted in its branch sum, set

```text
Phi_(A,B)(x) = sum over pi in S_11 of
  max(
    sum_{uv in A} max(x_(pi(u)), x_(pi(v))),
    sum_{uv in B} max(x_(pi(u)), x_(pi(v)))
  ).
```

The raw family `F` consists of the 16,000 pairs obtained as follows.  Start
from the pinned MAX10 certificate (SHA-256
`10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4`)
and retain exactly the 252 terms in which `A_0` and `B_0` each have four
edges, all eight edges are distinct and loopless, their uncoloured union uses
all ten old vertices, and that union has exactly two connected components.
Add vertex 11 by one new `A` edge and one new `B` edge, with both old endpoints
chosen in the same connected component of the uncoloured union
`A_0 union B_0`.  Each colour is simple after the lift, although an `A` edge
and a `B` edge may coincide.  The component-size census is
`(2,8):168`, `(3,7):39`, `(4,6):32`, `(5,5):13`; consequently
`sum (|K_1|^2+|K_2|^2)=16,000`.  Vertex relabelling and one global `A/B` swap
give 9,804 stored representatives.

The claimed result concerns the real linear span of these atoms.  It does not
assert that `F` is complete for two-hidden-layer ReLU networks.

There is also a named 6,740-occurrence family `B` (called `beta2-common` in
the artifacts).  For each of the same 252 four-edge source pairs
`(A_0,B_0)`, choose any loopless old-vertex edge `e` lying wholly inside one
connected component of the uncoloured union, and append one occurrence of
`e` to both branches:

```text
(A_0 multiset-union {e}, B_0 multiset-union {e}).
```

Here `B` is explicitly a family of edge multisets, not simple edge sets.
In 2,016 of the 6,740 raw occurrences, `e` was already present in exactly one
source branch, so that branch contains two occurrences of `e`; the remaining
4,724 additions are new to both branches.  The frozen quotient contains
4,916 representatives.  The common-edge lemma below shows that every
symmetrised function contributed by `B` is already a function contributed by
`F`.

## Statement

The delimited claim/no-claim pair below is the only normative theorem statement in this file.

<!-- G0015_VISIBLE_SCOPE_V1_BEGIN -->
> **Claim (normative):** MAX11 is not in the real span of the registered 16000-raw/9804-class same-component family union the 6740 named beta2-common edge-multiset lifts.
>
> **No-claim (normative):** Does not settle unrestricted MAX11 or exclude cross-component, multi-edge, other pair-atom, asymmetric, or arbitrary finite two-hidden-layer real-weight ReLU-network representations.
<!-- G0015_VISIBLE_SCOPE_V1_END -->

## Ordered-cone normal form

Let

```text
C = { x in R^11 : x_1 <= x_2 <= ... <= x_11 }.
```

For an integer direction `h` with `sum(h)=0`, primitive gcd, and first nonzero
entry positive, write `rho_h(x)=max(0,h dot x)`.  Put
`s_k=h_1+...+h_k`.  If `delta_k=x_(k+1)-x_k`, then on `C`

```text
h dot x = - sum_(k=1)^10 s_k delta_k.
```

Thus `rho_h` vanishes on `C` when every `s_k >= 0`.  Otherwise the
lexicographic sign convention forces the prefix sums to have both signs, so
the hyperplane `h dot x=0` meets the interior of `C`.  These are the active
hinge directions.

For one ordering of the graph vertices from low to high rank, every edge
maximum is the coordinate of its higher-ranked endpoint.  If `d` is the
right-minus-left vector of the resulting two edge sums, then

```text
max(L_A,L_B) = L_A + max(0,d dot x).
```

Writing a nonzero `d` as `g*h` in the chosen orientation gives either
`g*rho_h`, or, after reversing sign,

```text
max(0,-g*h dot x) = -g*h dot x + g*rho_h(x).
```

Summing over all `11!` orderings yields an exact linear-plus-hinges normal
form for every registered five-edge-per-branch atom.  The certificate later
retains only 7,135 active-hinge coordinates from that complete normal form.
Equality of functions would
force equality after this coordinate projection, so infeasibility of the
projected system is already a valid necessary-condition obstruction; the
7,135 rows are not asserted to contain every active direction.  The universal
contribution of the five left edges to
linear rank `r` (zero based) is

```text
5 * 2 * r * 9!.
```

The remaining linear corrections and hinge multiplicities are integer
counts from the ordering histogram.

### Why the coordinates are sound

The active `rho_h` functions, modulo linear functions, are independent on the
interior of `C`.  Consider first the complete finite canonical expansions of
the functions being compared.  For any fixed active `h`, choose a generic
point of `h dot x=0` inside the chamber and outside every other hyperplane
occurring in those complete expansions.  Across that point, only `rho_h` has
a gradient jump, namely a nonzero multiple of `h`.  A linear combination that
vanishes as a function has no jump, so its coefficient at `h` is zero.
Repeating this for every hyperplane leaves a linear function, which must also
be zero.  Consequently equality of the functions forces equality of every
active-hinge and linear coordinate, and hence equality after projecting to
the selected 7,135 hinge coordinates used by `M`.

On `C`, the target has the particularly simple form

```text
11! * MAX11(x) = 11! * x_11.
```

## Exact separating certificate

Let `M` be the frozen `7146 x 9804` integer matrix whose first 7,135 rows are
selected active-hinge coefficients and whose final eleven rows are the linear
coefficients.  Let `b` be zero except for

```text
b[7145] = 11! = 39,916,800.
```

The certificate selects 5,269 rows `i`, their exact positive row gcds `g_i`,
and the final row `f=7145`, whose gcd is `g_f=4`.  Its serialized integers
`n_i` and positive integer `D` satisfy, on every one of the 9,804 columns,

```text
sum_i n_i * (M[i,:] / g_i) + D * (M[f,:] / 4) = 0.       (1)
```

Define the rational row functional

```text
lambda_i = 4*n_i/(D*g_i),   lambda_f = 1,
```

and set every other row weight to zero.  Equation (1) gives
`lambda^T M=0`, while

```text
lambda^T b = 11! != 0.
```

If `b=M*c` for any real coefficient vector `c`, then
`lambda^T b=lambda^T M*c=0`, a contradiction.  Hence the target is outside
the real, and therefore rational, column span.

The common denominator in the primitive serialization has 12,517 bits; the
largest numerator has 12,564 bits.  Their size affects convenience, not the
logical form of the certificate.

## Quotient transport

The atom `Phi_(A,B)` is unchanged by a simultaneous relabelling of its eleven
vertices and by swapping `A` with `B`: the outer sum ranges over all
permutations and `max` is symmetric.  Therefore a correct isomorphism
partition has the same functional span as the raw 16,000-element list.  The
9,804-class partition already passed a separate exact G-0006 audit; G-0014 is
also required to bind the exact representatives used by this matrix.

## Common-edge multiset lemma

For a loopless edge `e={u,v}`, write

```text
h_e(x) = max(x_u,x_v)
```

and let the unsymmetrised atom `phi_(A,B)` be the outer maximum in the
definition of `Phi`.  Appending the same edge occurrence to both branches
gives the pointwise identity

```text
phi_(A multiset-union {e}, B multiset-union {e})(x)
  = h_e(x) + phi_(A,B)(x).                              (2)
```

This remains true when one branch already contains `e`, because its edge sum
counts occurrences.  If

```text
F_2^(11)(x) = sum_{1 <= i < j <= 11} max(x_i,x_j),
```

then every fixed loopless edge occupies every unordered image pair under
exactly `2*9!` permutations.  Summing (2) over `S_11` therefore yields

```text
Phi_(A multiset-union {e}, B multiset-union {e})
  = Phi_(A,B) + 2*9!*F_2^(11).                         (3)
```

The right-hand side is independent of the placement of `e`.  For every raw
member of `B`, choose an old vertex `a` in the same source component and put
`e'={a,11}`.  Appending `e'` to both source branches is a coincident-endpoint
member of `F`, and (3) gives exact pointwise equality between the two
symmetrised atoms.  Hence, over either `Q` or `R`,

```text
span(F union B) = span(F).
```

The standalone G-0018 audit reconstructs all 6,740 mappings, covers all
4,916 `B` quotient representatives, checks the identity by direct
permutation controls for `n=4,5,6,7`, and rejects three hostile mutations.

## Evidence gates

- Exact certificate archive:
  `G-0011/cut_only_exact_left_dual_v1.json.gz`, SHA-256
  `fe6768c8377aa1cc813dbd00805c807d4dd23f05ba246700503aa8598a951758`.
- Fresh-context exact replay: **PASS**, all 9,804 columns, SHA-256
  `9c26c0e6329804ee2a87ec9ef6b86cd935c91551ca503a97409368f41ac3676a`.
  It is a separate implementation but remains same-model-family/same-host
  evidence and therefore is not a T2 review.
  The auditor superseded its first reported bytes only to distinguish the
  51,667,080 relation entries replayed from all 70,059,384 matrix entries
  bound by the content hash; the arithmetic verdict did not change.
- Eleven-prime coefficient comparisons: 57,959/57,959 agree.
- Six hostile certificate mutations: 6/6 rejected.
- Exhaustive clean-implementation graph-to-matrix regeneration: **PASS**,
  all 9,804 columns and 70,059,384 integer entries, with zero mismatched
  columns, entries, or dual-support entries; SHA-256
  `581a8d9b5a1cd28f1ee2896e119a262977084369d32550ca8523fd205596ec71`.
  It reconstructs the raw family, quotient, frozen representatives, and every
  coefficient for the validated frozen direction list.  It does not
  independently rediscover the adaptive provenance of that list, which the
  projection argument does not require.  Its target check is a
  theorem/convention check of the serialization proved above, not an
  independent discovery of the target convention.  It is same-lineage T1
  evidence, not a blind or different-family T2 replication.
- Exact common-edge mapping audit: **PASS**, all 6,740 raw mappings and all
  4,916 quotient representatives, SHA-256
  `88ba04742803439713e3a9fd7c01171c3f6fe3a6edc64b8d99b19c546d4c009d`.
  Its audited script SHA-256 is
  `85b556eeb53584d8541dccd3bc689e4d3347e6153f255427d609e6cabb0dafc1`.
- Modular-obstruction source provenance: **recovered and bound**.  The exact
  historical extractor bytes match their recorded SHA-256 `ccb12f782e...`;
  G-0017 also binds the failed-solve input and every immediate generator hash.
- Git custody: supplied by the release commit containing this theorem and its
  canonical G-0017 bundle specification and verification receipt.
- Different-family or human referee: **not yet obtained**.

## Explicit non-claims

This result does not rule out:

- the named 9,200-raw cross-component lifts, either alone with `F` or as part
  of a broader family;
- lifts with more than one new edge on either side;
- other graph-pair or pairwise-comparison templates;
- nonsymmetric constructions;
- arbitrary finite two-hidden-layer ReLU networks over real weights.

In particular, a diagnostic evaluation found that the present dual is
nonzero on cross-component quotient class 0.  Thus this dual cannot certify
the union with that family; the probe says nothing about whether MAX11 lies
in its span.  The probe result SHA-256 is
`bb5ae0197453a56a1440b9867ec095037938208c9819243133aaaa435144a722`.

It therefore does not settle unrestricted MAX11, the all-`n` conjecture,
width lower bounds, approximation, or trainability.  Its content is an exact
no-go theorem for the registered `F union B` family, with `B` adding no new
symmetrised functions.
