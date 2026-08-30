# G-0084 fresh-context hostile referee report

## Verdict

**CONSISTENT**, at T1 only (fresh context, same model family).  I found no
mathematical defect in Theorem 2 or Theorem 5 after attacking the stated
definitions, the cited conventions, and the proposed escape routes.  This is
not a T2 review and does not promote any MAX11 claim.

Reviewed object:

- source commit: `570850c` (`G-0084: delimit symmetrization completeness`);
- file: `artifacts/math/G-0084/SYMMETRIZATION_COMPLETENESS_BOUNDARY.md`;
- source and current-worktree SHA-256:
  `56a3f0d970448a247a3ef117401996c7fe4683cb343db982882318e654aede25`;
- the file is byte-identical between `570850c` and the review-time HEAD.

The verdict is limited to correctness of the stated derivations.  It gives no
novelty standing and no evidence that MAX11 is or is not representable by an
unrestricted two-hidden-layer ReLU network.

## Rubric exercised

- `statement-match`
- `quantifier-scope`
- `every-nontrivial-inference`
- `edge-and-degenerate-cases`
- `hidden-assumptions`
- `imported-theorem-conditions`
- `symbol-stability`

The expected break attacked first was that a coordinate permutation might
change the sorted-cone branch selection or permit a degree-five block to
manufacture the claimed mass-six hyperplane.  It does neither.

## 1. Theorem 2 survives

For one second-layer preactivation

\[
g=\sum_r\beta_r\rho(w_r\mathbin\cdot x),
\]

the positive and negative coefficient sets give zonotopes \(P,Q\) with
\(g=h_P-h_Q\).  Therefore

\[
\rho(g)=\max(0,h_P-h_Q)
       =\max(h_Q,h_P)-h_Q
       =h_{\operatorname{conv}(P\cup Q)}-h_Q.
\]

This calculation is exact for zero coefficients and for empty positive or
negative sets (the singleton-zero convention handles both).  Arbitrary signs
in the output layer are legitimate in the real virtual-support-function
space.  Summing the units and applying the Reynolds operator gives (1) and
(2); the inverse in
\(h_{\sigma P}(x)=h_P(\sigma^{-1}x)\) disappears because inversion permutes
the whole finite group.

The bias-removal hypothesis matches Hertrich--Basu--Di Summa--Skutella,
Proposition 2.3: their proof states that homogenizing every layer preserves a
positively homogeneous network function (`literature/papers/2105.14835.txt`,
lines 406--442).  No convexity of the final function is needed.  The virtual
polytope/support-function bijection used here is also the one stated in
Grillo--Hofmann, Lemma 5 (`literature/papers/2510.14068.txt`, lines 315--434).

The theorem correctly stops at orbit averages of arbitrary real zonotopal
virtual atoms.  Neither cited source supplies coordinate-pair generators,
integer multiplicities, equal branch degree, degree five, or a network-
independent finite dictionary.

## 2. Lemma 3 survives every permutation and loop convention

Fix a strict sorted chamber and a coordinate permutation.  Each
\(m_{pq}(\sigma x)\), including a loop \(p=q\), is one fixed coordinate on a
neighborhood inside that chamber.  A degree-\(k\) branch is consequently
\(a\cdot x\) for a nonnegative integer count vector with
\(\lVert a\rVert_1=k\).  For two branches, \(d=b-a\) has coordinate sum zero
and

\[
\mu(d)=\sum_{d_i>0}(b_i-a_i)\leq \sum_i b_i=k.
\]

Primitive reduction cannot increase this mass.  A finite linear combination
can cancel a kink but cannot create one at a point where every summand is
locally affine.  Braid-wall kinks do not escape this argument because all
points used in Theorem 5 lie in the open sorted chamber and hence have an
ordinary neighborhood contained in it.

This is compatible with the exact chamber reduction in Rueß et al.
(`literature/papers/2607.21651.txt`, lines 315--395) and with Wang--Basu,
Lemma 1.2 (`literature/papers/2608.25221.txt`, lines 124--188).

## 3. Theorem 5 survives

The normalization is exact: there are \(11\cdot10\cdot9=990\) ordered
distinct triples, every branch gains \(6t\), and \(5940=6\cdot990\).  The
support polytope is the stated scaled Minkowski sum of segments, and all its
points have coordinate sum one.

Loops have the intended semantics.  Six copies of \((i,i)\) give \(6x_i\);
five copies of \((j,j)\) and one of \((\ell,\ell)\) give \(5x_j+x_\ell\).
The full orbit of one labelled seed contains each ordered triple exactly
\(8!\) times: coefficients \(6,5,1\) distinguish \(i,j,\ell\), so the
stabilizer fixes those three labels and freely permutes the remaining eight.
Thus \(G\in\mathcal V_{11,6}\) with the stated scaling.

For

\[
v=6e_2-5e_1-e_3,
\]

the primitive signed mass is six.  The displayed point
\((0,1,6,7,\ldots,14)\) is strictly sorted and lies on \(v^\perp\), so the
hyperplane really enters the chamber interior.  No degree-five count
difference can define this hyperplane, since proportional primitive integer
normals have the same signed mass.

Among the 990 normals \(6e_i-5e_j-e_\ell\), only
\((i,j,\ell)=(2,1,3)\) is proportional to \(v\).  Positive proportionality
fixes the uniquely valued coefficients \(6,-5,-1\); negative proportionality
would have two positive coordinates and is impossible.  After removing the
finitely many other orbit and degree-five hyperplanes, a generic point remains
in \(v^\perp\cap C^\circ\).  At that point exactly one summand contributes the
nonzero gradient jump \(v/5940\).  An affine function cannot alter it.
Therefore

\[
G\notin\mathcal V_{11,5}+\operatorname{Aff}(\mathbb R^{11}).
\]

The ordinary-network convention also checks out.  Each summand has the exact
one-hidden-layer identity

\[
\max(6x_i,5x_j+x_\ell)
=\rho(6x_i-5x_j-x_\ell)
 +\rho(5x_j+x_\ell)-\rho(-5x_j-x_\ell).
\]

Its hidden outputs are nonnegative, so a second identity ReLU layer embeds it
in a standard two-hidden-layer network without skips.  This is stronger than
merely appealing to the rank-two maxout conversion.

## 4. A stronger theorem follows from the same proof

The \(n=11\), degree-six instance is a specialization of a strict consecutive
degree hierarchy.  For every \(n\geq3\) and \(k\geq1\), define

\[
G_{n,k+1}(x)=
\frac{1}{(k+1)n(n-1)(n-2)}
\sum_{i,j,\ell\ \mathrm{pairwise\ distinct}}
\max\{(k+1)x_i,\;kx_j+x_\ell\}.
\]

Then \(G_{n,k+1}\in\mathcal V_{n,k+1}\), it is symmetric, convex and
positively homogeneous, and it obeys
\(G_{n,k+1}(x+t\mathbf1)=G_{n,k+1}(x)+t\).  Its chamber normal

\[
(k+1)e_2-ke_1-e_3
\]

is primitive of signed mass \(k+1\) and meets the open sorted chamber at, for
example, \(x_1=0,x_2=1,x_3=k+1\), followed by any strictly larger remaining
coordinates.  Degree \(k\) cannot have that hyperplane.  For \(k>1\), the
coefficient pattern makes the contributing ordered triple unique.  For
\(k=1\), swapping \(j\) and \(\ell\) gives the same normal, but the two equal
summands have positive coefficients and their jumps add rather than cancel.
The generic-hyperplane argument therefore proves

\[
G_{n,k+1}\notin\mathcal V_{n,k}
                  +\operatorname{Aff}(\mathbb R^n).
\]

Conversely, adding the same loop \((p,p)\) to both branches of a degree-\(k\)
seed gives

\[
\Phi_{A\cup\{(p,p)\},B\cup\{(p,p)\}}
=\Phi_{A,B}+x_p.
\]

After a full orbit sum, the added term is
\((n-1)!\sum_qx_q\), which is affine.  Hence

\[
\mathcal V_{n,k}+\operatorname{Aff}
\subsetneq
\mathcal V_{n,k+1}+\operatorname{Aff}
\qquad(n\geq3,\ k\geq1).
\]

This general theorem is a worthwhile structural corollary and a clean Lean
target.  It still says nothing about whether the hinge-free function MAX11
lies at degree five or has an unrestricted two-hidden-layer representation.

## 5. GNF and DR5-MAX

The implication

\[
e_{11}\in\mathcal L_*\Longrightarrow e_{11}\in\mathcal L_5
\]

is logically the weakest *additional proposition relative to the fixed
premise* \(e_{11}\in\mathcal L_*\) that forces the desired conclusion: any
standalone proposition \(S\) satisfying
\(e_{11}\in\mathcal L_*\wedge S\Rightarrow e_{11}\in\mathcal L_5\)
entails this implication.  That minimality is propositional, not a new
structural reduction.

Given GNF, averaging its finite variable-degree graphical atoms places MAX11
in \(\mathcal V_{11,*}\).  Its restriction to the open sorted chamber is
\(x_{11}\), so all interior hinge jumps cancel and the premise of DR5-MAX
holds.  DR5-MAX then supplies a degree-five hinge-free orbit combination.
Continuity extends equality from \(C^\circ\) to the closed chamber, and
symmetry extends it globally.  Thus `GNF + DR5-MAX` is sufficient as stated.

However, it is not a material advance toward either missing theorem:

- GNF is still the arbitrary-network-to-graphical-pair normal-form problem,
  including arbitrary real directions and virtual cancellations.
- Once GNF supplies its premise, DR5-MAX is almost exactly the remaining
  target-specific degree-five conclusion.

The wording “weakest” should therefore always retain the qualifier “within
the pair-max target fibre, relative to the all-degree premise.”  It is not the
weakest conceivable route from arbitrary ReLU networks to MAX11.

No cited primary source makes either statement trivial.  Hertrich et al. and
Grillo--Hofmann retain arbitrary virtual atoms.  Rueß et al. introduce the
restricted pair-max ansatz rather than prove it complete.  Wang--Basu state
explicitly that their corresponding linear system is only sufficient and “is
not a complete characterization” (`literature/papers/2608.25221.txt`, lines
524--538).  I found no source in the certified local corpus that proves or
refutes DR5-MAX.

## 6. Novelty posture and obligations

The exact n=11 counterexample was not located verbatim in the certified local
corpus or in a dated 2026-08-30 arXiv-focused query sweep.  That is not a
novelty audit.  Its essential ingredients are already very close to
Rueß et al.'s chamber expansion and Wang--Basu's degree-\(k\) count-vector
lemma, and the proof generalizes immediately as above.  The defensible posture
is therefore:

- mathematically useful exact boundary result;
- likely an elementary incremental corollary of the emerging pair-max
  literature unless a broader novelty audit establishes otherwise;
- no claim of a new lower-bound paradigm;
- no MAX11 solution or lower bound.

Nonblocking presentation obligations if the source is revised:

1. qualify “weakest” exactly as in Section 5 above;
2. add the one-line continuity step from \(C^\circ\) to \(C\) in the DR5-MAX
   sufficiency argument;
3. consider promoting the strict all-\(n\), all-\(k\) filtration theorem as a
   separate claim and Lean target, with a separate novelty search;
4. retain the current explicit no-claim boundary.

None of these changes is needed to repair Theorem 2 or Theorem 5.
