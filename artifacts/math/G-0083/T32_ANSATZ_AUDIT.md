# G-0083 — exact audit of low-degree routes for \(T_{3,2}\)

## Standing and no-claim boundary

This is a same-family derivation note.  It has not received an independent
proof review, and its novelty has not been audited beyond the cited local
corpus and a narrow primary-literature search.  It proves no representation
of \(T_{3,2}\), \(J_7\), or MAX11, and no unrestricted depth lower bound.

The useful outputs are:

1. an exact obstruction to every atom dictionary built only from the eight
   obvious primitive functions of \(T_{3,2}\);
2. an exact affine-rank test that any surviving degree-five atom must meet at
   least once in a certificate; and
3. a correction to a proposed ten-chamber exact-linear-algebra reduction.

## The target polytope is not a zero-summand

Write

\[
 K=Q_1*Q_2*Q_3*\{a\}*\{b\},
\]

where each \(Q_i\) is a square and \(*\) denotes join.  This is the Newton
polytope of

\[
 T_{3,2}=\max(q_1,q_2,q_3,a,b).
\]

The factors occupy independent join subspaces, so

\[
 \dim K=\sum_i\dim Q_i+(5-1)=6+4=10.
\]

For each square choose an edge \(E_i\) and its opposite edge \(E_i'\).
The face lattice of a join is the join of the factor face lattices.  More
explicitly, extend a supporting functional of \(E_1\subset Q_1\) so that it
has value zero on \(E_1,Q_2,Q_3,a,b\) and negative value on the rest of
\(Q_1\).  Its maximum and minimum faces on \(K\) are

\[
 K_1=E_1*Q_2*Q_3*a*b,\qquad E_1',
\]

respectively.  Here \(K_1\) is a nine-dimensional facet and \(E_1'\) has zero
volume in the facet ambient space.  If \(K\) were a zero-summand, Koutschan
et al. Lemma 5.1 would make \(K_1\) a zero-summand.  Repeating inside that
facet for \(Q_2\), and then for \(Q_3\), gives successively

\[
 K_2=E_1*E_2*Q_3*a*b,\qquad
 K_3=E_1*E_2*E_3*a*b.
\]

At each step the opposite face is an edge, hence has zero volume in the new
facet ambient space.  Thus the hypothetical zero-summand property descends
to \(K_3\).  But \(K_3\) is seven-dimensional and has
\(2+2+2+1+1=8\) affinely independent vertices.  It is a 7-simplex, which is
not a zero-summand by Koutschan et al. Corollary 5.2.  Contradiction.

Therefore

\[
 \boxed{K\text{ is not a zero-summand}.}
\]

This argument is a direct specialization of the cited face obstruction; an
external novelty claim is not made.

Primary locator: `literature/papers/2305.16933.txt`, lines 587--646.

## Fatal obstruction to the eight-primitive ansatz

The eight natural first-layer functions are the six coordinate-pair maxima
whose sums form \(q_1,q_2,q_3\), together with the linear functions \(a,b\).
The Newton polytopes of the first six are segments with six independent
directions; those of \(a,b\) are points.  Let \(U\) be the common six-
dimensional span of those segment directions.

Any convex branch obtained as a nonnegative sum, with arbitrary repetitions
and padding, of these eight primitives has a zonotope

\[
 Z_A\subset z_A+U.
\]

For two such branches,

\[
 \operatorname{conv}(Z_A\cup Z_B)
 \subset z_A+\operatorname{span}(U,z_B-z_A),
\]

so every corresponding rank-two atom has dimension at most seven.  This
bound is independent of the nominal degree: repetitions, affine terms, and
zero or diagonal padding add no segment direction outside \(U\).

Allowing arbitrary signed second-layer weights does not evade the argument.
Split any first-layer linear combination into positive and negative parts,
\(g=h_P-h_N\), where both \(P\) and \(N\) are translates of zonotopes with
directions in \(U\).  Then

\[
 \operatorname{ReLU}(g)
 =\max(h_P,h_N)-h_N
 =h_{\operatorname{conv}(P\cup N)}-h_N,
\]

and the two polytopes on the right have dimensions at most seven and six.
Additional affine-linear terms only translate these polytopes.  If affine
biases are allowed, apply the alleged identity at \(\lambda x\), divide by
\(\lambda\), and let \(\lambda\to\infty\); all biases disappear and the same
homogeneous representation remains.
Thus, if a signed combination of these unit outputs equalled \(h_K\),
grouping positive and negative coefficients would express \(K\) as a
Minkowski difference of zero-volume polytopes.  That would make \(K\) a
zero-summand, contradicting the preceding lemma.  Hence

\[
 \boxed{\text{No dictionary using only the eight natural primitives can
 represent }T_{3,2}.}
\]

This strictly contains the degree-five proposal that used multisets of the
eight primitives.  It is distinct from the earlier black-box-square no-go:
the present proof allows arbitrary degree and also allows the \(a,b\) point
factors to be combined or padded; the killer is the common six-dimensional
direction span.

The same proof gives a useful unrestricted necessary condition, with an
important hypothesis on what “direction rank” means.  Let \(P\) be a
full-dimensional, non-zero-summand \(d\)-polytope.  Restrict an alleged
two-hidden-layer representation of \(h_P\) to its effective
\(d\)-dimensional Newton coefficient space and take its recession function.
Separate free affine-linear terms from the first-layer hinge normal form.
Assume every second-layer preactivation has the form

\[
 g(x)=\ell(x)+\sum_s c_s\operatorname{ReLU}(\langle u_s,x\rangle),
 \qquad u_s\in U,
\]

for one common direction space \(U\) of dimension \(r\).  Splitting the
positive and negative \(c_s\) gives zonotopes \(Z_+,Z_-\) with directions in
\(U\), while \(\ell\) translates one branch.  Thus

\[
 \operatorname{ReLU}(g)
 =h_{\operatorname{conv}(t+Z_+,Z_-)}-h_{Z_-}
\]

for a translation vector \(t\).  The two polytopes have dimensions at most
\(r+1\) and \(r\).  If \(r\le d-2\), all such summands have zero volume, so
the output identity would make \(P\) a zero-summand.  Therefore

\[
 \boxed{r\ge d-1.}
\]

For \(T_{3,2}\), any exact two-hidden-layer representation must consequently
have projected first-layer **hinge-direction** rank at least nine after
affine terms are separated.  This is not the raw rank of a chosen weight
matrix (canceling ReLU pairs can encode affine functions), and it is not a
width lower bound: arbitrarily many collinear hinge directions still
contribute rank one.

## Exact rank filter for a viable degree-five atom

Expand the three square factors into their twelve vertices and append the
two point factors.  Let the resulting affine configuration be
\(V=\{v_1,\ldots,v_{14}\}\), of affine rank ten.  A degree-five branch is
specified by five (possibly repeated or diagonal) unordered pairs.  After
orienting them arbitrarily, write

\[
 Z_A=\sum_{(u,v)\in A}[v_u,v_v]
     =z_A+\sum_{(u,v)\in A}[0,v_v-v_u]
\]

and set \(D_A=\{v_v-v_u:(u,v)\in A\}\); define \(z_B,D_B\) similarly.
Then the associated atom \(R_{A,B}=\operatorname{conv}(Z_A\cup Z_B)\)
satisfies the exact formula

\[
 \dim R_{A,B}
 =\operatorname{rank}\bigl(D_A\cup D_B\cup\{z_B-z_A\}\bigr).
\]

Consequently a full-dimensional degree-five atom must obey

\[
 \operatorname{rank}\bigl(D_A,D_B,z_B-z_A\bigr)=10.
\]

Since each branch has rank at most five, this forces
\(\operatorname{rank}D_A+\operatorname{rank}D_B\ge9\).  It does **not**
force rank five on both sides: ranks four and five can work if their union
has rank nine and the branch offset supplies the tenth direction.

Because \(K\) is not a zero-summand, every degree-five certificate must
contain at least one atom passing this full-dimensional test.  The inference
stops there.  Rank-deficient atoms can still be necessary correction terms;
discarding all of them would make a reduced search incomplete unless a
separate span-redundancy theorem is proved.

## A minimal full-dimensional subclass that survives

There is a small, exact source of atoms passing the test.  In each square,
choose a base vertex and the two incident perimeter edges.  These give the
six independent internal square directions.  On the five factor nodes
\(Q_1,Q_2,Q_3,a,b\), choose a tree and realize each of its four edges as a
segment between the chosen factor basepoints.  Modulo the six-dimensional
internal span, the four tree directions form a basis of the four-dimensional
join quotient.  Thus all ten segment directions are independent.

Partition these ten edges into two sets of five.  Each branch zonotope then
has rank five, and their convex hull is ten-dimensional.  This gives a
finite, symmetry-stable **candidate** family of minimal-basis atoms that cuts
inside squares and couples factors.  No coefficient identity has been found,
and no completeness is claimed.  Geometrically, each choice selects an
11-vertex affine basis of \(K\); this close relationship to a 10-simplex also
explains why the family is not automatically easier than MAX11.

## Why ten chambers are not enough

The natural automorphism group is

\[
 H=(D_8^3\rtimes S_3)\times S_2,
 \qquad |H|=8^3\cdot6\cdot2=6144.
\]

A generic fundamental cone can orient the two endpoint pairs in every
square, order their two gaps, impose \(q_1\le q_2\le q_3\), and impose
\(a\le b\).  On it, each square's four expanded vertex forms make a chain,
and the three ordered top values can be interleaved with \(a\le b\) in ten
ways.  These ten regions suffice to identify the winning term of the target.

They do **not** linearize a 14-vertex cross-edge dictionary.  A first-layer
term \(\max(\langle v_u,x\rangle,\langle v_v,x\rangle)\) can compare
non-top vertices from different squares, whose relative order is not fixed
by the ten top-factor interleavings.  The proposed atom therefore remains a
maximum of sums of hinges, rather than a binary maximum of two linear forms,
on those regions.

A sound Rueß-style reduction must refine by the relevant cross-vertex
equality hyperplanes (and then collect the second-layer hinge directions),
or use a different exact global separation oracle.  If one refines by a
complete order of all fourteen vertex forms, a crude pre-feasibility ceiling
after the within-square chains, \(a\le b\), and the order of the three square
tops is

\[
 \frac{14!}{(4!)^3\,2!\,3!}=525{,}525
\]

order types.  Additive square relations make some infeasible, but there is no
basis for replacing them by ten.

The unrestricted raw degree-five dictionary is also not small.  Excluding
diagonal pairs leaves 91 possible vertex segments and
\(\binom{95}{5}=57{,}940{,}519\) branch multisets.  Even after dividing the
number of unordered branch pairs by the largest possible
\(H\) orbit (the branch interchange has already been removed by taking
unordered pairs), the elementary lower bound is over
\(2.73\times10^{11}\) atom orbits.  This is a size bound on that naive
enumeration, not on every structured search.

## Forest-level consequence

The reduction to \(T_{3,2}\) remains analytically valuable because it names
the smallest full-dimensional join core and forces any construction to couple
the square factors.  It does not make a naive exact degree-five census smaller
than the highly symmetric direct MAX11 quotient computation.  The immediate
division of labor should therefore be:

- direct complete quotient solve for the already frozen MAX11 dictionary as
  the primary computational discriminator;
- the minimal-basis cross-factor atoms above as a bounded analytic/discovery
  probe; and
- no further work on primitive-only or ten-chamber formulations unless a new
  direction-span or chamber-compression theorem fires the retry predicate.

The positive problem is still open: find a sparse full-dimensional
cross-factor identity, a complete exact separator for a declared structured
family, or a theorem that compresses the 14-vertex normal-fan calculation.

## Primary dependencies

- Bakaev et al., support functions, \(P^k\), and formal Minkowski difference:
  `literature/papers/2505.14338.txt`, lines 310--338.
- Rueß et al., pairwise-comparison atoms and exact hinge cancellation:
  `literature/papers/2607.21651.txt`, lines 330--395.
- Rueß et al., atom dimension and the degree lower-bound template:
  `literature/papers/2607.21651.txt`, lines 453--486.
- Koutschan et al., zero-summands, face descent, and the simplex obstruction:
  `literature/papers/2305.16933.txt`, lines 587--646.

These local texts are certified literature artifacts in the campaign.  Their
byte certification and the locators above establish source custody and
statement traceability, not the correctness or novelty of the new deductions
in this note.
