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

## Exact calibrations and the smallest counterexample

The checker replays four discriminators.

1. The exact global identity

   ```text
   MAX3(x) = x3 + ReLU(x2-x3)
                   + ReLU(ReLU(x1-x3)-ReLU(x2-x3))             (8)
   ```

   holds on all `5^3` integer points in `{-2,-1,0,1,2}^3`.  Its
   three Boolean charges are `0,0,1`: the nested second neuron is the required
   full-ancestor term.
2. The biased valid second-neuron term

   ```text
   psi_11(x)=ReLU(sum_i x_i - 10)                              (9)
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

Replay:

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
makes `sk>=11` vacuous, and a full-support term can have charge zero, as the
explicit counterexample above shows.  The next useful discriminator would
parameterise a genuinely charged full-support arbitrary-weight atom family and
test complete hinge cancellation; this artifact does not supply that family.

Nothing here constructs MAX11, excludes dense unrestricted networks, bounds
total width, proves pair-atom completeness, rationalises real weights, or
advances the open H-conforming sufficiency/compression step.  The result is a
necessary interaction-support condition and a cheap exact candidate screen.
