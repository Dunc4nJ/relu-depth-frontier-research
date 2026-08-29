# G-0065 — facewise bounds for a single zonotope stabilizer

## Exact scope

This artifact studies only identities of the special form

\[
\Delta_{10}+Z=B,
\qquad Z\text{ a zonotope},\quad B\in\mathcal P^2.          \tag{1}
\]

It does **not** constrain the general virtual identity
\(\Delta_{10}+A=B\) when \(A\) is an arbitrary non-zonotopal member of
\(\mathcal P^2\). In particular, it does not contradict any public
MAX5--MAX10 certificate.

## The facewise stabilizer theorem

Let \(N\) be the number of MAX coordinates, let \(S\subseteq[N]\) have
\(s=|S|\ge5\), and choose a generic direction \(x\) whose equal top
coordinates are exactly \(S\). If

\[
\Delta_{N-1}+Z=B,qquad Z\text{ a zonotope},\quad B\in\mathcal P^2,
\]

then

\[
F_x(\Delta_{N-1})+F_x(Z)=F_x(B).                            \tag{2}
\]

The first face is \(\Delta_{s-1}\). The class \(\mathcal P^2\) is closed
under exposed faces: faces commute with Minkowski sums; a face of a zonotope
is a zonotope; and a face of
\(\operatorname{conv}(P\cup Q)\) is either a face of one branch or the hull
of the two tied branch faces. Hence \(F_x(B)\in\mathcal P^2\), while
\(F_x(Z)\) remains a zonotope after translation into the face span.

Apply the G-0063 zonotope specialization to (2). Since the local simplex has
dimension \(s-1\),

\[
\boxed{\lambda_{\Delta_{s-1}}(F_x(Z))\ge\frac{s-4}{2}}.     \tag{3}
\]

For a MAX11 facet, \(s=10\), so every one of the eleven facet stabilizers
must satisfy

\[
\boxed{\lambda_{\Delta_9}(F_i(Z))\ge3}.                    \tag{4}
\]

In centered coordinates, G-0064 gives the concrete restriction

\[
F_i(Z)\text{ retains exactly the generators }g\text{ with }g_i=0. \tag{5}
\]

Thus (4) is substantially stronger than merely requiring one zero-coordinate
generator per facet.

## Exact no-go for the naïve centered Δ-zonotope

Set \(\mu=\mathbf1/11\), \(a_j=e_j-\mu\), and

\[
R_\Delta=\sum_{j=1}^{11}[0,a_j].
\]

Every coordinate of every \(a_j\) is nonzero. At the direction
\(d_i=\mu-e_i\) exposing the facet opposite vertex \(i\),

\[
\langle a_j,d_i\rangle=-(a_j)_i\ne0.
\]

Therefore \(F_{d_i}(R_\Delta)\) is a point and

\[
F_{d_i}(\Delta_{10}+R_\Delta)=\Delta_9+\text{point}.
\]

If \(\Delta_{10}+R_\Delta\) belonged to \(\mathcal P^2\), face closure would
force \(\Delta_9\in\mathcal P^2\). This is impossible because the
simplex-asymmetry value is \(9\), whereas every depth-two polytope has value
at most \(3\). Hence

\[
\boxed{\Delta_{10}+R_\Delta\notin\mathcal P^2}.             \tag{6}
\]

More generally, any proposed \(Z\) with no generator satisfying \(g_i=0\)
for some facet \(i\) is rejected by the same argument.

## Stronger bound for every zonotope stabilizer

Write an arbitrary finite zonotope, up to translation, as

\[
Z=\sum_r[0,g_r],\qquad g_r\in H=\{g:\sum_i g_i=0\}.
\]

For a generic direction with top-coordinate set \(S\), the segment generated
by \(g_r\) survives in the exposed face iff

\[
\operatorname{supp}(g_r)\subseteq S.                        \tag{7}
\]

Support containment makes the pairing zero because the coordinates on
\(S\) are equal and \(\sum_i g_{r,i}=0\). Conversely, if a generator has a
nonzero coordinate outside \(S\), its zero-pairing condition is a proper
hyperplane in the relative-open tie cone. Finiteness lets us choose the
direction outside all such accidental hyperplanes.

For a generator supported on \(S\), direct evaluation at the centered
simplex normals \(q_i=\mathbf1-se_i\) gives

\[
\lambda_{\Delta_{s-1}}([0,g_r])
=\frac1s\sum_i\max(0,\langle q_i,g_r\rangle)
=\sum_i g_{r,i}^{+}
=\frac{\lVert g_r\rVert_1}{2}.                              \tag{8}
\]

Put \(a_r=\lVert g_r\rVert_1/2\) and
\(k_r=|\operatorname{supp}(g_r)|\). Every nonzero centered generator has
\(k_r\ge2\). Summing (3) over all \(s\)-subsets gives

\[
\sum_r a_r\binom{11-k_r}{s-k_r}
\ge \binom{11}{s}\frac{s-4}{2}.                            \tag{9}
\]

For fixed \(s\), the retention multiplicity is maximized at \(k_r=2\).
Since outer additivity and (8) give
\(\lambda_\Delta(Z)=\sum_r a_r\),

\[
\lambda_\Delta(Z)
\ge\frac{\binom{11}s}{\binom9{s-2}}\frac{s-4}{2}
=\frac{55(s-4)}{s(s-1)}.                                  \tag{10}
\]

The strongest values occur at \(s=7,8\):

\[
\boxed{\lambda_{\Delta_{10}}(Z)\ge\frac{55}{14}}.          \tag{11}
\]

This improves G-0063's global \(7/2\) bound and applies to arbitrary real
zonotope generators, not only coordinate-pair generators.

### Equality is rigid

If equality holds in (11), use the \(s=7\) double count. Every step in (9)--
(10) must be equality. Retention is strictly less efficient for every support
size above two, so every nonzero generator has support exactly two. Such a
centered generator is a scalar multiple of \(e_a-e_b\); merge parallel
segments and call the resulting weights \(w_{ab}\).

Every seven-set constraint is then tight:

\[
\sum_{\{a,b\}\subseteq S}w_{ab}=\frac32
\qquad(|S|=7).                                               \tag{12}
\]

These equations force uniform weights. For distinct \(i,j\), compare (12)
on \(A\cup\{i\}\) and \(A\cup\{j\}\) over all six-sets \(A\) disjoint
from \(i,j\). Every six-subset sum of \(w_{ia}-w_{ja}\) is zero. Exchanging
one element makes all nine differences equal, and a six-fold sum then makes
them zero. Varying \(i,j\) forces a common edge weight; (12) sets it to
\(1/14\). Therefore

\[
\boxed{\lambda_\Delta(Z)=55/14
\Longrightarrow
Z\text{ is a translate of }\frac1{14}Z_{K_{11}}.}           \tag{13}
\]

The verifier also certifies that the 330-by-55 incidence matrix of seven-sets
versus edges has full column rank modulo 1,000,003, hence over \(\mathbb Q\).

## Weighted graphical stabilizers

Now specialize further to

\[
Z=\sum_{1\le a<b\le11}w_{ab}[e_a,e_b],\qquad w_{ab}\ge0.  \tag{14}
\]

For the centered \((s-1)\)-simplex, the facet normals are
\(q_i=\mathbf1-se_i\). Direct evaluation gives

\[
\lambda_{\Delta_{s-1}}([e_a,e_b])
=\frac1s\sum_i h_{[e_a,e_b]}(q_i)=1.                       \tag{15}
\]

At a generic top tie on \(S\), a root generator survives iff both endpoints
lie in \(S\). Outer additivity and (8) turn (3) into

\[
\boxed{\sum_{\{a,b\}\subseteq S}w_{ab}\ge\frac{|S|-4}{2}}
\qquad(5\le|S|\le11).                                      \tag{16}
\]

Double-count (16) over all \(s\)-subsets. Each edge occurs in
\(\binom9{s-2}\) such subsets, so

\[
\sum_{a<b}w_{ab}
\ge\frac{\binom{11}s}{\binom9{s-2}}\frac{s-4}{2}
=\frac{55(s-4)}{s(s-1)}.                                  \tag{17}
\]

The strongest values are \(s=7,8\):

\[
\boxed{\sum_{a<b}w_{ab}\ge\frac{55}{14}}.                 \tag{18}
\]

Uniform weights \(w_{ab}=1/14\) meet every inequality (16), with equality
at \(s=7,8\). Thus (18) is sharp for this finite system of necessary linear
constraints. It is not a sufficiency result: concentrating total weight
\(55/14\) on one edge passes (11) while immediately violating (9) on a
seven-set avoiding that edge.

## Low-arity and hostile controls

The exact verifier checks all load-bearing finite statements:

- every translated root segment has \(\lambda_\Delta=1\) for simplex sizes
  2 through 11;
- dense centered segments replay
  \(\lambda_\Delta([0,g])=\sum_i g_i^+=\lVert g\rVert_1/2\);
- generic tie directions retain exactly the induced root edges;
- support-retention multiplicities are checked for every support size, and
  the seven-set/edge incidence matrix has certified full column rank;
- edge/subset incidences and (10) are enumerated, not sampled;
- uniform \(1/14\) passes all MAX11 subset constraints, while any uniform
  decrement fails a tight seven-set;
- the centered \(\Delta\)-zonotope facet calculation is replayed for
  MAX4 through MAX11, showing that the face obstruction begins only when the
  exposed facet simplex has dimension at least four;
- MAX4 is a positive boundary control:
  \(\Delta_3=\operatorname{conv}([e_1,e_2]\cup[e_3,e_4])\);
- the negative sides of every public MAX5--MAX10 certificate have
  \(\rho_\Delta\ne1\), so they are not zonotopes and lie outside (1)'s scope.

Run:

```bash
.venv/bin/python -B artifacts/math/G-0065/verify_single_zonotope_face_bounds.py \
  --check-frozen
```

## Input bindings and claim boundary

This artifact binds the exact G-0063 stabilizer-size theorem and the G-0064
face-gluing theorem by SHA-256 in its frozen report.

- It proves no MAX11 representation.
- It does not rule out a non-zonotopal \(A\in\mathcal P^2\).
- It does not prove that the equality-case zonotope
  \((1/14)Z_{K_{11}}\) is realizable in (1).
- It does not make the graphical block catalogue complete.
- Novelty has not been adjudicated and no priority claim is made.
