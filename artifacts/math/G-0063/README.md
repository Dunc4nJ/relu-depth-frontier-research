# G-0063 — a simplex-asymmetry lower bound on any depth-two stabilizer

## Result

Let \(\Delta=\Delta_n\) be an \(n\)-simplex and suppose

\[
\Delta+A=B,\qquad A,B\in\mathcal P_{n,d}.
\]

Write

\[
p=2^d-1,\qquad
t=\lambda_\Delta(A),\qquad
r=\rho_\Delta(A)=\frac{\lambda_{-\Delta}(A)}{\lambda_\Delta(A)}.
\]

When \(n>p\), every such identity necessarily satisfies

\[
\frac1p\le r<p,
\qquad
t\ge \frac{n-p}{p-r}
      \ge \frac{n-p}{p-p^{-1}}.
\]

For the campaign target \(\operatorname{MAX}_{11}\), the polytope is
\(\Delta_{10}\), so \(n=10,d=2,p=3\). Therefore

\[
\boxed{\lambda_\Delta(A)\ge\frac{21}{8}}.
\]

If \(A\) is a zonotope (or any centrally symmetric non-singleton convex
body), then \(r=1\), and the stronger specialization is

\[
\boxed{\lambda_\Delta(A)\ge\frac72}.
\]

This is a **necessary size condition**, not a MAX11 lower bound. A large
centrally symmetric stabilizer can dilute the simplex asymmetry, so the
invariant does not rule out \(\Delta_{10}+A=B\).

## Definitions and exact derivation

For convex compact \(L\) and a convex body \(K\),
\(\lambda_K(L)\) is the least nonnegative scale \(s\) for which some
translate of \(sK\) contains \(L\). Bakaev--Yehudayoff define

\[
\rho_\Delta(L)=\lambda_{-\Delta}(L)/\lambda_\Delta(L)
\]

for non-singleton \(L\). Their Theorem 7 gives
\(\rho_\Delta(P)\le 2^d-1=p\) for \(P\in\mathcal P_{n,d}\) in the stated
dimension range. Reflection preserves \(\mathcal P_{n,d}\), and

\[
\rho_\Delta(-A)=\rho_\Delta(A)^{-1},
\]

so applying the same theorem to \(-A\) gives \(r\ge p^{-1}\).

Every simplex is outer additive (Definition/Theorem 6 in the source). Apply
this once with reference body \(\Delta\) and once with reference body
\(-\Delta\). Since

\[
\lambda_\Delta(\Delta)=1,
\qquad
\lambda_{-\Delta}(\Delta)=n,
\]

the identity \(\Delta+A=B\) gives

\[
\lambda_\Delta(B)=1+t,
\qquad
\lambda_{-\Delta}(B)=n+rt,
\qquad
\rho_\Delta(B)=\frac{n+rt}{1+t}.
\]

The depth bound \(\rho_\Delta(B)\le p\) now implies

\[
n-p\le(p-r)t.
\]

Because \(n>p\), this forces \(r<p\) and yields both displayed lower bounds.

## Why the source class is exactly the campaign class

The paper defines \(\mathcal P_{n,0}\) as points and
\(\mathcal P_{n,d}\) as finite Minkowski sums of
\(\operatorname{conv}(K\cup L)\) with \(K,L\in\mathcal P_{n,d-1}\).
This is the same inductive polytope class denoted \(\mathcal P^d\) in the
campaign. Its Section 6.1 also states the virtual-polytope correspondence:
the hidden-layer count of \(h_X\) is the least \(d\) for which
\(X+P=Q\) with \(P,Q\in\mathcal P_{n,d}\). Thus the theorem applies directly
to the campaign's \(A/B\), after passing from \(N\) coordinates to the
centered coordinate simplex in its \((N-1)\)-dimensional affine span.

## Exact controls on the public MAX5--MAX10 certificates

The verifier groups every negative certificate term into \(A\) and every
positive term into \(B\), then evaluates both outer radii exactly. It uses the
centered coordinate simplex

\[
\Delta=\operatorname{conv}\{e_i-\mathbf1/N\}
\]

whose facet normals in \(\sum_i x_i=0\) are
\(q_i=\mathbf1-Ne_i\). For an \(S_N\)-symmetrized certificate side, Lemma 13
of the source reduces \(\lambda_\Delta\) and \(\lambda_{-\Delta}\) to support
evaluations at \(q_i\) and \(-q_i\). Only the \(N\) possible preimages of the
distinguished coordinate are needed; no sampled grid or floating point is
used.

Run:

```bash
.venv/bin/python -B artifacts/math/G-0063/verify_simplex_asymmetry_bound.py \
  --check-frozen
```

The controls pass for all six public certificates. In every case they replay
the exact outer-additivity identities

\[
\lambda_\Delta(B)-\lambda_\Delta(A)=1,
\qquad
\lambda_{-\Delta}(B)-\lambda_{-\Delta}(A)=N-1.
\]

The known witnesses are far above the new lower bound; therefore they validate
the derivation but provide no evidence that the bound is sharp.

## Certified source

- Egor Bakaev and Amir Yehudayoff, *A simplex-based measure of symmetry*,
  arXiv:2607.03815.
- Archived PDF: `source/2607.03815.pdf`
- SHA-256:
  `4875ffd0fdc33624d8da00fa87709b88a6087587d27db21571f447aa23d2182b`
- Definitions and main statements: PDF pp. 2--7; depth/NN correspondence and
  proof: PDF pp. 25--27.

## Claim boundary and construction consequence

This artifact proves no unrestricted MAX11 representation and no new
impossibility theorem. It retires only stabilizer candidates below the stated
outer-radius threshold. Combined with the independent G-0064 face-gluing
constraint, the next positive object must be a **full-dimensional** stabilized
depth-two block, large enough to pass this bound, whose eleven facet faces
obey the generator restrictions and whose every three-way-or-higher tie is
carried by a noncentrally symmetric tied block.
