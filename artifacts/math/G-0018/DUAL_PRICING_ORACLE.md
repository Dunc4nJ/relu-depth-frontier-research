# Exact pricing oracle for the G-0011 left dual

## Executive conclusion

For an arbitrary loopless pair atom with five edges in each branch on eleven
vertices, do **not** construct its complete direction histogram.  The fastest
exact route I can presently justify is a split-6 meet-in-the-middle computation
using two small tries:

1. propagate only dual-relevant prefixes of length six by subset DP;
2. for each six-vertex prefix set, propagate only dual-relevant suffixes of
   length five;
3. join the two counts through the 17,908 raw words that can hit the 5,267
   hinge coordinates in the exact dual;
4. compute the three supported linear coordinates with a separate three-state
   subset DP;
5. screen with a 61-bit prime, and form the exact 12.6-kilobit integer dot
   product only for modular survivors.

The fixed tries have 2,587 prefix nodes and 8,181 suffix nodes.  A conservative
combinatorial bound is 397,111 prefix transitions plus 150,150 suffix
transitions per signed graph, before terminal-list checks.  This is materially
smaller than constructing every direction word and is suitable for a compiled
Rust/C++ oracle.  A Python implementation may be useful for certification and
tests, but it is not a credible way to price millions of unrelated graphs.

There is also an exact collapse that should be exploited before any pricing:
for fixed branch size five, the symmetrised atom depends only on the signed
difference graph `B-A`.  Thus common-edge placements and isomorphic signed
graphs share one price.

## Correction to the support description

The G-0011 certificate is not supported on 5,269 hinge rows.  Its 5,269 pivot
rows consist of:

- 5,267 selected hinge rows;
- linear rank 1 (matrix row 7136), with primitive-row divisor 725,760;
- linear rank 3 (matrix row 7138), with primitive-row divisor 20,160.

The failing row is linear rank 10 (matrix row 7145), with divisor 4.  Ranks are
zero-based.  Any pricing implementation that omits ranks 1 and 3 evaluates a
different functional.

## Denominator-free exact normalization

Write the serialized common denominator as `q`, the pivot numerators as
`N_i`, their primitive-row divisors as `g_i`, and the failing-row divisor as
`g_f=4`.  G-0011 proves

```text
sum_i N_i (row_i / g_i) + q (row_7145 / 4) = 0
```

on all 9,804 frozen columns.  The least common multiple of every `g_i` and 4
is only

```text
L = 3,628,800 = 10!.
```

Therefore use the integer functional

```text
Omega(c) = sum_i [N_i (L/g_i)] row_i(c) + [q (L/4)] row_7145(c).
```

This is exact on an arbitrary new integer column.  It does **not** assume that
the old row gcd `g_i` divides the corresponding coordinate of the new column.
The largest fixed coefficient is about 12,584 bits.  Modular weights are
obtained simply by reducing these integer coefficients; no modular inverse is
needed.

## Atom semantics and the signed graph collapse

Let `A` and `B` be the two five-edge branches and let

```text
W_uv = 1_{uv in B} - 1_{uv in A}.
```

For an ordering `pi=(v_0,...,v_10)`, define its signed back-degree word

```text
w_r(pi) = sum_{s<r} W_{v_r,v_s}.
```

The branch difference on the ordered chamber has coefficient word `w(pi)`.
For nonzero `w`, let `k=gcd(|w_0|,...,|w_10|)` and orient `w/k` so its first
nonzero entry is positive.  That ordering contributes `k` to the corresponding
primitive hinge coefficient.  Hence, for a selected primitive direction `d`,

```text
h_d(A,B) = sum_{pi: orient(w(pi))=d} gcd(w(pi)).
```

The hinge part plainly depends only on `W`.  The linear base does too, apart
from a universal term.  If `a_r(pi)` is the A-branch back degree at rank `r`,
then

```text
ell_r = sum_pi [a_r(pi) + 1_{first_nonzero(w(pi))<0} w_r(pi)]
      = 10 r 9! + sum_{pi: first_nonzero(w(pi))<0} w_r(pi).
```

The equality `sum_pi a_r(pi)=10 r 9!` uses only that `A` contains five
loopless edges: each edge has `2 r 9!` orderings whose later endpoint is at
rank `r`.  Consequently the entire normal-form column, and thus `Omega`, is a
function only of the signed graph `W` when both branch sizes are five.

Practical consequence: canonicalise `W` under vertex relabelling and global
sign reversal, then cache its price.  Pair graphs differing only by common
edge placement should never be priced twice.

## Relevant raw words

Every back-degree coordinate lies in `[-5,5]`.  For each supported primitive
direction `d`, the only raw words that can contribute are

```text
+k d and -k d,  1 <= k <= floor(5 / ||d||_infinity).
```

The 5,267 supported hinge directions have the following infinity-norm census:

| `||d||_infinity` | directions |
|---:|---:|
| 1 | 262 |
| 2 | 2,639 |
| 3 | 1,876 |
| 4 | 443 |
| 5 | 47 |

Thus there are exactly

```text
2 (5*262 + 2*2639 + 1876 + 443 + 47) = 17,908
```

distinct signed raw terminal words.

Split a word after coordinate 5, so the prefix has length six and the suffix
has length five.  Direct reconstruction from the frozen support gives:

- prefix-trie level sizes: `1, 1, 11, 35, 125, 501, 1913`;
- suffix-trie level sizes: `1, 11, 91, 511, 2143, 5424`.

The corresponding node totals are 2,587 and 8,181.  Each suffix terminal
stores a short list of triples `(prefix_node, hinge_index, k)`.

## Split-6 bidirectional trie algorithm

Precompute the signed subset sums

```text
inc[v][mask] = sum_{u in mask} W_vu
```

in `O(n 2^n)` time and about 22--45 KiB using signed 8- or 16-bit entries.

### Prefix phase

Maintain counts on `(mask, prefix_trie_node)`, starting with
`(0,root) -> 1`.  At depth `r<6`, transition through every `v` outside `mask`
using label `inc[v][mask]`.  Discard the transition if the trie has no child
with that label.  Equal states are added.  At depth six, retain the map

```text
P_S[p] = number of orderings of S producing relevant prefix p
```

for every six-set `S`.

### Suffix phase and join

For each six-set `S`, start `(mask=S, suffix_root) -> 1`.  Add the five
remaining vertices in every order, again following only existing suffix-trie
edges labelled by `inc[v][mask]`.  At a suffix terminal `q` with multiplicity
`Q_S[q]`, visit its metadata list.  For each `(p,d,k)`, add

```text
k * P_S[p] * Q_S[q]
```

to hinge coordinate `h_d`, or multiply it immediately by the fixed modular
dual weight when only a modular price is requested.

### Pseudocode

```text
price(W):
    inc = signed_subset_sums(W)

    prefix[0][root] = 1
    for depth in 0..5:
        for (mask,node,count) in prefix[depth]:
            for v notin mask:
                child = prefix_trie.child(node, inc[v][mask])
                if child exists:
                    prefix[depth+1][mask|bit(v),child] += count

    hinge[0..5266] = 0
    for each six-set S:
        suffix[(S,root)] = 1
        for suffix_depth in 0..4:
            advance suffix states with the same labelled transition rule
        for (terminal,count_q) in suffix terminals:
            for (prefix_node,d,k) in terminal.metadata:
                count_p = prefix[6].get((S,prefix_node), 0)
                hinge[d] += k * count_p * count_q

    ell_1, ell_3, ell_10 = linear_sign_dp(inc)
    return integer_dot(Omega_weights, hinge, ell_1, ell_3, ell_10)
```

### Operation and memory bounds

At prefix depth `j`, a state count is bounded by

```text
C(11,j) * min(j!, number_of_relevant_prefixes_at_depth_j).
```

For depths zero through six these bounds are

```text
1, 11, 110, 990, 7920, 55440, 332640.
```

The resulting bound for transitions through depth six is 397,111.  For a
fixed six-set the five-vertex suffix DP has at most
`1,5,20,60,120,120` states by depth and at most 325 transitions.  Across all
462 six-sets this is 150,150 suffix transitions.  Terminal lists have mean
length about 3.3 and maximum length 31; the absolute crude bound is therefore
about 1.72 million terminal-entry checks, with a much smaller expected count.

All hinge multiplicities fit signed 32-bit arithmetic:
`h_d <= 5*11! = 199,584,000`.  Use 64-bit counters anyway.  A packed compiled
implementation needs only a few tens of MiB, dominated by prefix states and
hash/sort workspace; the fixed tries and 17,908 terminal records are small.

## The supported linear rows in `O(n 2^n)`

The trie deliberately discards words irrelevant to the hinge support, so it
cannot by itself recover the linear correction.  Use a separate DP with sign
state `s in {zero, positive, negative}`, recording the sign of the first
nonzero word coordinate.

Let `C[mask,s]` count ordered prefixes with vertex set `mask` and sign state
`s`.  On adding `v` at rank `r=|mask|`, set `z=inc[v][mask]`, update the sign
state if it is still zero, and propagate the count.  For each required rank
`r in {1,3,10}`, whenever the new sign state is negative, add

```text
C[mask,s] * z * (10-r)!
```

to the correction at rank `r`; the factorial counts arbitrary completions.
Finally add the universal base `10 r 9!`.  This costs three scalar states per
mask and is negligible beside the trie computation.

As a useful check, rank 1 has the closed form

```text
ell_1 = 2 |A intersection B| 9!.
```

## Modular-first and exact-survivor modes

For a broad scan, reduce the integer-scaled `Omega` weights modulo a 61-bit
prime and accumulate the scalar price directly at terminal joins.  A nonzero
residue is an exact proof that the rational price is nonzero.  Recheck modular
zeros with another prime and then compute their exact feature vector and
12.6-kilobit integer dot product.

If every member of a named family is expected to be annihilated, generate the
small integer feature matrix once and replay the exact big-integer row-vector
product in blocks, as G-0011's verifier already does.  Alternatively, a CRT
zero proof needs roughly 12.6 kilobits of modulus after a rigorous coefficient
bound, so direct `fmpz` replay is probably simpler.

For millions of raw pair graphs, the essential pre-pass is signed-graph
canonicalisation and caching.  Without that collapse, even a sub-million-op
oracle per object is expensive.  In compiled code, a reasonable unbenchmarked
expectation is single-digit to tens of milliseconds per *new signed graph*;
Python is likely hundreds of milliseconds or worse.  These are engineering
estimates, not measured performance claims.

## Why I do not see a substantially smaller algebraic transform

The dual is dense and arithmetically irregular: every one of its 5,267 hinge
numerators is nonzero and the coefficients are about 12.5 kilobits.  The
split-6 terminal incidence matrix has shape `1913 x 5424`, 17,908 nonzeros,
and structural rank 1,797 (maximum bipartite matching).  Structural rank is
not the actual arithmetic rank, but it says that sparsity alone does not
offer a small low-rank factorisation; generic weights with this support have
rank 1,797.  A low-rank bilinear transform would therefore be much less
attractive than the sparse terminal join unless a new exact identity is
found.

More conceptually, the terminal weight is an essentially arbitrary function
of the full eleven-coordinate elimination word.  The next coordinate depends
on the actual earlier vertex subset, not just its size.  That is why a scalar
`2^n` DP is unavailable without either a small automaton or a separable weight
function.  The two tries are the useful automaton; I found no evidence for a
meaningful further state collapse.

## Consequences for G-0009

### Beta2 common-edge family: exact annihilation, no sample needed

Here is the exact function lemma, without relying on the signed-graph normal
form.  Put `h_ij(x)=max(x_i,x_j)` and

```text
phi_(A,B)(x) = max(sum_(a in A) h_a(x), sum_(b in B) h_b(x)),
Phi_n(A,B)(x) = sum_(sigma in S_n) phi_(sigma A,sigma B)(x).
```

For any pair of edge multisets `A_0,B_0` and any fixed loopless edge `e`,

```text
phi_(A_0+e,B_0+e) = h_e + phi_(A_0,B_0)
```

pointwise, because `max(U+h,V+h)=h+max(U,V)`.  After summing over all
permutations, each unordered target edge is the image of `e` under exactly
`2(n-2)!` permutations: choose which endpoint of `e` maps to which target
endpoint and permute the other `n-2` vertices.  Therefore

```text
Phi_n(A_0+e,B_0+e)
  = Phi_n(A_0,B_0) + 2(n-2)! F_2^(n),
F_2^(n) = sum_(1<=i<j<=n) h_ij.
```

At `n=11` the added term is exactly `2*9!*F_2^(11)`, independent of `e`.
The lemma permits `e` to coincide with an edge already present in one source
branch: edges are occurrences in a multiset, and adding the same new
occurrence to both branch sums is all the pointwise proof uses.

Every G-0009 beta2 atom has form `(A_0+e, B_0+e)` for one of the 252 source
bases.  For the same source base, G-0008 contains a same-component lift with
coincident endpoints,

```text
(A_0+{a,11}, B_0+{a,11}),
```

because its generator loops independently over both endpoints in a component
and does not require them to differ.  Taking `a` to be the smallest vertex in
the first stored component gives one deterministic G-0008 witness per source
base.  The lemma makes the beta2 atom and this G-0008 atom pointwise equal
after full symmetrisation.

The source/filter assumptions were checked directly against the frozen
generators:

- all 252 source bases have four edges per branch;
- their eight union edges are distinct and loopless;
- their active vertex set is exactly `{1,...,10}` and is partitioned into
  exactly two stored components;
- G-0008 contains exactly ten coincident-endpoint raw lifts per source base,
  one for every active vertex;
- G-0009 beta2 metadata covers all 252 and only those source-base indices;
- choosing the first-component minimum maps the 252 bases to 252 distinct raw
  G-0008 items and 252 distinct frozen G-0008 graph classes;
- all 6,740 raw beta2 atoms have exactly the same signed adjacency and branch
  sizes as their fixed source-base witness.

Since G-0011 annihilates every G-0008 column, it annihilates every beta2-common
column exactly.  This is also a direct corollary of G-0009's proved identity

```text
Phi_N(A+e,B+e) = Phi_N(A,B) + 2(N-2)! F_2^(N),
```

whose added term is independent of the common edge's placement.

This proves the global pointwise inclusion

```text
{beta2-common functions} subset {G-0008 functions},
span_Q(G-0008 union beta2-common) = span_Q(G-0008),
```

and the same equality over `R`.  It is stronger than the old 886-row rank
observation.  Consequently the G-0011 no-go, with its unchanged nonzero target
pairing, extends immediately to the union of the G-0008 family and all 4,916
beta2-common quotient classes.  It does not extend to the cross family.

An artifact-level mapping audit should serialize, for every one of the 6,740
beta2 raw records, its source-base index, the deterministic coincident-endpoint
G-0008 raw index, and that raw index's frozen G-0008 class.  The verifier should
reconstruct both pairs from the pinned certificate, check the source branches,
branch sizes, signed adjacency, class lookup, and all census statements above.
It should also hash the 6,740-entry map and independently compare a sample of
full normal-form columns.  The algebraic lemma is the equality authority; the
column comparisons are convention/mapping controls rather than the proof.

That lightweight audit has now been implemented and passed:

- standalone script: `artifacts/math/G-0018/audit_beta2_union_mapping.py`,
  SHA-256 `85b556eeb53584d8541dccd3bc689e4d3347e6153f255427d609e6cabb0dafc1`;
- canonical result: `artifacts/math/G-0018/beta2_union_mapping_audit_v1.json`,
  SHA-256 `88ba04742803439713e3a9fd7c01171c3f6fe3a6edc64b8d99b19c546d4c009d`;
- canonical 6,740-record mapping payload SHA-256
  `891c48572318a6396786023349fa4358dfc6beeef515137836bd1d465afb100e`.

It imports no local evaluator or enumerator, reconstructs both raw families
directly from the pinned certificate, binds their byte-level metadata and pair
digests to the frozen quotient artifacts, independently rechecks the 252
witness graph classes, and runs direct permutation controls for `n=4,5,6,7`.
All 6,740 mappings passed.  Mutants with an edge added to only one branch, a
loop edge, or a mismatched source base were all rejected.  The distinct-class
count is a diagnostic; the pointwise common-edge lemma and the exhaustive
source-preserving map are the premises of the span corollary.

### Cross-component family: genuinely unresolved

The cross family has no corresponding common-edge collapse.  Its signed
support is a full tree, while the same-component constructions have different
topology.  The huge interpolatory-looking dual gives no positive reason to
expect universal annihilation, so my prior leans toward finding a nonzero
cross price.  Confidence should remain low: G-0009 found zero cross rank gain
over the same baseline on both its orbit and adaptive held-out finite systems.

The cheapest decisive falsification has now been run on exactly one
deterministic representative: cross quotient class 0.  Its regenerated
7,146-entry column has SHA-256
`5697f88247c4f2f77c408dbbe3bb67532f5742b9196cb805286a0df8318ce263`.
The denominator-free exact price is negative and nonzero (12,580 bits); an
independently accumulated reduction modulo `2^61-1` agrees and equals
`1755775690469619915`.  Therefore the current G-0011 dual does **not**
annihilate the G-0008-union-cross family.

The scope is deliberately only that conclusion.  This does not determine
whether MAX11 lies in the union span, does not prove that another separator
does or does not exist, and is not a scan of the 3,615 cross quotient classes.
The single-process run was externally capped at 4 GiB and peaked at 154,988
KiB RSS.  Frozen artifacts:

- evaluator/probe SHA-256
  `7cde60263a7065229781c1c73c273869b5a05f3906a1d40adf76a3e7d60b5c65`;
- canonical result SHA-256
  `bb5ae0197453a56a1440b9867ec095037938208c9819243133aaaa435144a722`.

This closes only the route “reuse the present separator unchanged for
G-0008 union cross.”  A broader-family result now requires a new exact dual
or a direct membership computation; exhaustive pricing of this family with a
functional already known not to annihilate it would add no theorem evidence.

## Minimal independent validation plan

1. Generalise the trie engine to `n<=7` and compare every output coordinate
   against brute permutation enumeration on random and adversarial signed
   graph pairs.
2. On `n=11`, compare the 5,267 hinge values and linear ranks 1, 3, 10 for at
   least three frozen G-0008 representatives against
   `cut_matrix_01_02_03_04.npz`, including low- and high-support columns.
3. Check that the exact integer price is zero on those controls and that the
   target pairing remains nonzero.
4. Relabel vertices and swap A/B; both the feature vector and price must remain
   unchanged.
5. Include mutants that omit the raw-word gcd, include only `+kd`, or omit the
   rank-1/rank-3 linear rows; each must fail a frozen comparison.
6. Check a base atom with two different common-edge placements.  Their full
   compact feature vectors must agree, certifying the beta2 collapse in the
   implementation as well as algebraically.

This oracle would accelerate exact evaluation of the existing restricted
pair-atom ansatz.  It does not enlarge the theorem's claim boundary to
unrestricted MAX11 or unrestricted two-hidden-layer ReLU networks.
