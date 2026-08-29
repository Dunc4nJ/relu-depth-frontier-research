# G-0066 — equality at simplex asymmetry three inside the braid fan

## Result and exact scope

Let \(m\ge 5\), let \(\Delta=\Delta_{[m]}\), and let \(R\subset\mathbb R^m\)
be a nonpoint generalized permutohedron.  With \(\mathcal P^2\) denoting sums
of convex hulls of two zonotopes, this artifact proves

\[
 R\in\mathcal P^2\ \text{ and }\ \rho_\Delta(R)=3
 \quad\Longleftrightarrow\quad
 R=t+\sum_{|I|=4}a_I\Delta_I,
 \qquad a_I\ge0,                                      \tag{1}
\]

where not all \(a_I\) vanish.  Thus the extremal depth-two generalized
permutohedra are exactly the translated nonnegative sums of coordinate
tetrahedra.

This is a classification only at the equality value \(\rho_\Delta=3\), and
only inside the generalized-permutohedron class.  It is not an unrestricted
MAX11 obstruction.

## Proof

Use the centered simplex facet normals

\[
 q_i=\mathbf 1-me_i,\qquad i\in[m],
\]

and write

\[
 A_K=\sum_i h_K(-q_i),\qquad B_K=\sum_i h_K(q_i).
\]

Both quantities are translation invariant and Minkowski additive, and the
support-function formula of Bakaev--Yehudayoff gives
\(\rho_\Delta(K)=A_K/B_K\) for every nonpoint \(K\).

### 1. Equality descends to every nonpoint primitive

Choose a depth-two presentation

\[
 R=t+\sum_j C_j,
 \qquad C_j=\operatorname{conv}(P_j\cup Q_j),             \tag{2}
\]

where \(P_j,Q_j\) are zonotopes; point summands are absorbed into \(t\).
The proof of the Minkowski-sum bound expresses \(\rho_\Delta(R)\) as the
positive \(B_{C_j}\)-weighted average of the primitive ratios.  Every
primitive has ratio at most three.  If one branch is a point, the same
support-function proof gives the sharper bound two.  Consequently equality
in (1) forces both branches of every nonpoint primitive to be nonpoint and

\[
 \rho_\Delta(C_j)=3.                                     \tag{3}
\]

Each \(C_j\) is a Minkowski summand of \(R\).  Shephard's summand criterion
therefore makes every edge direction of \(C_j\) an edge direction of \(R\).
Because \(R\) is a generalized permutohedron, those directions are roots
\(e_a-e_b\).  Hence each \(C_j\) is itself a generalized permutohedron.

### 2. Equality makes the two branches a disjoint-support join

Fix one equality primitive \(C=\operatorname{conv}(P\cup Q)\).  Equality in
the two inequalities in the convex-hull proof gives

\[
 h_P(q_i)=h_Q(q_i)\quad\text{for every }i,                \tag{4}
\]

and, for every \(i\), at least one of \(P,Q\) has zero width in direction
\(q_i\).  All points of \(C\) have the same coordinate sum.  In that affine
hyperplane, (4) says that \(P\) and \(Q\) have the same coordinatewise
minima.  Translate by this common minimum vector.  The translated branches
are nonnegative, have the same positive coordinate sum \(L\), and the
zero-width condition says their coordinate supports are disjoint.

The resulting convex hull is a free join.  Every pair consisting of a vertex
\(p\) of one branch and a vertex \(q\) of the other is therefore a cross edge.
It must be a root edge.  Nonnegativity, disjoint supports, and
\(\sum p_i=\sum q_i=L\) then force

\[
 p=Le_a,\qquad q=Le_b.                                   \tag{5}
\]

Thus each branch is a centrally symmetric polytope whose vertices are among
the vertices of a coordinate simplex.  Affine independence makes such a
nonpoint polytope a segment.  The two branches use disjoint pairs, so

\[
 C=t_C+L\Delta_I\qquad(|I|=4).                            \tag{6}
\]

Summing (6) proves the forward implication of (1).  Conversely,
\(\Delta_I\) for \(|I|=4\) is the convex hull of two disjoint coordinate
segments, hence is a depth-two primitive.  Direct support evaluation gives
\(B_{\Delta_I}=m\) and \(A_{\Delta_I}=3m\).  Nonnegative sums preserve both
depth two and the ratio three, proving the reverse implication.

## Strict consequence for every single-zonotope MAX11 stabilizer

Let

\[
 \Pi_m=\sum_{1\le i<j\le m}[e_i,e_j],\qquad
 t_m=\frac{m-4}{m(m-1)},\qquad
 D_m=\Delta_{[m]}+t_m\Pi_m.                              \tag{7}
\]

Exact support evaluation gives

\[
 \lambda_\Delta(D_m)=\frac{m-2}{2},\qquad
 \lambda_{-\Delta}(D_m)=\frac{3(m-2)}2,
 \qquad \rho_\Delta(D_m)=3.                             \tag{8}
\]

For generalized permutohedra, the signed standard-simplex decomposition is
unique.  The coefficients of \(D_m\) are

\[
 y_{[m]}=1,\qquad y_{\{i,j\}}=t_m,                       \tag{9}
\]

with all other nonsingleton coefficients zero.  When \(m\ge5\), (9) cannot
be the coefficient vector of a nonnegative sum of coordinate tetrahedra;
translations alter only singleton coefficients.  Classification (1) hence
implies

\[
 \boxed{D_m\notin\mathcal P^2\quad(m\ge5).}              \tag{10}
\]

G-0065 showed that equality in its MAX11 zonotope-stabilizer bound forces
\(Z\), up to translation, to equal \((1/14)\Pi_{11}\).  A generic seven- or
eight-coordinate tie face of \(\Delta_{10}+Z\) is respectively \(D_7\) or
\(D_8\), because \(t_7=t_8=1/14\).  Faces of depth-two polytopes remain
depth two, contradicting (10).  Therefore the earlier non-strict bound
improves to

\[
 \boxed{\lambda_{\Delta_{10}}(Z)>55/14}                  \tag{11}
\]

for every zonotope \(Z\) satisfying
\(\Delta_{10}+Z\in\mathcal P^2\).  This remains a
**single-zonotope-subclass** theorem; the unrestricted virtual identity may
have a non-zonotopal negative side.

## Hostile control: why the braid-fan hypothesis is essential

In \(\mathbb R^5\), set

\[
 P=\operatorname{conv}\{(1/2,1/2,0,0,0),e_3\},\qquad
 Q=[e_4,e_5],\qquad C=\operatorname{conv}(P\cup Q).
\]

Both branches are segments and exact evaluation gives \(A_C=15\), \(B_C=5\),
so \(\rho_{\Delta_4}(C)=3\).  But the cross edge from
\((1/2,1/2,0,0,0)\) to \(e_4\) is not parallel to a root.  Hence \(C\) is not
a generalized permutohedron.  Equality alone does not imply the tetrahedron
classification.

## Executable controls and source bindings

The exact verifier:

- binds the upstream G-0065 artifact and both load-bearing primary sources by
  SHA-256;
- evaluates every coordinate tetrahedron through ambient dimensions 4--11;
- recovers the unique signed-simplex coefficients of every \(D_m\),
  \(5\le m\le11\), by Boolean Möbius inversion;
- exhaustively checks through eight coordinate vertices that a centrally
  symmetric coordinate-simplex vertex subset has at most two vertices;
- replays the hostile non-braid equality example; and
- verifies \(t_7=t_8=1/14\) and the exact values in (8).

Run:

```bash
.venv/bin/python -B artifacts/math/G-0066/verify_gp_equality_classification.py \
  --check-frozen
```

The script checks finite algebraic consequences; the structural proof above
is the mathematical argument.  Novelty has not been adjudicated, and no
priority claim is made.
