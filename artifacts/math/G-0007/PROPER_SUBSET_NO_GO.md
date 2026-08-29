# No linear proper-subset lift for MAX

## Statement

Let N >= 2. There is no real linear combination of functions

    x -> max_{i in S} x_i

over nonempty proper subsets S of {1,...,N} that equals

    x -> max(x_1,...,x_N)

for every real x.

This rules out the tempting linear strategy “apply a MAX(N-1)
representation to every (N-1)-subset and recombine.” It does not rule out
nonlinear composition, auxiliary variables, or genuinely new atoms.

## Proof

First consider a symmetric linear combination. For 1 <= r <= N-1 define

    F_r(x) = sum_{|S|=r} max_{i in S} x_i.

On the chamber x_1 <= x_2 <= ... <= x_N, the coordinate x_j is the maximum
of exactly C(j-1,r-1) subsets of size r. Hence

    F_r(x) = sum_{j=r}^N C(j-1,r-1) x_j.

Suppose that

    max(x_1,...,x_N) = sum_{r=1}^{N-1} c_r F_r(x).

Compare coefficients on the ordered chamber. The coefficient of x_1 gives
c_1=0. Inductively, after c_1=...=c_{j-1}=0, the coefficient of x_j for
j<N is c_j C(j-1,j-1)=c_j, so c_j=0. Thus every c_r is zero. But then the
coefficient of x_N on the right is zero, while it is one on the left, a
contradiction.

It remains to remove the symmetry assumption. If an arbitrary linear
combination over proper subsets equalled MAX_N, average that identity over
all N! coordinate permutations. The right-hand side MAX_N is unchanged.
Every coefficient on subsets of a fixed cardinality r becomes the same,
so the averaged left-hand side has the form sum_r c_r F_r. The preceding
triangular argument gives the same contradiction.

Therefore no such linear proper-subset representation exists. QED.
