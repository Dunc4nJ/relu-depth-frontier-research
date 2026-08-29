# G-0064 — unrestricted face-gluing obstruction for MAX

## Bottom line

This note proves a necessary condition for **every** finite, arbitrary-real,
two-hidden-layer ReLU representation of `MAX_n`.  It does not assume pairwise
first-layer weights, symmetry of an individual neuron, rational parameters, or
a finite atom catalogue.

After the lossless bias removal and centering from G-0020/G-0022, write an
output-active second preactivation as

\[
q_j(x)=\sum_i b_{ji}\operatorname{ReLU}(w_i^Tx)
      =h_{P_j}(x)-h_{Q_j}(x),
\]

where `P_j,Q_j` are zonotopes, and put

\[
C_j=\operatorname{conv}(P_j\cup Q_j).
\]

If at an input `x` at least three coordinates attain the maximum, then some
output-active second neuron necessarily satisfies both

\[
q_j(x)=0                                                   \tag{1}
\]

and

\[
F_x(C_j)=\operatorname{conv}(F_x(P_j)\cup F_x(Q_j))
\quad\text{is not centrally symmetric}.                  \tag{2}
\]

Here `F_x(K)` is the face of `K` exposed by `x`.  Thus a three-or-more-way MAX
tie cannot be generated solely by first-layer walls or by second neurons that
strictly select one zonotope branch.  A genuinely tied, non-zonotopal outer
branch is mandatory at every such input.

Equivalently, every global MAX11 witness must glue compatible lower-arity
virtual-`P^2` certificates along all simplex faces.  For each of the eleven
ten-vertex facets, face localization recovers a MAX10 certificate, but the
eleven local certificates must arise as faces of one common finite collection
of global zonotope-hull blocks.  This compatibility requirement is absent from
an isolated MAX10 identity and is the precise remaining lift problem.

## Setting

Work in a finite-dimensional real inner-product space `V`.  For a nonempty
compact convex set `K`, define

\[
h_K(u)=\max_{p\in K}\langle u,p\rangle,
\qquad
F_u(K)=\{p\in K:\langle u,p\rangle=h_K(u)\}.
\]

A translated zonotope is a finite Minkowski sum of points and segments.  Let
`S2(V)` consist of finite Minkowski sums of primitive blocks

\[
C=\operatorname{conv}(P\cup Q),                             \tag{3}
\]

where `P,Q` are translated zonotopes.  G-0022 proves the exact unrestricted
equivalence

\[
\operatorname{MAX}_n\text{ has a two-hidden-layer representation}
\iff
\Delta_n^0+A=B\quad(A,B\in S2(H)),                          \tag{4}
\]

for the centered simplex `Delta_n^0` in
`H={x:sum_i x_i=0}`.  Biases and arbitrary real signs are already included in
that equivalence.

## Lemma 1 — exposed-face calculus for a primitive block

For compact convex sets `K,L`,

\[
F_u(K+L)=F_u(K)+F_u(L).                                     \tag{5}
\]

For a primitive block (3), exactly one of the following holds:

\[
F_u(C)=
\begin{cases}
F_u(P),&h_P(u)>h_Q(u),\\
F_u(Q),&h_Q(u)>h_P(u),\\
\operatorname{conv}(F_u(P)\cup F_u(Q)),&h_P(u)=h_Q(u).
\end{cases}                                                 \tag{6}
\]

### Proof

The support of a Minkowski sum is the sum of the supports.  Equality in the
support inequality holds precisely when both summands are exposed, giving
(5).  Also

\[
h_{\operatorname{conv}(P\cup Q)}(u)=\max(h_P(u),h_Q(u)).
\]

If one support value is strict, every maximizer lies in that branch.  If they
are equal, the maximizers are exactly the convex hull of the two exposed
faces.  This proves (6).  In the two strict cases, `F_u(C)` is a face of a
zonotope and is therefore itself a zonotope, hence centrally symmetric. ∎

## Lemma 2 — centrally symmetric terms cannot hide an asymmetric summand

Suppose nonempty compact convex sets satisfy

\[
R+Z_1+\cdots+Z_s=W_1+\cdots+W_t,                             \tag{7}
\]

and every `Z_i,W_j` is centrally symmetric, with arbitrary centers.  Then `R`
is centrally symmetric.

### Proof

If `K` is centrally symmetric about `c_K`, then

\[
h_K(v)-h_K(-v)=2\langle c_K,v\rangle.                        \tag{8}
\]

Apply support functions to (7), subtract the equation at `-v`, and use (8).
The odd part of `h_R` is the linear form

\[
h_R(v)-h_R(-v)
=2\left\langle\sum_jc_{W_j}-\sum_ic_{Z_i},v\right\rangle.
\]

Write the displayed vector as `c`.  Replacing `R` by `R-c`—that is,
translating by the negative of `c`—subtracts the linear form
`\langle c,v\rangle` from its support function, so the translated support
function is even.  An even support function uniquely determines a set equal
to its reflection, so `R-c` is centrally symmetric. ∎

The lemma is stronger and safer than the false shortcut “every Minkowski
summand of a zonotope is a zonotope.”  For example, a triangle and its
reflection sum to a centrally symmetric hexagon; the second summand there is
not centrally symmetric, so it does not satisfy (7)'s hypotheses.

## Theorem 3 — noncentral exposed faces force a tied primitive block

Let

\[
X+A=B,
\qquad
A=\sum_{r=1}^{a}\operatorname{conv}(P_r^0\cup P_r^1),
\qquad
B=\sum_{s=1}^{b}\operatorname{conv}(Q_s^0\cup Q_s^1),        \tag{9}
\]

where every `P_r^e,Q_s^e` is a zonotope.  Fix `u`.  If the exposed face
`F_u(X)` is not centrally symmetric, then at least one primitive block `C`
appearing on either side of (9) satisfies

\[
h_{C^0}(u)=h_{C^1}(u)                                       \tag{10}
\]

and

\[
F_u(C)=\operatorname{conv}(F_u(C^0)\cup F_u(C^1))
\text{ is not centrally symmetric}.                         \tag{11}
\]

### Proof

Apply `F_u` to (9) and use (5):

\[
F_u(X)+F_u(A)=F_u(B).                                       \tag{12}
\]

If every primitive exposed face on both sides were centrally symmetric, then
their Minkowski sums `F_u(A)` and `F_u(B)` would be centrally symmetric.
Lemma 2 applied to (12) would force `F_u(X)` to be centrally symmetric, a
contradiction.  Hence some primitive exposed face is not centrally symmetric.
By Lemma 1, a strict branch choice always exposes a zonotope face and is
centrally symmetric.  The offending primitive must therefore satisfy the tie
(10), and (6) gives exactly (11). ∎

This theorem is invariant under translations, arbitrary positive scalings,
and moving a term between the two sides of (9).  It therefore applies to
arbitrary real output weights after positive and negative terms are grouped.

## Corollary 4 — every three-way MAX tie activates a genuine outer tie

Let a finite bias-free two-hidden-layer network compute `MAX_n` exactly.  Let

\[
S(x)=\{i:x_i=\operatorname{MAX}_n(x)\}.
\]

If `|S(x)|>=3`, then an output-active second neuron satisfies (1) and (2).

### Proof

Project the network to `H` as in G-0022.  For each second neuron, split the
incoming coefficients into positive and negative parts.  This gives zonotopes
`P_j,Q_j` and the exact identity

\[
\operatorname{ReLU}(q_j)=h_{C_j}-h_{Q_j},
\qquad C_j=\operatorname{conv}(P_j\cup Q_j).                  \tag{13}
\]

Grouping positive and negative output weights produces (9) with
`X=Delta_n^0`.  At input `x`,

\[
F_x(\Delta_n^0)=
\operatorname{conv}\{e_i-\mu:i\in S(x)\}.                    \tag{14}
\]

This is a simplex of dimension `|S(x)|-1`.  A `d`-dimensional centrally
symmetric polytope has at least `2d` vertices: after translating its center to
zero, vertices occur in antipodal pairs, and at least `d` of those pairs are
needed to span a `d`-dimensional space.  A `d`-simplex has only `d+1<2d`
vertices for `d>=2`, so the face in (14) is not centrally symmetric.

Theorem 3 therefore supplies a noncentral `C_j` face.  Pure carrier summands
`Q_j=conv(Q_j\cup Q_j)` have zonotopal faces, so the noncentral block comes
from an output-active `C_j`.  Its branch-support tie says

\[
h_{P_j}(x)-h_{Q_j}(x)=q_j(x)=0,
\]

and (11) gives (2). ∎

For `d=1` a segment is centrally symmetric.  This is why the theorem begins at
a three-way tie, not a two-way tie.

## Corollary 5 — continuum coverage of every simplex-face normal cone

For every subset `S subseteq [n]` with `3<=|S|<=n-1`, define the relative-open
tie cone

\[
\mathcal C_S=\{x:x_i=x_j>x_\ell\text{ for all }i,j\in S,
\ \ell\notin S\}.                                            \tag{15}
\]

If `q_1,...,q_m` are the output-active second preactivations of an exact
network, then

\[
\mathcal C_S\subseteq\bigcup_{j=1}^m\{x:q_j(x)=0\}.           \tag{16}
\]

Because every `q_j` is continuous and the union is finite, the Baire-category
theorem applied in the affine span of `C_S` implies that for each `S`, at least
one `q_j` vanishes on a nonempty relatively open subset of `C_S`.  Thus the
coverage cannot be achieved only by finitely many transverse, accidental
zero crossings: some second preactivation must be identically zero on a full
polyhedral patch of every face-normal cone.

For MAX11 there are

\[
\sum_{k=3}^{10}\binom{11}{k}=1980                            \tag{17}
\]

proper simplex faces to which this applies.  Width is unrestricted, so (17)
is not by itself a neuron lower bound; one symmetric orbit can cover many
faces.  It is a global compatibility requirement, not a counting proof.

## Corollary 6 — face localization and the MAX10 gluing problem

Taking the exposed face of (4) gives

\[
F_x(\Delta_n^0)+F_x(A)=F_x(B).                               \tag{18}
\]

Faces of zonotopes are zonotopes, and (6) shows that a face of a primitive
`S2` block is again an `S2` block (a strict branch is included by using the
same zonotope twice).  After translating all faces into `x^perp`, (18) is a
virtual-`S2` certificate for the simplex on the maximizer set `S(x)`.

Consequently, every MAX11 certificate induces a MAX10 certificate on each
cone where exactly ten coordinates tie above the eleventh.  The eleven
induced certificates are not independent: every local zonotope face must be
a face of the same global zonotope.  If a global zonotope has generators
`g_r in H`, then at the facet direction opposite coordinate `i`, its exposed
face retains exactly those generators with

\[
\langle g_r,\mu-e_i\rangle=-g_{r,i}=0.                       \tag{19}
\]

All other generators contribute only a selected endpoint translation on that
facet.  Equation (19) is the concrete gluing rule.  A viable positive lift
must construct global generator multisets whose eleven zero-coordinate
restrictions reproduce compatible MAX10 face blocks while additional walls
cancel away from those facets.

This explains why simply summing eleven coordinate-deletion MAX10 identities
fails: it ignores the common-face compatibility and introduces no mechanism
for cancelling the extra global walls.

## Separate decisive no-go — signed sums of dense MAX10 compositions

A tempting asymmetric class is

\[
\operatorname{MAX}_{11}(x)\stackrel?=\sum_r c_r
\operatorname{MAX}_{10}(L_rx)+\ell(x).                       \tag{20}
\]

It is impossible.  Each term `MAX10(L_r x)` is the support function of the
convex hull of the ten rows of `L_r`, which has affine dimension at most nine
in the ten-dimensional centered space.  Grouping arbitrary positive and
negative real coefficients turns (20) into a signed Minkowski combination of
lower-dimensional polytopes.  Rueß et al., Proposition 4.2, citing Koutschan
et al., Corollary 5.2, proves that a `d`-simplex is not a signed Minkowski
combination of lower-dimensional polytopes (it is not a zero summand).
Translations and the linear term only translate the row polytopes and do not
alter this obstruction.

Local primary-source custody for that step:

- `literature/papers/2607.21651.pdf`, SHA-256
  `0a4def828040e0c17cf02e654b3ea76e85d17da14c207589ed0fee8a1c8ecd56`,
  Proposition 4.2; extracted-text SHA-256
  `a92c482f9e5a11fb1b0b54dc6945e410f83cfd84a00382ee2bcc7d692b817d0a`,
  local lines 453--463.
- `literature/papers/2305.16933.pdf`, SHA-256
  `f2d58f699b858aa6d24b7022f2ac0f233079554c3c20b8032e888eb631c569bb`,
  Corollary 5.2; extracted-text SHA-256
  `5c552b3b3eaa6b439077202681b80eed6ee0e304821924f936f5310959730c80`,
  local lines 638--646.

Thus dense linear maps do not rescue a composition-only MAX10 lift.  A
successful construction must use genuinely full-dimensional primitive blocks
`conv(Z0 union Z1)` and their cross-wall cancellation.

## Relationship to prior campaign results

- G-0020 removes biases from a representation of the positively homogeneous
  target without changing its two widths.
- G-0022 proves the unrestricted virtual-polytope equivalence and the local
  projective wall-cancellation law.  The result here is different: it uses the
  **shape of the whole exposed subgradient face** and detects higher-order
  MAX ties that a scalar codimension-one jump does not.
- G-0031 proves that the canonical winner cells cannot stay in their original
  fan.  Corollary 6 identifies the corresponding global lift compatibility:
  new walls are allowed, but their eleven facet restrictions must come from
  common global zonotopes.
- G-0060 proves that standard Boolean-cube output values cannot obstruct an
  unrestricted-width network.  The present theorem is genuinely global and
  parameter-coupled: it constrains a continuum of tie cones and the shared
  subgradient polytopes.

## Claim boundary

- This is a necessary condition, not a MAX11 representation or impossibility
  theorem.
- It does not bound unrestricted width: a neuron orbit may satisfy many of the
  1,980 face obligations.
- It does not claim that every collection of locally compatible MAX10 faces
  extends to a global block; that extension problem is the next constructive
  gate.
- It does not make the finite pair-atom catalogue complete.
- The dense-MAX10 no-go applies only to linear combinations of composed
  `MAX10` functions.  It does not exclude full-dimensional second-layer
  zonotope-hull blocks.
- Novelty has not been adjudicated, and no priority claim is made.

## Falsifiers

The proof is false if any of the following exists:

1. a primitive block with strict branch support at `u` but a non-zonotopal
   exposed face;
2. an equality `R+Z=W` with `Z,W` centrally symmetric and `R` not centrally
   symmetric;
3. a two-hidden-layer MAX network and a point with at least three maximal
   coordinates at which every output-active second preactivation is nonzero;
4. a dense-MAX10 identity (20) whose row polytopes all have dimension at most
   nine, contradicting the cited zero-summand theorem.

Items 1 and 2 are ruled out by Lemmas 1 and 2.  Item 3 is the direct network
counterexample target for an adversarial audit.  Item 4 must be treated as
source-dependent until the cited theorem is independently statement-matched.
