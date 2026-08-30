# G-0073: exact symmetric-profile gate for the Y-spoke family

## Why this is the next construction gate

G-0072 rejects the complete frozen asymmetric loop-edge/root-direction family
over both registered finite fields.  G-0073 changes the inner wall rather than
enlarging that failed catalogue.  Its new primitive

\[
Y_{k,\ell,11}=\max(2x_k,x_\ell+x_{11})
\]

has support three and the non-braid wall
\(x_\ell+x_{11}-2x_k=0\), while its distinguished MAX10 facet still exposes
\(2x_k\).  This is the smallest currently identified lift that escapes the
root-only obstruction.

For every one of the 252 pinned two-component MAX10 bases \((A,B)\), every
ordered cross-component pair \((k,\ell)\), and both outer orientations, the
raw subject contains

\[
\max(A+2x_k,B+Y_{k,\ell,11})
\quad\text{or}\quad
\max(A+Y_{k,\ell,11},B+2x_k).
\]

There are exactly 18,400 labelled seeds and 8,104 full-\(S_{11}\) orbits after
coordinate relabelling and global outer-branch swap.  Coefficients are free per
orbit.  MAX10 coefficients are **not** inherited.

## Exact normalization

Define

\[
\operatorname{Sym}_{\rm avg}(f)(x)
=\frac1{11!}\sum_{\sigma\in S_{11}} f(\sigma x).
\]

For a profile \(p=(c_0,c_1,c_2,c_3)\), let \(X_p\) be the distinct labelled
assignments of the multiset with \(c_i\) copies of level \(i\).  The integer
matrix stores

\[
M_{p,j}=\sum_{x\in X_p}\Phi_j(x)
=|X_p|\operatorname{Sym}_{\rm avg}(\Phi_j)(x_p),
\]

and target \(b_p=|X_p|\max(x_p)\).  The last three columns are the averaged
carrier orbits represented by \(x_1\), \(\max(x_1,x_2)\), and
\(\max(2x_1,x_2+x_3)\).

Thus emitted coefficients multiply `Sym_avg`.  A compiler that literally sums
all \(11!\) coordinate permutations must divide every emitted coefficient by
\(11!\).

## Exact decision rule

The 364 profile rows are necessarily rank deficient: the zero row vanishes,
and homogeneity/translation identities create proportional rows.  The program
therefore does not use an unreachable full-row-rank criterion.

It computes \(G=MM^T\) exactly over the integers and resolves the system over
\(\mathbb Q\).  Over \(\mathbb Q\),

\[
\operatorname{col}(G)=\operatorname{col}(M),\qquad
\ker(G)=\ker(M^T),
\]

because \(y^TGy=\|M^Ty\|^2\).  The only accepted outcomes are:

- `PROFILE_GATE_EXACT_Q_MEMBERSHIP`: sparse original-column coefficients solve
  all 364 rows.  Every selected column includes its materialized expression
  descriptor, and a stdlib `Fraction` replay is independent of the FLINT solve.
- `PROFILE_GATE_EXACT_Q_NONMEMBERSHIP`: a normalized exact row dual annihilates
  all 8,107 columns and sends the target to one.

Modular ranks at 1,000,003 and 1,000,033 are diagnostics only.  They do not
replace the exact rational resolution.

## Claim boundary and next fork

Exact nonmembership supplies a rational dual and therefore excludes a global
identity inside this frozen Y-spoke-plus-carriers family even with arbitrary
real output coefficients.  It is not an unrestricted two-hidden-layer lower
bound.

Exact membership is only a necessary finite-profile survivor.  It is not a
global CPWL identity.  Its sparse basic solution is one interpolant among many;
if that interpolant fails a later generic slice, the family is not thereby
rejected.  The correct continuation is constraint generation in the full
8,107-column coefficient space, followed by complete chamber/normal-form replay
and an explicit two-hidden-layer compiler.

## Controls

The frozen producer checks:

- the 252-base topology census and exact 18,400-seed count;
- complete pynauty orbit canonicalization plus 10,296 independent typed-DAG
  NetworkX VF2 checks;
- exhaustive nested/flattened Y identities and a coefficient mutant;
- literal-versus-vectorized evaluation on 6,144 Boolean seed-points;
- coordinate relabelling and outer-branch-swap invariance;
- facet exposure and a degree mutant;
- literal small-\(n\) permutation/profile normalization;
- constant-profile closed forms after multiprocessing assembly; and
- rank-deficient exact member and nonmember solver controls.

## Commands

Frozen subject identifiers:

- producer SHA-256: `333dba4065c08d54742177941305c13841e6237001f364cf5a68a9e4ec2ebf67`
- preflight scientific payload: `d440ecf8b5119f1c6b8f872444cb364995d1f4043513519d57fbbd3eeb3517b8`
- preflight artifact SHA-256: `05908cba9a9ea47ccda0d07f2fa5af630c38c7031986ede57cb6a78dad611e1d`
- environment manifest SHA-256: `12ad4b74f2736a883c562389d6ac50089ea07d5182593c7f75d564af80eb2a7c`

```bash
.venv/bin/python -B artifacts/math/G-0073/y_spoke_profile_gate.py \
  --self-test --skip-full-vf2

.venv/bin/python -B artifacts/math/G-0073/y_spoke_profile_gate.py \
  --preflight-only \
  --output artifacts/math/G-0073/y_spoke_orbit_preflight_v1.json.gz
```

The registered `--run` command and frozen script hash are recorded in the
experiment ledger only after the final preflight is committed and pushed.
