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

This is an exact counterexample to any unqualified claim that the *number* of
dense first rows alone controls the full Boolean charge.  The rank obstruction
applies only when every globally supported second term factors through the
declared core; dense--local mixing is the explicit escape route.  Consequently
the useful next ansatz is the separated-core family above, not the family of
all networks with a bounded count of dense first rows.

### Complete Boolean-cube no-go for mixed-term obstructions

The escape is not isolated.  Dense--local mixed second neurons span *every*
function on one Boolean cube.  Define one shared dense first neuron and two
coordinate-local first neurons per input:

```text
d(x)       = ReLU(sum_i x_i - n),
l_i,0(x)   = ReLU(x_i),
l_i,1(x)   = ReLU(1-x_i).
```

For every Boolean vertex `v in {0,1}^n`, define the mixed second neuron

```text
H_v(x) = ReLU(1 + 2 d(x)
                 - sum_{i:v_i=0} l_i,0(x)
                 - sum_{i:v_i=1} l_i,1(x)).                  (14)
```

At a Boolean input `u`, the dense activation is zero and the local sum is the
Hamming distance from `u` to `v`.  Therefore

```text
H_v(u) = 1 if u=v, and 0 otherwise.                           (15)
```

These are the standard basis vectors of the `2^n`-dimensional space of cube
functions.  Hence every `F:{0,1}^n -> R` has the exact cube interpolation

```text
N_F(x) = sum_{v in {0,1}^n} F(v) H_v(x),
N_F(u) = F(u) for every Boolean u.                            (16)
```

This is a valid no-skip two-hidden-layer ReLU network with shared first width
`2n+1`, second width at most `2^n`, arbitrary real output weights, and second
fan-in `n+1`.  Every `H_v` has a nonzero dense-parent coefficient and one
nonzero local parent for every coordinate.  The dense parent is not merely a
zero-labelled edge: at `x=2(1,...,1)`, including `2d(x)` changes every `H_v`
relative to deleting that parent.

In particular,

```text
Delta_[n] H_v = (-1)^(n-|v|),                                (17)
```

so mixed neurons realise both charge signs, and arbitrary output scaling gives
arbitrary charge magnitude.  Taking `F(0)=0` and `F(v)=1` otherwise matches the
entire Boolean restriction of `MAX_n` (but not necessarily `MAX_n` off-cube).

Consequently, no nontrivial obstruction depending only on the values on one
Boolean cube--including any collection of Boolean Möbius coefficients, signs,
or ranks computed from those values--can exclude unrestricted dense--local
mixed networks.  The falsifier is a single pair `(u,v)` violating `(15)` or a
cube label vector not reconstructed by `(16)`.  The route decision is to stop
strengthening the single-cube charge invariant for arbitrary mixing.  A viable
next obstruction must couple multiple basepoints through shared parameters,
control global walls, or impose a width/wiring restriction.  The translated
difference rank theorem above does the first under separated-core wiring.

## Exact calibrations and the smallest counterexample

The checker replays four discriminators.

1. The exact global identity

   ```text
   MAX3(x) = x3 + ReLU(x2-x3)
                   + ReLU(ReLU(x1-x3)-ReLU(x2-x3))            (18)
   ```

   holds on all `5^3` integer points in `{-2,-1,0,1,2}^3`.  Its
   three Boolean charges are `0,0,1`: the nested second neuron is the required
   full-ancestor term.
2. The biased valid second-neuron term

   ```text
   psi_11(x)=ReLU(sum_i x_i - 10)                             (19)
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

Replay of the mixed-term Boolean-cube universality no-go:

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
to arbitrary dense--local mixing.

Nothing here constructs MAX11, excludes dense unrestricted networks, bounds
total width, proves pair-atom completeness, rationalises real weights, or
advances the open H-conforming sufficiency/compression step.  The result is a
necessary interaction-support condition and a cheap exact candidate screen.
