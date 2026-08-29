# Proper-signed-core obstruction for symmetric pair-orbit certificates

## Theorem

Let `N >= 2`.  For a function `h : R^r -> R`, define its unnormalised
injection symmetrisation

```text
U_h(x) = sum_{f:[r] -> [N] injective} h(x_{f(1)},...,x_{f(r)}).
```

If every `r < N`, no finite real linear combination of such functions equals
`MAX_N` on `R^N`.

Consequently, in the degree-`k` pair-orbit ansatz

```text
Phi[A,B] = max(sum_{e in A} max_e, sum_{e in B} max_e),  |A|=|B|=k,
```

cancel the common edge multiset `C=A intersect B` and call `(A-C,B-C)` the
signed core.  Any exact symmetric pair-orbit certificate for `MAX_N` must use
at least one term whose signed core touches all `N` coordinates.  It is not
enough that the full pair touches all coordinates through common padding.

## Proof

Evaluate at a binary vector with `t` ones.  For a subset `R` of the `r`
kernel labels, exactly

```text
(t)_{|R|} (N-t)_{r-|R|}
```

injections send precisely `R` to one-coordinates.  Therefore the binary
profile is

```text
G_h(t) = sum_{R subset [r]} (t)_{|R|}(N-t)_{r-|R|} h(1_R),
```

up to the harmless factor `(N-r)!` when using a full `S_N` permutation sum
rather than an injection sum.  This is a polynomial in `t` of degree at most
`r`.  If `r<N`, its `N`th finite difference vanishes.  The conclusion is
unchanged under arbitrary real linear combinations.

For `MAX_N`, the binary profile is `G(0)=0` and `G(t)=1` for `1<=t<=N`, so

```text
Delta^N G(0) = sum_{t=0}^N (-1)^(N-t) binom(N,t) G(t) = (-1)^(N+1) != 0.
```

Thus proper-support symmetrisations cannot equal `MAX_N`.

For a pair atom, write

```text
Phi[A,B] = sum_{e in C} max_e + Phi[A-C,B-C].
```

After full coordinate symmetrisation, a common loop is `(N-1)! F_1` and a
common nonloop is `2(N-2)! F_2`; both have zero `N`th finite difference for
`N>2`.  The remaining core is an `r`-variable kernel.  If it touches fewer
than `N` coordinates, the preceding argument applies.

When a symmetric function is linear on the ordered chamber with coefficient
vector `c=(c_1,...,c_N)`, its binary profile satisfies
`G(t)=c_{N-t+1}+...+c_N`, and the same finite difference is

```text
Lambda(c) = sum_{j=1}^N (-1)^(N-j) binom(N-1,j-1)c_j.
```

In general,

```text
Delta^N G(0) = (-1)^(N+1) Lambda(c).
```

For the target `N=11` the sign is positive.  This identifies the U-statistic
obstruction with G-0047's alternating-binomial functional, but the binary
proof does not require individual atoms to be braid-linear or their hinges to
have been decomposed.

## Exact scope

This is a necessary support condition, not a MAX11 solution or lower bound.
Full-signed-core atoms can have nonzero finite difference; they generally
also have non-braid hinges.  A successful construction must still cancel all
such hinges while retaining the required finite-difference direction.  The
argument also does not constrain unrestricted networks whose first-layer
weights depend on all coordinates.
