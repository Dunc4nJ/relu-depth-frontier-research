# G-0060 — Boolean Möbius charge forces one full-ancestor neuron

## Exact theorem

For `n >= 1`, write `1_S in R^n` for the indicator of `S subseteq [n]` and
define the full Boolean Möbius charge

```text
Delta_[n] f = sum_{S subseteq [n]} (-1)^(n-|S|) f(1_S).       (1)
```

Consider an arbitrary finite two-hidden-layer ReLU network, with every bias
and every real sign allowed,

```text
N(x) = c + sum_j a_j phi_j(x),
phi_j(x) = ReLU(beta_j + sum_i b_ji ReLU(gamma_i + w_i . x)). (2)
```

For an output-active second neuron `j`, let

```text
D_j = union_{i : b_ji != 0} support(w_i).                      (3)
```

Then an exact representation `N = MAX_n` has at least one index `j` with

```text
a_j != 0,  Delta_[n] phi_j != 0,  and  D_j = [n].              (4)
```

More exactly, its per-neuron charges obey the conservation law

```text
sum_j a_j Delta_[n] phi_j = Delta_[n] MAX_n = (-1)^(n+1).     (5)
```

For `MAX11`, the right side is exactly `1`.

### Proof, including arbitrary biases and real weights

If a function `h` is independent of coordinate `r`, pair every subset
`T subseteq [n]-{r}` with `T union {r}` in (1).  Their indicator vectors
differ only in coordinate `r`, so the two function values are equal.  Their
signs are opposite:

```text
(-1)^(n-|T|) + (-1)^(n-|T|-1) = 0.
```

Hence `Delta_[n] h=0`.  This argument does not inspect a coefficient field,
a bias, or an activation formula.

The scalar term `phi_j` in (2) is independent of every coordinate outside
`D_j`: no first-layer neuron connected to `j` reads such a coordinate.  Thus
`D_j proper-subset [n]` implies `Delta_[n] phi_j=0`.  The constant `c` also
has zero charge.  Applying the linear functional (1) to (2) proves the left
identity in (5).

On the Boolean cube, `MAX_n(1_empty)=0` and `MAX_n(1_S)=1` for every nonempty
`S`.  Since the sum of all Boolean-lattice signs is zero,

```text
Delta_[n] MAX_n
 = -(-1)^n
 = (-1)^(n+1),
```

which is nonzero.  Therefore at least one output-active term has nonzero
charge; it cannot omit a coordinate, proving (4).  QED.

## Sparse-architecture corollary

Suppose each first-layer row uses at most `s` input coordinates and each
second neuron has at most `k` nonzero incoming first-layer weights.  Then
`|D_j| <= sk`, so

```text
MAX_n exact  ==>  sk >= n.                                    (6)
```

The sharper nonuniform form is that some output-active second neuron satisfies

```text
sum_{i : b_ji != 0} |support(w_i)| >= n,                       (7)
```

with overlaps making (7) only necessary, not sufficient.  Thus, for example,
arbitrary biased/asymmetric two-hidden networks whose first neurons are
two-coordinate-local and whose second-neuron fan-in is at most five cannot
represent `MAX11`, regardless of width elsewhere or coefficient field.

## Exact strengthening for a separated low-rank core

There is a stronger rank obstruction for one tractable arbitrary-weight
family.  It is useful precisely because its extra wiring hypothesis is
falsifiable.

For `epsilon > 0`, define the full coordinate difference

```text
D_epsilon f(x)
  = sum_{S subseteq [n]} (-1)^(n-|S|)
      f(x + epsilon 1_S).                                    (8)
```

Let `A` be any real `q by n` matrix and suppose, with no regularity assumption
on any summand, that

```text
MAX_n(x) = G(Ax) + sum_l H_l(x),                              (9)
```

where every `H_l` is independent of at least one input coordinate (the omitted
coordinate may depend on `l`).  Then

```text
ker(A) subseteq span{(1,...,1)},
rank(A) >= n-1.                                               (10)
```

To prove this, `(8)` annihilates every `H_l`.  If `v in ker(A)`, then for every
subset `S`,

```text
G(A(v + epsilon 1_S)) = G(A(epsilon 1_S)),
```

so the remaining term gives
`D_epsilon MAX_n(v)=D_epsilon MAX_n(0)`.  If `v` is nonconstant, let
`M=max_i v_i` and `T={i:v_i=M}`.  The top set `T` is nonempty and proper.  Set

```text
g = M - max_{i notin T} v_i > 0
```

and choose `0<epsilon<g`.  At zero,

```text
D_epsilon MAX_n(0)=(-1)^(n+1) epsilon != 0.                  (11)
```

At `v`, every coordinate outside `T` remains below every coordinate in `T`
throughout the epsilon cube.  In fact, at vertex `S` the maximum is
`M+epsilon` when `S` meets `T` and `M` otherwise.  It is therefore independent
of every coordinate outside `T`, so its full difference is zero.  This
contradicts translation invariance through `ker(A)`.  Hence every kernel vector
is constant, and rank-nullity proves `(10)`.

The direct network corollary is as follows.  Choose a set `C` of first-layer
neurons and let `A` contain their input-weight rows.  Assume every output-active
second-layer neuron either

1. has all active parents in `C`, or
2. has a proper coordinate ancestor union `D_j` from `(3)`.

For the first class, if `y=Ax`, define `G(y)` by evaluating those second-layer
terms with first activations `ReLU(gamma_i+y_i)`.  This absorbs every arbitrary
first- and second-layer bias and makes `A(x+v)=Ax` the exact equality used
above, not a homogeneity assumption.  Every term in the second class omits a
coordinate.  Exact `MAX_n` therefore forces `rank(A)>=n-1` and `|C|>=n-1`.  In
particular, under this separated-core wiring, `MAX11` needs at least ten
independent core directions: one through nine dense core ridges are impossible
regardless of the widths, biases, real coefficients, or asymmetry elsewhere.

The argument is elementary.  No close statement was found in the bounded
local primary-corpus and arXiv searches, but novelty remains unknown and no
novelty or priority is claimed.

The rank bound is sharp for the functional decomposition.  For `n=2`, the
exact network identity

```text
MAX2(x)=x2+ReLU(x1-x2)                                       (12)
```

uses a rank-one core.  For `n=3`, the formula in the next section factors
through the rank-two map `(x1-x3,x2-x3)` plus the coordinate-local carrier
`x3`.

### Why the wiring hypothesis cannot be deleted

One dense first ridge may be mixed by an outer ReLU with a local first neuron.
For every `n>=2`, the valid second-neuron term

```text
Phi_n(x) = ReLU(ReLU(sum_i x_i - (n-2)) - 2 ReLU(x1))         (13)
```

has full coordinate support and Boolean charge `-1`.  On the Boolean cube it
equals one only at `S=[n]-{1}`.  It is not a function of `sum_i x_i`: the two
size-`n-1` subsets that respectively omit coordinate 1 and coordinate 2 give
values one and zero.  Thus `(13)` is neither a local remainder nor a function
of the one-dimensional dense core.  Multiplying it by output weight `-1`
already gives the `+1` charge required by `MAX11`.

Formula `(13)` uses the first-layer bias `-(n-2)`.  It is therefore an exact
counterexample to a dense-row count law for the **biased parameterisation**, but
by itself it says nothing after G-0020's lossless recession reduction of the
homogeneous MAX target to a bias-free network.  The rank obstruction applies
whenever every globally supported second term factors through the declared
core; `(13)` is only the explicit biased escape from that wiring hypothesis.

### Complete bias-free Boolean-cube no-go

The bias-free gap has a simpler exact solution that does not require
dense--local mixing.  For every nonempty subset `T subseteq [n]`, define the
full-support integer weight

```text
(w_T)_i = 1  if i in T,
          -n if i notin T,
g_T(x) = ReLU(w_T . x).                                      (14)
```

For every nonempty `U subseteq [n]`, direct evaluation gives

```text
g_T(1_U) = |U|  if U subseteq T,
           0    otherwise.                                   (15)
```

Indeed, if `U` is not contained in `T`, at least one selected coordinate has
weight `-n`, while the other at most `n-1` selected coordinates contribute at
most one each; hence `w_T.1_U <= -1`.  If `U subseteq T`, the dot product is
exactly `|U|`.

Index rows and columns by nonempty subsets in nondecreasing cardinality.  The
evaluation matrix is

```text
M[U,T] = |U| 1{U subseteq T}
       = diag(|U|) Z[U,T],
det(M) = product_{empty != U subseteq [n]} |U| != 0,          (16)
```

where `Z` is the upper-triangular subset-zeta matrix with unit diagonal.  Thus
the restrictions of the `g_T` form a basis for all cube label vectors that
vanish at the origin.  Explicitly, for any `F:{0,1}^n -> R` with `F(0)=0`, set

```text
q(U) = F(1_U)/|U|,
c_T  = sum_{V superset T} (-1)^(|V|-|T|) q(V),
N_F(x) = sum_{empty != T subseteq [n]} c_T ReLU(g_T(x)).      (17)
```

Superset Möbius inversion yields `N_F(1_U)=F(1_U)`.  Equation `(17)` is an
exact no-skip two-hidden-layer ReLU network: the first layer computes `g_T`,
the second layer is the bias-free identity pass-through
`ReLU(g_T)=g_T`, and the output weights are `c_T`.  Every bias and the output
constant are zero, every first row has full support, and the whole network is
positively homogeneous.  Widths are `2^n-1` in both hidden layers and every
second neuron has fan-in one.

For the Boolean restriction of `MAX_n`, `F(0)=0` and `F(1_U)=1`.  The
coefficients simplify to

```text
c_T = 1 / (|T| binom(n,|T|)) > 0.                            (18)
```

For `t=|T|`, this follows from
`sum_j (-1)^j binom(n-t,j)/(t+j)=(t-1)!(n-t)!/n!`, equivalently the
elementary beta integral of `x^(t-1)(1-x)^(n-t)`.

This matches every Boolean value of `MAX_n` using a completely bias-free
network, but it is not a global representation away from the cube.

Consequently, even after the G-0020 recession reduction, no nontrivial
obstruction that is a function only of the output values on the standard cube
`{0,1}^n` can exclude unrestricted-width bias-free networks: those restrictions
are exactly all vectors with value zero at the origin.  This includes every
Boolean Möbius coefficient, sign pattern, and rank computed solely from that
value vector.  It does **not** rule out invariants that also inspect width,
weights, walls, multiple translated cubes, or a bounded number of dense rows.
The falsifier is one nonempty pair `(U,T)` violating `(15)`, a zero determinant
in `(16)`, or a label vector with `F(0)=0` not reconstructed by `(17)`.

The route decision is therefore to stop strengthening a standard-cube output
invariant for unrestricted networks.  A viable next obstruction must couple
multiple basepoints through shared parameters, control global walls, or impose
a width/wiring restriction.  The translated-difference theorem above does the
first under separated-core wiring.  The construction is elementary; novelty
is unknown and no novelty or priority is claimed.

## Exact calibrations and the smallest counterexample

The checker replays four discriminators.

1. The exact global identity

   ```text
   MAX3(x) = x3 + ReLU(x2-x3)
                   + ReLU(ReLU(x1-x3)-ReLU(x2-x3))            (19)
   ```

   holds on all `5^3` integer points in `{-2,-1,0,1,2}^3`.  Its
   three Boolean charges are `0,0,1`: the nested second neuron is the required
   full-ancestor term.
2. The biased valid second-neuron term

   ```text
   psi_11(x)=ReLU(sum_i x_i - 10)                             (20)
   ```

   has charge `1` on the Boolean cube.  It compiles in (2) by writing each
   `x_i=ReLU(x_i)-ReLU(-x_i)`.  Dropping `x11` and changing the threshold to
   `9` makes the term independent of `x11`; all `1024` subset pairs cancel and
   its charge is exactly zero.  This explicitly exercises nonzero biases.
3. Full ancestry is not sufficient: `ReLU(sum_i x_i)` reads all eleven
   coordinates but has charge zero.  This is the smallest conceptual
   counterexample to the converse and the main limit of (4).
4. For every pinned exact MAX5--MAX10 pair certificate, the script computes
   each labelled seed atom's charge over its full Boolean cube.  Every
   proper-support seed has zero charge, every nonzero-charge seed has full
   support, and after multiplying by `n!` for unnormalised symmetrisation the
   coefficient-weighted charges equal `(-1)^(n+1)`.  This is only a necessary
   calibration of those certificates, not another global verification.

Replay of the ancestor-support controls:

```bash
python -B artifacts/math/G-0060/boolean_mobius_ancestry.py
```

The run uses at most `2^11=2048` cube vertices per scalar test and exact
integer/rational arithmetic.  `report_v1.json` can be replayed byte-for-object
with:

```bash
python -B artifacts/math/G-0060/boolean_mobius_ancestry.py \
  --check-report artifacts/math/G-0060/report_v1.json
```

Replay of the separated-core rank controls and its dense--local escape:

```bash
python -B artifacts/math/G-0060/core_bottleneck.py \
  --check-report artifacts/math/G-0060/core_bottleneck_v1.json
```

Replay of the bias-free Boolean-cube universality no-go:

```bash
python -B artifacts/math/G-0060/mixed_cube_universality.py \
  --check-report artifacts/math/G-0060/mixed_cube_universality_v1.json
```

## Relationship to the existing wall and pair-orbit results

- G-0047 proves a stronger-looking polynomial-profile statement for
  **symmetrisations of local kernels** and applies it to proper signed cores in
  the pair-orbit family.  The theorem here removes the pair, symmetry,
  homogeneity, and rationality assumptions by applying the Boolean functional
  directly to the additive second-neuron decomposition.  Its price is that it
  sees only coordinate locality.
- G-0022 Theorem 6 and Hertrich et al. (arXiv:2105.14835, Section 6) concern
  cancellation of intermediate non-braid walls.  Equation (1) does not count
  or delete walls, so the same-hyperplane cancellation normal form for a
  one-hidden-layer network in arXiv:2601.01417, Lemma A.1 is not being lifted
  to depth three here.
- The G-0043 arbitrary-wall zero circuit remains a full counterexample to any
  naive deletion theorem.  Charge is linear, so a zero circuit has total
  charge zero, but its constituent terms need not vanish separately.  This
  theorem does not compress such circuits.
- Grillo--Hertrich--Loho (arXiv:2502.09324, Proposition 2.3) uses Boolean
  Möbius inversion for braid-fan-compatible functions.  No ancestor-support
  corollary was found in the local primary corpus, but the observation is
  elementary and likely standard; **no novelty or priority is claimed**.

## Falsifier, route decision, and no-claim boundary

The theorem is falsified by one shaped network matching `MAX_n` on the full
Boolean cube while every output-active second term omits some coordinate.
The proof identifies the exact failure that would then have to occur: one
paired subset value would differ despite the term being coordinate-independent.

As a research route, the invariant deserves a small implementation role: use
the `2048`-point exact charge as a fail-fast filter and require at least one
charged full-support atom in any new asymmetric/sparse MAX11 ansatz.  It does
**not** justify another broad rank census by itself.  One dense first neuron
makes `sk>=11` vacuous, and a full-support term can have charge zero.  The rank
strengthening above recommends one bounded exact target: rule out separated
cores of rank at most nine.  Formula `(13)` says not to extrapolate that result
to arbitrary dense--local mixing in the biased parameterisation.  The
bias-free subset-zeta basis separately rules out value-only single-cube
obstructions at unrestricted width, but does not settle bounded dense-row
counts.

Nothing here constructs MAX11, excludes dense unrestricted networks, bounds
total width, proves pair-atom completeness, rationalises real weights, or
advances the open H-conforming sufficiency/compression step.  The result is a
necessary interaction-support condition and a cheap exact candidate screen.
