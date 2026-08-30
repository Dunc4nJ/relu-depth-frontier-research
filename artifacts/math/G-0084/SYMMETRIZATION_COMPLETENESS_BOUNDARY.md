# G-0084 — what symmetrization does, and does not, buy

## Standing and exact no-claim boundary

This is a same-family exact derivation for `G-0006`.  It gives:

1. the virtual-polytope normal form obtained by symmetrizing an **arbitrary**
   two-hidden-layer representation of a positively homogeneous symmetric
   function;
2. an exact counterexample to any general inference from symmetry (even with
   positive homogeneity, translation covariance, and pair-max structure) to
   the Rueß degree-five dictionary; and
3. the weakest target-fibre hypothesis left open by that counterexample.

It does **not** show that MAX11 is outside the degree-five dictionary, that
MAX11 has no two-hidden-layer representation, or that a MAX11-specific
normal-form theorem is impossible.  The counterexample below is not MAX11.

## 1. Virtual polytopes and arbitrary two-hidden-layer networks

Write \(\rho(t)=\max(t,0)\).  For a polytope \(P\subset\mathbb R^n\), write

\[
 h_P(x)=\max_{p\in P}\langle p,x\rangle.
\]

Let \(\mathsf{VP}_n\) be the real vector space of virtual polytopes: formal
real Minkowski combinations of ordinary polytopes, identified whenever their
formal support functions agree.  Thus

\[
 h_{P+Q}=h_P+h_Q,\qquad
 h_{\operatorname{conv}(P\cup Q)}=\max(h_P,h_Q),
\]

and \([P]-[Q]\) has support-function representative \(h_P-h_Q\).  This is
the support-function realization of the cancellative Grothendieck
construction; no convexity is asserted for a general virtual support
function.

All empty Minkowski sums below mean the singleton \(\{0\}\).

For a coordinate permutation \(\sigma\in S_n\), let \(\sigma P\) denote the
coordinate-permuted polytope.  Since
\(h_{\sigma P}(x)=h_P(\sigma^{-1}x)\), averaging functions and averaging
virtual polytopes commute (the inverse is immaterial when summing over the
whole group).

### Lemma 1 (one arbitrary second-layer unit)

Let

\[
 g(x)=\sum_{r=1}^{m}\beta_r\rho(\langle w_r,x\rangle)
\]

and define two zonotopes

\[
 P=\sum_{\beta_r>0}[0,\beta_rw_r],\qquad
 Q=\sum_{\beta_r<0}[0,-\beta_rw_r].
\]

Then, with \(R=\operatorname{conv}(P\cup Q)\),

\[
 g=h_P-h_Q,
 \qquad
 \rho(g)=h_R-h_Q.
\]

#### Proof

The segment identity
\(h_{[0,w]}(x)=\rho(\langle w,x\rangle)\), positive scaling, and Minkowski
additivity give \(g=h_P-h_Q\).  Hence

\[
 \rho(g)=\max(0,h_P-h_Q)
        =\max(h_Q,h_P)-h_Q
        =h_{\operatorname{conv}(P\cup Q)}-h_Q.\qedhere
\]

### Theorem 2 (the exact output of symmetrization)

Suppose a positively homogeneous function \(f:\mathbb R^n\to\mathbb R\)
has a finite two-hidden-layer representation.  After deleting all biases, as
per Hertrich--Basu--Di Summa--Skutella Proposition 2.3, write it as

\[
 f(x)=\sum_{j=1}^{m_2}a_j\rho\!\left(
       \sum_{r=1}^{m_1}\beta_{jr}\rho(\langle w_r,x\rangle)\right).
\]

For each \(j\), form \(P_j,Q_j,R_j\) as in Lemma 1.  Its virtual Newton
polytope is then

\[
 [f]=\sum_{j=1}^{m_2}a_j\bigl([R_j]-[Q_j]\bigr)
 \quad\text{in }\mathsf{VP}_n.                                      \tag{1}
\]

If \(f\) is \(S_n\)-invariant, then

\[
 [f]
 =\frac1{n!}\sum_{j=1}^{m_2}a_j\sum_{\sigma\in S_n}
   \bigl([\sigma R_j]-[\sigma Q_j]\bigr).                            \tag{2}
\]

In particular, if \(f=\operatorname{MAX}_n=h_{\Delta_{n-1}}\), where
\(\Delta_{n-1}=\operatorname{conv}\{e_1,\ldots,e_n\}\), then (2) is an
equality with the ordinary polytope \([\Delta_{n-1}]\) on the left.

#### Proof

Positive homogeneity permits removal of every bias without changing the
represented function.  Apply Lemma 1 to every second-layer unit and then use
linearity of the output to obtain (1).  Apply the Reynolds operator
\(n!^{-1}\sum_\sigma\sigma\) to (1).  It fixes \([f]\) because \(f\) is
symmetric, and it sends every summand to the orbit average displayed in
(2). \(\square\)

### Exact information content of (2)

Equation (2) gives a finite orbit sum **after a particular finite network is
already known**.  Its seeds are general virtual atoms

\[
 [\operatorname{conv}(P_j\cup Q_j)]-[Q_j],                           \tag{3}
\]

where \(P_j,Q_j\) are zonotopes with arbitrary real generator directions,
arbitrary real lengths, and as many generators as the first-layer width
allows.  Therefore (2) gives none of the following without another theorem:

- coordinate-pair directions \([e_p,e_q]\);
- nonnegative unit multiplicities;
- equal branch degree;
- degree at most five;
- rational coefficients; or
- a universal finite seed dictionary independent of the unknown network.

It also does not allow the negative \(-[Q_j]\) parts to be discarded
atom-by-atom.  Convexity of the final target can arise only after cancellations
among different virtual atoms.

This is the precise distinction between “a solution may be averaged” and
“the averaged solution lies in the finite Rueß ansatz.”

## 2. The degree-\(k\) pair-max orbit space

Let

\[
 E_n=\{(p,q):1\le p\le q\le n\},\qquad
 m_{pq}(x)=\max(x_p,x_q),
\]

and let \(\mathcal M_{n,k}\) be the multisets of cardinality \(k\) in
\(E_n\), with loops and repetitions allowed.  For
\(A,B\in\mathcal M_{n,k}\), put

\[
 Z_A=\sum_{(p,q)\in A}[e_p,e_q],\qquad
 \Phi_{A,B}(x)=\max\!\left\{
   \sum_{(p,q)\in A}m_{pq}(x),
   \sum_{(p,q)\in B}m_{pq}(x)\right\}.
\]

Then

\[
 \Phi_{A,B}=h_{\operatorname{conv}(Z_A\cup Z_B)}.
\]

Define the full symmetrized degree-\(k\) pair-max space

\[
 \mathcal V_{n,k}
 =\operatorname{span}_{\mathbb R}\left\{
   \sum_{\sigma\in S_n}\Phi_{A,B}(\sigma x):
   A,B\in\mathcal M_{n,k}\right\}.
\]

This is the complete Rueß dictionary at a fixed degree, before any further
computational subfamily restriction.

For a nonzero integer vector \(d\in\mathbb Z^n\) with
\(\sum_i d_i=0\), define its signed mass

\[
 \mu(d)=\sum_{d_i>0}d_i
       =\sum_{d_i<0}(-d_i)=\tfrac12\lVert d\rVert_1.
\]

Call \(d\) primitive if the gcd of its coordinates is one.

Let \(\mathscr H_{n,k}\) be the finite set of hyperplanes \(d^\perp\)
arising from differences of two nonnegative integer count vectors of total
mass \(k\).  This is a universal set depending only on \(n,k\), not on a
chosen element of \(\mathcal V_{n,k}\).

### Lemma 3 (degree bounds every sorted-cone hinge normal)

Let

\[
 C^\circ=\{x\in\mathbb R^n:x_1<x_2<\cdots<x_n\}.
\]

For every \(F\in\mathcal V_{n,k}\), the nondifferentiability locus of
\(F\) in \(C^\circ\) is contained in \(\mathscr H_{n,k}\), whose nonzero
normals satisfy

\[
 d^\perp,\qquad
 d\in\mathbb Z^n\setminus\{0\},\quad
 \sum_i d_i=0,\quad
 \mu(d_{\mathrm{prim}})\le k,                                      \tag{4}
\]

where \(d_{\mathrm{prim}}\) is either primitive orientation of the ray
\(\mathbb R d\).  Adding any affine-linear function does not enlarge this
locus.

#### Proof

Fix \(A,B\) and \(\sigma\).  On \(C^\circ\), every
\(m_{pq}(\sigma x)\) is one coordinate of \(x\).  Consequently the two
branches of \(\Phi_{A,B}(\sigma x)\) are \(a\cdot x\) and \(b\cdot x\)
for count vectors \(a,b\in\mathbb N^n\) satisfying

\[
 \sum_i a_i=\sum_i b_i=k.
\]

The only possible interior kink of this term has normal \(d=b-a\).  It has
zero coordinate sum, and

\[
 \mu(d)=\sum_{d_i>0}(b_i-a_i)\le\sum_i b_i=k.
\]

Dividing by the coordinate gcd cannot increase signed mass.  Away from all
of these finitely many hyperplanes, every summand is locally linear.  A finite
real linear combination can cancel existing kinks, but cannot create a kink
where all its summands are locally linear.  Affine terms are locally linear
everywhere. \(\square\)

## 3. Exact degree-six counterexample at \(n=11\)

Let \(T\) be the 990 ordered triples of pairwise distinct indices in
\([11]\).  Define

\[
 \boxed{
 G(x)=\frac1{5940}\sum_{(i,j,\ell)\in T}
       \max\{6x_i,\,5x_j+x_\ell\}.}                                \tag{5}
\]

The denominator is
\(5940=6\cdot 11\cdot10\cdot9\).

### Lemma 4 (exact structural properties of \(G\))

The function \(G\) is convex, positively homogeneous, \(S_{11}\)-invariant,
and satisfies

\[
 G(x+t\mathbf1)=G(x)+t\qquad(x\in\mathbb R^{11},\ t\in\mathbb R).  \tag{6}
\]

It is the support function of the ordinary \(S_{11}\)-invariant polytope

\[
 P_G=\frac1{5940}\sum_{(i,j,\ell)\in T}
             [\,6e_i,\,5e_j+e_\ell\,].                             \tag{7}
\]

Moreover,

\[
 G\in\mathcal V_{11,6}.
\]

#### Proof

Every term in (5) is a maximum of two linear forms and hence is convex and
positively homogeneous.  Permuting coordinates permutes \(T\), proving
symmetry.  Both branches in every term gain \(6t\) under
\(x\mapsto x+t\mathbf1\).  There are \(11\cdot10\cdot9=990\) terms, so
the numerator gains \(5940t\), which proves (6) and verifies the
normalization exactly.

There is also an explicit ordinary ReLU realization, since

\[
 \max(6x_i,5x_j+x_\ell)
 =\rho(6x_i-5x_j-x_\ell)
  +\rho(5x_j+x_\ell)-\rho(-5x_j-x_\ell).
\]

Thus (5) has a finite one-hidden-layer realization; passing its nonnegative
hidden outputs through identity ReLUs gives an exact network with exactly two
hidden layers.

The support function of the segment
\([6e_i,5e_j+e_\ell]\) is the corresponding maximum in (5); Minkowski
additivity gives (7).  Every endpoint of every unscaled segment has coordinate
sum six, so every point of \(P_G\) has coordinate sum one.  Thus (7) lies in
the same translation-covariant affine hyperplane as the MAX11 simplex; (6) is
also immediate from this support-polytope fact.

Finally, take \(A\) to be six copies of the loop \((i,i)\), and \(B\) to
be five copies of \((j,j)\) and one copy of \((\ell,\ell)\).  Then
\(\Phi_{A,B}(x)=\max\{6x_i,5x_j+x_\ell\}\).  Summing its orbit and scaling
therefore puts \(G\) in \(\mathcal V_{11,6}\): the stabilizer of the other
eight labels has size \(8!\), so the full \(S_{11}\)-orbit sum is exactly
\(8!\) times the numerator of (5).  Each block also has the standard exact
two-hidden-layer pair-max realization. \(\square\)

### Theorem 5 (symmetry does not reduce degree six to degree five)

\[
 \boxed{G\notin\mathcal V_{11,5}+\operatorname{Aff}(\mathbb R^{11}).}
\]

In particular, even within the pair-max model,
\(S_{11}\)-symmetry, positive homogeneity, and the exact MAX11 translation
law do not imply membership in the degree-five orbit dictionary.
Nor can \(G\) be a signed combination of unsymmetrized degree-five blocks:
averaging any such identity would put \(G\), which is already symmetric, in
\(\mathcal V_{11,5}\).

#### Proof

Consider

\[
 v=6e_2-5e_1-e_3,
 \qquad H=v^\perp.
\]

The vector \(v\) is primitive, has coordinate sum zero, and has signed mass
\(\mu(v)=6\).  The point

\[
 x^0=(0,1,6,7,8,9,10,11,12,13,14)
\]

lies in \(H\cap C^\circ\), since
\(6x^0_2-5x^0_1-x^0_3=6-0-6=0\).  Thus this intersection contains a
nonempty relatively open subset of \(H\).

No hyperplane allowed by Lemma 3 for degree five equals \(H\).  Indeed, if
an integer \(d\) with primitive signed mass at most five were proportional
to \(v\), its primitive orientation would be \(v\) or \(-v\), both of
signed mass six, a contradiction.

The orbit terms in (5) have kink normals

\[
 v_{i,j,\ell}=6e_i-5e_j-e_\ell.
\]

Only \((i,j,\ell)=(2,1,3)\) gives the hyperplane \(H\).  To see this, equality
of two such hyperplanes makes their primitive integer normals equal up to
sign.  Equality with \(+v\) fixes, uniquely, the locations of the coefficients
\(6,-5,-1\).  Equality with \(-v\) is impossible because \(-v\) has two
positive coordinates \(5,1\) and one negative coordinate \(-6\), whereas
every \(v_{i,j,\ell}\) has one positive coordinate \(6\) and two negative
coordinates \(-5,-1\).

Inside \(H\cap C^\circ\), remove:

1. the finitely many other orbit hyperplanes \(v_{i,j,\ell}^\perp\); and
2. the finite universal set \(\mathscr H_{11,5}\) from Lemma 3.

Every removed intersection is a proper hyperplane of \(H\).  A finite union
of proper hyperplanes cannot cover the nonempty relatively open set
\(H\cap C^\circ\).  Choose a point \(x^*\) in the remainder.

Near \(x^*\), every term of (5) except the \((2,1,3)\) term is affine.  The
remaining term is, up to an affine function,

\[
 \frac1{5940}\rho(v\cdot x).
\]

Its gradient has the nonzero jump \(v/5940\) across \(H\).  Its positive
coefficient cannot cancel because no other orbit term has a kink there, and
adding affine functions never changes a gradient jump.  Hence \(G\) is not
differentiable at \(x^*\).

By Lemma 3, every member of
\(\mathcal V_{11,5}+\operatorname{Aff}(\mathbb R^{11})\) is locally affine
at \(x^*\).  Therefore \(G\) is not a member of that space. \(\square\)

## 4. What hypothesis can still make the degree-five search complete?

There are two logically independent missing reductions.

### 4.1 Arbitrary-network to graphical-pair normal form

Equation (2) only supplies orbit averages of the general virtual atoms (3).
To enter **any** pair-max dictionary, one needs a theorem that a MAX11
identity can be regrouped, after all virtual cancellations, into atoms

\[
 h_{\operatorname{conv}(Z_A\cup Z_B)}
\]

with graphical zonotopes \(Z_A,Z_B\) generated by coordinate segments
\([e_p,e_q]\), with the two branches of each atom having the same finite
cardinality (allowed to vary between atoms).  Neither symmetrization nor
final-target convexity proves the direction restriction, the discreteness, or
the atomwise equal-degree condition.  Call this missing statement `GNF`.

More abstractly, a finite orbit reduction is valid under the following exact
and essentially minimal seed hypothesis: there is a finite \(S_{11}\)-stable
set \(\mathcal A\subset\mathsf{VP}_{11}\) such that some MAX11 virtual
identity has every atom in \(\operatorname{span}\mathcal A\).  Only then does
the Reynolds operator reduce the identity to the finitely many orbit sums in
\(\mathcal A/S_{11}\).  Symmetry gives the Reynolds step; it does not give
the seed hypothesis.

### 4.2 The weakest target-fibre statement not killed by \(G\)

Theorem 5 rules out the global claim

\[
 \mathcal V_{11,6}\subseteq\mathcal V_{11,5}.
\]

MAX11 has an additional property on \(C^\circ\): its restriction is the
linear function \(x_{11}\).  Thus a weaker, target-relevant degree reduction
could still hold only on the **hinge-free fibre**.

For a symmetrized pair-max combination, use the Rueß sorted-cone expansion

\[
 F|_{C^\circ}=L_F+\sum_d c_{F,d}\rho(d\cdot x),                       \tag{8}
\]

after discarding sign-definite directions and choosing one primitive
orientation for every hyperplane meeting \(C^\circ\).  This expansion is
unique: at a generic point of one such hyperplane, its coefficient is the
normal gradient jump and all other hinge terms are locally affine.  Let
\(\mathsf H(F)=(c_{F,d})_d\) and let \(\mathsf L(F)\) be the coefficient
vector of \(L_F\).  Put

\[
 \mathcal L_*=\mathsf L(\ker\mathsf H\cap\mathcal V_{11,*}),
 \qquad
 \mathcal L_5=\mathsf L(\ker\mathsf H\cap\mathcal V_{11,5}),
\]

where \(\mathcal V_{11,*}\) is the span of pair-max orbit blocks of all finite
degrees.  The logically weakest direct statement needed for the MAX11 fibre is

\[
 \boxed{e_{11}\in\mathcal L_*\ \Longrightarrow\ e_{11}\in\mathcal L_5.}
                                                                         \tag{DR5-MAX}
\]

Given `GNF`, the premise holds; the conclusion is precisely a degree-five
pair-max representation because symmetry extends equality with \(x_{11}\)
from the sorted cone to all of \(\mathbb R^{11}\).

A stronger but reusable linear-algebra hypothesis is

\[
 \boxed{
 \mathcal L_*\subseteq\mathcal L_5.}                               \tag{DR5}
\]

Statement `(DR5)` says only that every ordered-cone **linear output**
obtainable after exact cancellation of arbitrary-degree interior hinges has a
degree-five realization with exact hinge cancellation.  It does not claim
that arbitrary nonlinear functions, such as \(G\), reduce to degree five.

`GNF + (DR5-MAX)` would make the full degree-five pair-orbit system complete
for unrestricted MAX11; `(DR5)` implies `(DR5-MAX)`.  None of these statements
is proved here.  Conversely, the direct
functional hypothesis that MAX11 already has a signed sum of degree-five
pair-max blocks is sufficient, but it merely restates the missing normal form
rather than deriving it.

## 5. Next falsifiable discriminator

Attack the reusable `(DR5)` before attempting a global symmetry normal form:

> Find an exact finite combination of degree-six (or structured higher-degree)
> orbit blocks whose every sorted-cone interior hinge cancels, but whose
> remaining ordered-cone linear coefficient vector lies outside the exact
> degree-five hinge-free linear projection.

Such a combination would be an exact counterexample to `(DR5)` and would
show that even a hypothetical graphical normal form would not justify the
degree-five census for arbitrary hinge-free ordered-cone outputs.  It would not
by itself refute the narrower `(DR5-MAX)` unless its remaining linear vector
were \(e_{11}\).  A clean null over a declared structured
degree-six family would remain bounded to that family.  Theorem 5 supplies a
mandatory hostile control: a purported degree-reduction procedure must reject
\(G\), because its mass-six hinge is genuinely present.  Any proposed bridge
that uses only symmetry, homogeneity, translation covariance, or pair-max
structure is already falsified; a surviving bridge must use the target's
exact hinge cancellation (or another explicitly MAX11-specific invariant).

## 6. Primary source and local-artifact locators

- Bias removal and arbitrary-network virtual-polytope characterization:
  `literature/papers/2105.14835.txt`, lines 406--442 and 1508--1577; the
  virtual-polytope summary is at lines 1612--1617.
- The virtual-polytope/support-function bijection and recursive maxout-network
  correspondence are also stated by Grillo--Hofmann:
  `literature/papers/2510.14068.txt`, lines 315--506.  Their common-affine-span
  dimension bound at lines 561--619 does not supply a symmetry-to-pair or
  degree-five normal form.
- Symmetrization versus the explicitly restricted pair-max ansatz, and the
  sorted-cone hinge expansion: `literature/papers/2607.21651.txt`, lines
  274--313 and 315--395.
- Pair-max support polytopes and the degree-five dimension motivation:
  `literature/papers/2607.21651.txt`, lines 444--486.
- Formal Minkowski difference and support-function language:
  `literature/papers/2505.14338.txt`, lines 308--338.
- Zero-summands provide a lower-dimensional obstruction, not a completeness
  theorem: `literature/papers/2305.16933.txt`, lines 587--662.
- The adjacent common-direction-rank obstruction and its explicit no-claim
  boundary: `artifacts/math/G-0083/T32_ANSATZ_AUDIT.md`.
- The Lean notes explicitly exclude any arbitrary-network or degree-five
  completeness result: `formalization/README.md` and
  `formalization/INDUCTION_OBSTRUCTION_STATEMENT_MATCH.md`.

The local literature objects above are campaign-certified for source custody
and statement traceability only.  This new derivation has not received a T2
referee review or a novelty audit.
