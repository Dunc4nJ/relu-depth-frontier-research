# G-0082 — structural boundaries around the first unknown join

## Status

This note records two exact deductions and one constructive reduction that
change the MAX11 search space. The arguments have received an internal
adversarial proof review. Their novelty has **not** been checked against the
complete literature, and none of them proves a MAX11 representation or lower
bound.

## The exact equivalent target

For

\[
T_{a,b}=\max\bigl(
  \max(x_1,x_2)+\max(x_3,x_4),\ldots,
  \max(x_{4a-3},x_{4a-2})+\max(x_{4a-1},x_{4a}),
  x_{4a+1},\ldots,x_{4a+b}
\bigr),
\]

the support function of
\(J_7=\Delta_7*[0,1]^2\) is \(T_{1,8}\), up to the standard
choice of coordinates for the join.

Bakaev--Brunck--Hertrich--Stade--Yehudayoff Claim 5 proves

\[
T_{a,b+4}\in\operatorname{span}\{T_{a+1,b+1}\circ L:L\text{ linear}\}.
\]

Applying it with \((a,b)=(0,7)\) gives

\[
\operatorname{MAX}_{11}=T_{0,11}
   \in\operatorname{span}\{T_{1,8}\circ L\}.
\]

Consequently \(J_7\in W_2\) implies
\(\operatorname{MAX}_{11}\in W_2\). Conversely, an exact two-hidden-layer
MAX11 representation gives every ten-dimensional CPWL function by the
standard signed decomposition into maxima of eleven affine forms; in
particular it gives \(h_{J_7}\). Thus, at the level of existence,

\[
J_7\in W_2\quad\Longleftrightarrow\quad
\operatorname{MAX}_{11}\in W_2.
\]

This is the first unknown member of the family: \(\dim J_p=p+3\), while the
published MAX10 theorem puts every CPWL function of dimension at most nine in
\(W_2\), covering \(J_1,\ldots,J_6\).

Primary locators:

- Bakaev et al., Claim 5 and its nine-term construction:
  literature/papers/2505.14338.txt, lines 238--278.
- Rueß et al., Theorem 1.1 and Corollary 1.3:
  literature/papers/2607.21651.txt, lines 118--143 and 649--660.

## A smaller full-dimensional constructive core

Two more applications of Claim 5 give

\[
T_{1,8}\in\operatorname{span}(T_{2,5}\circ L),\qquad
T_{2,5}\in\operatorname{span}(T_{3,2}\circ L).
\]

Each application expands into nine affine copies, so a certificate for
\(T_{3,2}\in W_2\) yields one for \(J_7\) through at most \(9^2=81\) copies.
Here

\[
T_{3,2}=\max(q_1,q_2,q_3,a,b),\qquad
q_i=\max(x_{4i-3},x_{4i-2})+\max(x_{4i-1},x_{4i}).
\]

Substituting \((q_1,q_2,q_3,a,b)\) into the explicit nine-term MAX5 identity
of Bakaev et al. gives an exact depth-three construction. It does not
automatically flatten to depth two: after substitution, branches such as

\[
\max(2b,q_1+q_2,q_3+a)
\]

are convex hulls of several zonotopes, and the published binary nesting
certifies a \(P^3\) object rather than a \(P^2\) object. The focused positive
problem is therefore to find cross-factor cancellation that rewrites this
nine-term circuit using full-dimensional
\(\operatorname{conv}(Z_0\cup Z_1)\) blocks.

Primary locator: Bakaev et al., Claim 4 / Equation (2),
literature/papers/2505.14338.txt, lines 165--232.

## Obstruction 1: lower-dimensional gluing alone cannot work

Embed

\[
J_p=\operatorname{conv}\bigl(
  0,e_{x_1},\ldots,e_{x_p},
  e_t,e_t+e_{y_1},e_t+e_{y_2},e_t+e_{y_1}+e_{y_2}
\bigr)
\subset\mathbb R^{p+3}.
\]

Take \(d=-e_{y_1}\). Its two opposite exposed faces are

\[
F_d(J_p)=
\operatorname{conv}\{0,e_{x_1},\ldots,e_{x_p},e_t,e_t+e_{y_2}\}
\cong\Delta_{p+2}
\]

and

\[
F_{-d}(J_p)=
\operatorname{conv}\{e_t+e_{y_1},e_t+e_{y_1}+e_{y_2}\},
\]

a segment. The first equality follows because the displayed \(p+3\)
vertices are affinely independent; the opposite segment has zero volume in
the \((p+2)\)-dimensional face ambient space.

If \(J_p\) were a zero-summand, Koutschan et al. Lemma 5.1 would force the
simplex \(F_d(J_p)\) to be a zero-summand. Their Corollary 5.2 says that a
full-dimensional simplex is not a zero-summand. Hence

\[
J_p\text{ is not a zero-summand for every }p\ge0.
\]

Functional corollary: \(h_{J_p}\) cannot be a finite real linear combination
of maxima of at most \(p+3\) affine functions. To handle biases correctly,
apply the hypothetical identity at \(\lambda x\), divide by \(\lambda\), and
let \(\lambda\to\infty\). Each affine maximum becomes the support function of
a polytope with at most \(p+3\) vertices and therefore dimension at most
\(p+2\). Grouping positive and negative coefficients would make \(J_p\) a
zero-summand, a contradiction.

For \(p=7\), this rules out signed sums made only from maxima of at most ten
affine forms. It does **not** rule out \(J_7\in W_2\): a valid \(P^2\) atom
can be full-dimensional and can have two zonotopal branches with many
vertices. It also rules out only literal facet/intersection
inclusion--exclusion; a gluing construction that introduces shared
full-dimensional blocks remains possible.

Primary locators: Koutschan et al., Lemma 5.1 and Corollary 5.2,
literature/papers/2305.16933.txt, lines 587--646.

## Obstruction 2: the three squares cannot remain black boxes

Suppose a \(W_2\) certificate for \(T_{3,2}\) used atoms whose two zonotopal
branch supports were built only from linear terms and nonnegative Minkowski
combinations of the five whole factors \(q_1,q_2,q_3,a,b\). Restrict to the
linear section

\[
x_{4i-3}=x_{4i-2}=r_i,\qquad
x_{4i-1}=x_{4i}=0,\qquad a=r_4,\quad b=r_5.
\]

Then \(q_i=r_i\), so \(T_{3,2}\) restricts to
\(\operatorname{MAX}_5(r)\). Every allowed branch restricts to a linear
function of \(r\), and every \(P^2\) atom restricts to a maximum of two
linear functions. On the hyperplane \(r_5=0\), this would express
\(\max(0,r_1,r_2,r_3,r_4)\) as a signed sum of binary affine maxima,
contradicting Koutschan et al. Theorem 5.4.

Therefore a successful flattening must use first-layer directions that cut
inside the square factors and/or couple different factors. Treating the
squares as precomputed scalar inputs is an exact dead end.

Primary locator: Koutschan et al., Lemma 5.3 and Theorem 5.4,
literature/papers/2305.16933.txt, lines 648--690.

## Research consequence

The unrestricted constructive target is now:

> Flatten the explicit nine-term \(T_{3,2}\) depth-three circuit through
> cross-factor, full-dimensional \(P^2\) blocks and virtual cancellation.

The complementary computational target remains the direct \(S_{11}\)-orbit
MAX11 dictionary. Failures of positive subdivisions for \(J_2\), including
G-0080, are method falsifiers only: \(J_2\in W_2\) is already implied by the
published dimension-nine theorem.
