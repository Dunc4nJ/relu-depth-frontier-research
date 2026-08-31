# G-0118 triangular-chain interpretation

## Observation

The first three globally refuted prefix candidates failed, in order, at

```text
(0,0,0,0,0,0,0,0,1,-5,4)
(0,0,0,0,0,0,0,0,1,-4,3)
(0,0,0,0,0,0,0,0,1,-3,2)
```

and iteration 4 added the next row

```text
(0,0,0,0,0,0,0,0,1,-2,1).
```

This is a real deterministic pattern, but it is weak evidence for convergence.
It is largely explained by the frozen signed-lexicographic coordinate order.

## Exact elementary enumeration

A degree-five raw word has coordinates in `[-5,5]`.  Restrict to directions
supported on the final three ranks, write the nonzero suffix as `(a,b,c)`, and
impose the normal-form conditions:

1. `a+b+c=0`;
2. the first nonzero coordinate is positive;
3. `gcd(|a|,|b|,|c|)=1`;
4. some proper prefix sum is negative, so the hinge is active on the ordered
   cone.

Exhaustive integer enumeration gives the following signed-lexicographic list:

```text
(1,-5,4)
(1,-4,3)
(1,-3,2)
(1,-2,1)
(2,-5,3)
(2,-3,1)
(3,-5,2)
(3,-4,1)
(4,-5,1)
```

The tempting continuation `(1,-1,0)` is absent because all its proper prefix
sums are nonnegative; it is linear on the ordered cone rather than an active
hinge direction.

Thus the observed four-step chain is exactly the initial `a=1` block of the
allowed top-three-coordinate order.  The one-row CEGIS rule deliberately chose
the first nonzero global residual, so this pattern can arise even when the
successive finite members are not approaching a global identity in any useful
metric.

## Epistemic consequence

- Downgrade the chain from “mild evidence of a recurrence” to “primarily an
  ordering diagnostic.”
- Do not extrapolate a fifth one-row correction or infer eventual termination.
- The preregistered Batch32 replay remains informative because it crosses this
  exhausted initial block and exposes a broader residual profile in one frozen
  pass.

This note interprets already disclosed iterations.  It does not inspect or
predict the iteration-4 replay outcome, prove membership of the frozen family,
or establish a global MAX11 identity.
