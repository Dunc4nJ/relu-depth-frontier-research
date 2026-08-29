# Exact obstruction to the isolated/common-padding induction

## Statement

Fix `N > m >= 1`.  Start from exact identities for `MAX_m`, insert their
variables into proper subsets of `{1,...,N}`, take arbitrary linear
combinations of coordinate-permutation orbit sums, and optionally add the
same multiset of pairwise-max terms to both arguments of any outer maximum.
No function produced by this procedure is `MAX_N`.

This statement concerns this linear, equivariant induction language.  It does
not cover asymmetric topology-dependent padding, nonlinear composition, or a
new degree-five MAX11 identity.

## Proof

For a nonempty subset `S` write

```text
M_S(x) = max_{i in S} x_i,
H_r(x) = sum_{|S|=r} M_S(x).
```

Inserting an exact `MAX_m` identity into every injection and then summing over
the coordinate-permutation orbit produces a scalar multiple of `H_m`.
Different insertion arities and coefficients therefore remain in the span of
`H_1,...,H_{N-1}`.

Common-edge padding does not escape this span.  Pointwise,

```text
max(U+C,V+C) = C + max(U,V).
```

Here `C` is a sum of terms `max(x_i,x_j)`, including `x_i` when `i=j`.
After coordinate symmetrization these contributions are scalar multiples of
`H_2` and `H_1`.  Repeating the operation still adds only proper-subset
maxima.

It remains to show that `MAX_N` is not in their span.  On the chamber
`x_1 <= ... <= x_N`,

```text
H_r(x) = sum_{j=r}^N binom(j-1,r-1) x_j.
```

If `x_N = sum_{r=1}^{N-1} c_r H_r(x)`, comparison of the coefficient of
`x_1` gives `c_1=0`.  Inductively, after `c_1=...=c_{j-1}=0`, comparison of
the coefficient of `x_j` gives `c_j=0` for every `j<N`.  The coefficient of
`x_N` on the right is then zero, a contradiction.

Thus isolated-variable orbit induction plus common-edge padding cannot lift
MAX5 or MAX6 to MAX10, nor MAX10 to MAX11.  This does **not** obstruct leaf
padding or any operation that introduces a genuinely new outer-max hinge;
those require the separate finite structural tests in `audit_report_v1.json`.

## Retry predicate

Retry only with an explicitly specified equivariant operator that introduces
new hinge directions rather than only proper-subset maxima.  Its complete
orbit-incidence map, including templates assigned zero coefficient, must pass
an exact rational reconstruction and a complete arbitrary-chamber hinge
replay.  Agreement on a finite sample is not enough.
