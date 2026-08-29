# G-0067 — the maximum-coordinate subdivision cell is not in `P^2`

## Bottom line

The canonical face-to-face subdivision

\[
\Delta_d=\bigcup_{i=0}^{d}\{x\in\Delta_d:x_i\ge x_j\text{ for every }j\}
\]

does **not** supply the `P^2` subdivision sought for MAX11.  Every maximal
cell is affinely equivalent to

\[
D_d=\{y\in\mathbb R^d_{\ge0}:\textstyle\sum_k y_k+y_i\le1
\text{ for }i=1,\ldots,d\}.
\]

This note computes the complete Minkowski type cone of `D_d` and proves

\[
D_d\notin P^2\qquad(d\ge5).
\]

In particular, `D_10` cannot be used with Lemma 10 of Bakaev--Brunck--
Hertrich--Stade--Yehudayoff to obtain a two-hidden-layer representation of
MAX11.  This kills one natural subdivision; it does **not** rule out another
`P^2` subdivision or an unrestricted virtual-`P^2` identity for the simplex.

## 1. The cell and its normal fan

Fix the cell where `x_0` is a largest barycentric coordinate and eliminate
`x_0=1-sum_i y_i`.  This gives `D_d` above.  Its `2d` facets have normals

\[
\ell_i=-e_i,\qquad u_i={\bf1}+e_i,
\]

with supports zero and one, respectively.  Its vertices are indexed by
subsets `T subseteq [d]`:

\[
v_T=\frac1{|T|+1}{\bf1}_T.
\]

At `v_T`, the upper facets indexed by `T` and the lower facets indexed by its
complement are active.  Hence `D_d` is simple and its normal fan is
simplicial.

## 2. Complete closed Minkowski type cone

Let `R` be a Minkowski summand of `D_d`.  The normal fan of `D_d` refines the
normal fan of `R`, including when `R` is lower-dimensional.  Here is a
self-contained justification of the step.  If `D_d=R+S`, then
`h_D=h_R+h_S`.  On each maximal normal cone `sigma_T` of `D_d`, `h_D` is
linear.  For `p,q in sigma_T` and `0<t<1`, convexity gives

\[
h_R(tp+(1-t)q)\le th_R(p)+(1-t)h_R(q)
\]

and the same inequality for `h_S`.  Their sums are equal because `h_D` is
linear, so both inequalities must be equalities.  Hence `h_R` and `h_S` are
linear on every `sigma_T`.  This is exactly the normal-fan refinement
statement and does not use full dimensionality of either summand.

Translate `R` so that its support on every `ell_i` is zero, and write `c_i`
for its support on `u_i`.  Because each `sigma_T` is a full-dimensional
simplicial cone whose rays are the appropriate `ell_i,u_i`, these `2d`
support values determine the linear form on every maximal cone and therefore
the complete support function of `R`.

For a subset `T`, put `m=|T|`.  The gradient selected by the corresponding
maximal cone has zero coordinates off `T` and satisfies

\[
\sum_k y_k+y_i=c_i\quad(i\in T).
\]

Thus

\[
\sum_k y_k=\frac{\sum_{i\in T}c_i}{m+1}.
\]

Requiring this point to satisfy every lower and upper inequality gives,
uniformly for every `i` and every `A subseteq [d] setminus {i}`,

\[
(|A|+1)c_i\ge\sum_{j\in A}c_j.                 \tag{1}
\]

Taking `A=[d] setminus {i}` shows that (1) implies

\[
(d+1)c_i\ge C:=\sum_jc_j.                       \tag{2}
\]

Conversely, set

\[
L=\frac{C}{d+1},\qquad \lambda_i=c_i-L.
\]

Condition (2) says `lambda_i>=0`, and summing gives `sum_i lambda_i=L`.
For any `A` as in (1),

\[
(|A|+1)c_i-\sum_{j\in A}c_j
=L+(|A|+1)\lambda_i-\sum_{j\in A}\lambda_j
\ge (|A|+2)\lambda_i\ge0.
\]

Therefore (1) and (2) are equivalent, and the complete closed type cone,
modulo translations, is the nonnegative orthant in the `lambda_i`.

Its `i`th extreme ray has

\[
c^{(i)}=(1,\ldots,1,2,1,\ldots,1).
\]

The associated ray polytope is

\[
P_i=\operatorname{conv}(e_i,D_{d-1}^{(i)}),                 \tag{3}
\]

where `D_{d-1}^{(i)}` lies in `y_i=0`.  Indeed, all subset vertices whose
index set contains `i` collapse to `e_i`; the others reproduce `D_{d-1}`.
The target support vector `(1,...,1)` has every
`lambda_i=1/(d+1)`, so, with the chosen translations,

\[
D_d=\frac1{d+1}\sum_{i=1}^d P_i.                            \tag{4}
\]

Equation (4) is an exact decomposition, but its ray summands are not the
required two-zonotope joins.  The next lemma rules out not only the rays but
every nonzero point of the type cone.

## 3. No type-cone summand is primitive `P^2` when `d>=5`

For nonzero `c` satisfying (2), `L>0`, so every `c_i>0`.  Define the `d` axis
points

\[
a_i=\frac{c_i}{2}e_i.                                      \tag{5}
\]

Each `a_i` is a vertex of the corresponding summand polytope `P(c)`.  It lies
on the `d-1` independent lower facets with indices different from `i` and on
upper facet `i`.  Its remaining upper inequalities follow from the
two-coordinate instance `2c_j>=c_i` of (1).

Suppose, for contradiction, that

\[
P(c)=\operatorname{conv}(Z_0\cup Z_1),                     \tag{6}
\]

where `Z_0,Z_1` are translated zonotopes.  Every extreme point in (5) belongs
to one of the two branches.  A zonotope is centrally symmetric, so consider
one branch, with center `q`, containing three distinct axis vertices
`a_i,a_j,a_k`.

The reflection `2q-a_r` lies in `P(c)` for each
`r in {i,j,k}`.  Nonnegativity of its `r`th coordinate gives

\[
q_r\ge c_r/4.                                               \tag{7}
\]

Apply upper inequality `j` to the reflection of `a_i`, where `i!=j`:

\[
2\sum_mq_m-c_i/2+2q_j\le c_j,
\]

or

\[
\sum_mq_m+q_j\le c_j/2+c_i/4.                              \tag{8}
\]

But (7), using also the third index `k`, yields

\[
\sum_mq_m+q_j
\ge q_i+2q_j+q_k
\ge c_i/4+c_j/2+c_k/4,
\]

which strictly contradicts (8) because `c_k>0`.  Consequently one centrally
symmetric branch can contain at most two of the axis vertices.  Two branches
can contain at most four.  Equation (6) is therefore impossible for `d>=5`.

Finally, in any expression of `D_d` as a Minkowski sum of primitive `P^2`
blocks, each block is a Minkowski summand of `D_d` and hence belongs, after a
translation, to the closed type cone above.  This includes boundary and
lower-dimensional candidates by the support-function argument in Section 2.
If `c=0`, the translated support function is zero on every ray and hence,
by linearity on the complete fan, zero in every direction; the summand is the
single point `{0}`.  Every nonpoint block therefore has nonzero `c` and is
excluded by the preceding argument.  A sum of point blocks cannot equal the
positive-dimensional `D_d`.  This proves the theorem.

## 4. Exact controls and sharp boundary of this obstruction

Run:

```bash
.venv/bin/python artifacts/math/G-0067/verify_pair_subdivision_nogo.py
```

The verifier uses exact rational arithmetic and Z3 linear real arithmetic to
check:

- equivalence of (1) and (2) for every `2<=d<=10`;
- the orthant-ray decomposition and the vertex description (3);
- UNSAT for one centrally symmetric branch reflecting any three specified
  axis vertices, with arbitrary nonnegative type-cone coefficients;
- SAT for a two-branch cover of the four axis vertices at `d=4`;
- UNSAT for two-branch covers at `d=5`, `d=6`, and `d=7`.

The `d=4` SAT case is a hostile boundary control: the two pairs of axis
vertices can be covered by two centrally symmetric segments.  It shows only
that this necessary obstruction stops at four axes, not that `D_4` is in
`P^2`.  The requested `d=6` and `d=7` reruns both remain UNSAT; the exact
argument is actually sharp one dimension earlier, between `d=4` and `d=5`.

## Scope and epistemic status

**Proved here:** the complete Minkowski type cone of the explicit polytope
`D_d`, and `D_d notin P^2` for every `d>=5`.

**Killed:** the maximum-coordinate/pair-subdivision route to a `P^2`
subdivision of `Delta_10`.

**Not proved:** nonexistence of another `P^2` subdivision of `Delta_10`,
nonexistence of a virtual identity `Delta_10+A=B` with `A,B in P^2`, or any
unrestricted MAX11 lower bound.

The only external result used to connect a `P^2` subdivision to network depth
is Lemma 10 of:

- Bakaev, Brunck, Hertrich, Stade, and Yehudayoff, *Better Neural Network
  Expressivity: Subdividing the Simplex*, arXiv:2505.14338.
- Local PDF: `literature/papers/2505.14338.pdf`, SHA-256
  `84d730de9c29a96b4e158723c10b5b4f6e5da799869ad47311ea6c26f251f54b`.
- Local extracted text: `literature/papers/2505.14338.txt`, SHA-256
  `ada6147683a2e2f8fd9fb8881f56026ac48468b1d6092887169ea159fa046183`.

No novelty claim is made for the subdivision itself or for the elementary
polyhedral argument until a dedicated literature audit is complete.
