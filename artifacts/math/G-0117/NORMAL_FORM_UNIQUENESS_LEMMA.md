# Ordered-chamber ReLU normal-form uniqueness

## Statement

Let

```text
C° = {x in R^n : x_0 < x_1 < ... < x_(n-1)}.
```

Let `D` be a finite set of nonzero integer vectors `d in Z^n` satisfying:

1. `sum_i d_i = 0`;
2. `gcd_i |d_i| = 1`;
3. the first nonzero coordinate of `d` is positive; and
4. some proper prefix sum `P_j(d)=sum_(i=0)^j d_i` is negative.

Then the functions

```text
{ReLU(d.x) : d in D}
```

are linearly independent modulo linear functions on `C°`.  Precisely, if

```text
ell.x + sum_(d in D) c_d ReLU(d.x) = 0             for every x in C°,
```

then every `c_d=0` and `ell=0`.

The same conclusion holds after subtracting any fixed linear target.  Hence a
nonzero G-0117 hinge residual is an exact obstruction to equality with its
linear target on the ordered chamber; if every hinge residual vanishes, the
remaining equality is decided by the explicit linear vector.

## Proof

Put `g_j=x_(j+1)-x_j` for `0 <= j <= n-2`.  On `C°`, every `g_j>0`.  Because
`sum_i d_i=0`, summation by parts gives

```text
d.x = -sum_(j=0)^(n-2) P_j(d) g_j.                 (1)
```

For a first-positive nonzero `d`, its first nonzero prefix sum is positive.
Condition 4 supplies a negative prefix sum.  Thus the coefficients
`-P_j(d)` in (1) have both signs.  Choosing all gaps positive and adjusting
one gap from each sign class gives a solution of `d.x=0`; indeed the set

```text
H_d ∩ C°,       H_d={x:d.x=0},
```

contains a relatively open subset of the hyperplane `H_d`.

Distinct vectors in `D` define distinct hyperplanes.  To see this, coincident
hyperplanes would make their normals nonzero scalar multiples.  Integer
primitivity restricts the scalar to `+1` or `-1`, and first-positive
orientation excludes `-1`.

Fix `d in D`.  Since `D` is finite and no other `H_e` equals `H_d`, the
relatively open set `H_d ∩ C°` is not covered by the finitely many proper
subspaces `H_d ∩ H_e`, `e != d`.  Choose

```text
x* in (H_d ∩ C°) \ union_(e != d) H_e.
```

A sufficiently small ball around `x*` remains inside `C°` and meets no other
hinge hyperplane.  Across `H_d` in this ball, the gradient of
`ReLU(d.x)` jumps by `d`; every other hinge term and the linear term have the
same gradient on both sides.  Therefore the gradient jump of the displayed
zero function is exactly `c_d d`.  It must vanish, and `d != 0`, so `c_d=0`.

This argument applies independently to every `d in D`.  The identity then
reduces to `ell.x=0` on the nonempty open set `C°`, which forces `ell=0`.

## Symmetry consequence used by G-0117

Each G-0117 atom and the MAX target are invariant under coordinate
permutations.  Every `x in R^n` can be permuted into the closed ordered
chamber.  Equality on `C°` extends to its closure by continuity, and symmetry
then extends it to all of `R^n`.  Consequently:

- an exact zero ordered-chamber normal form proves the corresponding global
  function identity, before the separate architecture-compilation step;
- a nonzero active hinge coefficient proves that certificate is not a global
  identity; and
- neither conclusion says that the fixed atom family is complete.

## Scope and dependencies

This lemma is elementary real piecewise-linear analysis.  It does not assert
that G-0117 generated every possible direction or atom.  Its only
implementation dependency is statement matching: `active_direction` must mean
condition 4, and direction normalization must enforce conditions 1–3.
