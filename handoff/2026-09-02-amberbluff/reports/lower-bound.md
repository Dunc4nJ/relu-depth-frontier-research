# Lower-Bound Machinery for Two-Hidden-Layer `MAX_n` over the Reals

Extraction from seven local paper texts, read in full. Section and theorem locators given throughout. Files are in `/data/projects/relu-depth-frontier-research/literature/papers/`.

Papers read:

| File | Reference |
|---|---|
| `2502.09324.txt` | Grillo, Hertrich, Loho, "Depth-Bounds for Neural Networks via the Braid Arrangement", NeurIPS 2025 |
| `2510.14068.txt` | Grillo, Hofmann, "On the Expressivity of Sparse Maxout Networks" |
| `2601.01417.txt` | Safran, "A Depth Hierarchy for Computing the Maximum in ReLU Networks via Extremal Graph Theory", COLT 2026 |
| `2302.12553.txt` | Haase, Hertrich, Loho, "Lower Bounds on the Depth of Integral ReLU Neural Networks via Lattice Polytopes", ICLR 2023 |
| `2502.06283.txt` | Averkov, Hojny, Merkert, "On the Expressiveness of Rational ReLU Neural Networks with Bounded Depth", ICLR 2025 |
| `2105.14835.txt` | Hertrich, Basu, Di Summa, Skutella, "Towards Lower Bounds on the Depth of ReLU Neural Networks" |
| `2305.16933.txt` | Koutschan, Moser, Ponomarchuk, Schicho |
| `2607.21651.txt` | Rueß et al., "Shallower ReLU Network Representations via Exact Linear Algebra" (read for context on the `n <= 10` upper bound) |

---

# A. Per-paper lower-bound machinery

## A1. Haase, Hertrich, Loho (2302.12553, ICLR 2023) — integral weights

**(i) Theorem statement.** Theorem 3, §1.1: for `n = 2^k`, the function `max{0, x_1, …, x_n}` is not in `ReLU^Z_n(k)`, where `ReLU^Z_n(k)` is the set of functions on `R^n` representable by a ReLU network with `k` hidden layers, arbitrary width, and **all weights integral**. Biases may be assumed zero by Lemma 7, restated from Hertrich et al. Corollary 4 upgrades this to a strict hierarchy `ReLU^Z_n(k−1) ⊊ ReLU^Z_n(k)` for `k ≤ ⌈log_2(n+1)⌉`.

**(ii) Mechanism.** Three layers of machinery.

1. §2.4, Theorem 8: `f` positively homogeneous is in `ReLU^Z_n(k)` iff `f = g − h` with `g, h` convex positively homogeneous and Newton polytopes `P_g, P_h ∈ P_k`, where `P_0` = lattice points and `P_{k+1}` = Minkowski sums of `conv(Q_1 ∪ Q_2)` for `Q_1, Q_2 ∈ P_k`.
2. §3, Propositions 9 and 10: any Minkowski sum `P + Q` admits a subdivision whose full-dimensional cells are **affine products** of a face of `P` and a face of `Q`; any `conv(P ∪ Q)` admits a subdivision whose cells are **joins** of faces. Crucially, these two propositions hold for arbitrary real polytopes, not only lattice polytopes.
3. §4, Theorem 16: define `Q_k` as the lattice polytopes all of whose faces of dimension at least `2^k` have even normalized volume. Then `P_k ⊆ Q_k`. Proposition 17: for `n = 2^k` and `P ∈ Q_k`, `P + Δ^n_0 ∉ Q_k`, because the subdivision of `P + Δ^n_0` has exactly one odd cell, a translate of the simplex itself.

The parity engine is Lucas' theorem: `C(i+j, i)` is even whenever `i + j ≥ 2^k` and `i, j < 2^k`.

**(iii) Where it fails for real weights.** Two independent places, both stated by the authors in §1.3.

- The invariant `Vol` mod 2 needs the vertices to be **lattice points**. Without integrality there is no integer-valued normalized volume, so "even" is meaningless.
- Even accepting integrality, the argument is not scale-invariant. The authors say it explicitly: the proof excludes an integral `k`-layer network computing `max{0, x_1, …, x_{2^k}}` but does not exclude one computing `2 · max{0, x_1, …, x_{2^k}}`, after which dividing the output weights by two yields a half-integral network for the target.

The subdivision machinery in §3 survives for real polytopes. Only the invariant dies.

**(iv) Value at `n = 11`, two hidden layers, real weights.** None directly. Indirectly it gives the scaffolding that Averkov et al. exploit, discussed in D.

## A2. Averkov, Hojny, Merkert (2502.06283, ICLR 2025) — `N`-ary fractions

**(i) Theorem statement.** Theorem 2: let `n, N` be positive integers and let `p` be a prime **not dividing** `N`. Every ReLU network whose weights are all `N`-ary fractions, meaning of the form `z / N^t` with `z ∈ Z`, `t ∈ Z_{≥0}`, needs at least `⌈log_p(n+1)⌉` hidden layers to represent `F_n = max{0, x_1, …, x_n}` exactly. Width is unrestricted. Theorem 4 gives the asymptotic form `C · ln n / ln ln N`, using the prime number theorem to bound the smallest prime not dividing `N`.

**(ii) Mechanism.** Replaces "even" with "divisible by `p`", and replaces Lucas by the fact that `C(d, i) ≡ 0 mod p` for `0 < i < d` when `d = p^t`. Proposition 11, §3.1: if `d = p^t`, then `Vol_d` is Minkowski-additive modulo `p` on lattice polytopes in a common `d`-dimensional lattice subspace. The proof is one line of mixed-volume expansion, equation (1). Proposition 13 handles `conv(A ∪ B)`. Theorem 14: for `P ∈ SU^k(P_0(Z^n))` and `k ≤ t`, every `p^k`-dimensional face of `P` has volume divisible by `p`. Theorem 15: if `h_P ∈ ReLU^Z_n(k)` and `d = p^t ≤ n` with `k ≤ t`, then `p | Vol_d(P)`.

Two auxiliary pieces matter for the campaign. Lemma 10: `SU^k(P_0(Z^n))` is **closed under taking faces**. Lemma 16: a `k`-hidden-layer network with rational weights of common denominator `M` yields `M^{k+1} f ∈ ReLU^Z_n(k)`. The final proof clears denominators and observes `Vol_n(N^{t(k+1)} Δ_n) = N^{n t(k+1)}`, which is not divisible by `p` when `p ∤ N`.

**(iii) Where it fails for real weights.** The clearing step, Lemma 16, is the whole obstruction. It needs a **common denominator** to exist. For a single irrational weight there is no `M`, no lattice polytope, and no integral normalized volume. Note also that the argument is intrinsically "mod `p`" and cannot be strengthened to `p`-adic valuation: I checked that `C(9, 3) ≡ 3 mod 9`, so Proposition 11 does not lift to modulus `p^2`. That closes off the natural quantitative refinement.

**(iv) Value at `n = 11`.** Substantial, as a constraint on any rational certificate. See D.

## A3. Grillo, Hertrich, Loho (2502.09324, NeurIPS 2025) — braid arrangement

**(i) Theorem statements.** Two results, both **conditional on breakpoint location, not on weights**.

- Theorem 4.8 and Corollary 4.9, §4: `M²_{B_d}(ℓ) ⊆ V_{B_d}(2^{2^ℓ − 1})`. Consequently `max{0, x_1, …, x_d}` with `d = 2^{2^ℓ − 1}` is not computable by a `B^0_d`-conforming ReLU network with `ℓ` hidden layers. This is `Ω(log log d)` depth, the first non-constant conditional bound that does not restrict weights.
- Theorem 5.2, §5: `M²_{B_d}(2) = V_{B_d}(4)` exactly. So a braid-conforming two-hidden-layer network computes precisely the span of `σ_M(x) = max_{i ∈ M} x_i` over `|M| ≤ 4`, and nothing more.

`B^0_d`-conforming means every neuron's output function has breakpoints only on the hyperplanes `x_i = x_j` or `x_i = 0`.

**(ii) Mechanism.** Proposition 2.2: `V_{B_d}`, the CPWL functions compatible with the braid fan, is isomorphic to set functions on `2^[d]` via `F(S) = f(1_S)`. Proposition 2.3 identifies `Φ(V_{B_d}(k)) = F_d(k)`, the annihilator of the Möbius vectors `α_{S,T}` of Boolean sublattices of rank `k+1`. Lemma 3.3 says a maxout layer preserves braid compatibility exactly on "conforming tuples". The core induction is Proposition 4.6 and Proposition 4.7: `A(F_L(k)) ⊆ F_L(k² + k)`, where `A(U) = span{F⁺ : F ∈ U ∩ C_L}`. Lemma 4.5 pushes positive and negative support elements down to low lattice levels, which is what makes the induction close. The recursion `n_ℓ ≤ n_{ℓ−1}² + n_{ℓ−1}` starting from `n_1 = 2` is what produces the doubly-exponential growth, hence `Ω(log log d)` depth.

**(iii) Where it fails for real weights.** It does not fail because of weights. It fails because of **breakpoint conformality**. The `σ_M` basis and the whole set-function isomorphism exist only for functions compatible with the braid fan. The authors say so in §7: since Bakaev et al. compute `max` of five numbers with two hidden layers, "considering `B^0_d`-conforming networks is a real restriction", and they note the doubly-logarithmic bound "may not extend to all networks". Their suggested fix is to change the underlying fan.

**(iv) Value at `n = 11`.** A clean conditional statement. `max_{11} = σ_{[11]}` is a basis element of `V_{B_11}`, and `|[11]| = 11 > 4`, so by Theorem 5.2 no braid-conforming two-hidden-layer network computes `MAX_11`. This is a genuine, unconditional-in-weights, conditional-in-breakpoints lower bound at exactly the campaign's target.

There is a sharp and important corollary for the campaign. The Rueß et al. certificates for `n ≤ 10` have a first layer consisting only of pairwise comparisons, which is braid-conforming at layer one. Since `MAX_5` through `MAX_10` are two-hidden-layer computable but are excluded by Theorem 5.2, **those networks must create off-braid breakpoints in the second hidden layer that cancel in the output**. The class "first layer braid-conforming" is therefore strictly larger than "network braid-conforming", and the entire `n ≤ 10` result lives in that gap.

## A4. Safran (2601.01417, COLT 2026) — extremal graph theory

Dissected in full in section B below. Summary of the three points here.

**(ii) Mechanism.** Homogenization on a compact domain, a Turán clique in a graph induced by first-layer supports, a graded assignment of exponentially negative values that freezes all first-layer activations, then layer collapse and induction.

**(iii) Where it fails for real weights.** It does not fail. This is the only paper in the set whose bound is unconditional in the weight field. The price is that it bounds **width**, not depth. The argument can never yield a depth lower bound because the base case, incomputability of `Max_3` by one hidden layer, is the only depth fact used, and the induction only trades width for arity.

**(iv) Value at `n = 11`.** Direct and nontrivial. See B.

## A5. Koutschan, Moser, Ponomarchuk, Schicho (2305.16933) — simplex is not a zero summand

**(i) Statement.** §5. A polytope `P ∈ P_n` is a **zero-summand** if there are zero-volume polytopes `P_1, …, P_r, Q_1, …, Q_s` with `P + P_1 + … + P_r = Q_1 + … + Q_s`. Corollary 5.2: an `n`-simplex in `P_n` is not a zero summand. Theorem 5.4: `max(0, x_1, …, x_n)` is not a linear combination of maxima of fewer than `n+1` affine functions, that is, `MAX_n(n) ⊊ CPWL_n`. This settles a conjecture of Wang and Sun open since 2005.

**(ii) Mechanism.** Lemma 5.1 is a face-descent argument. If `P` is a zero summand and `F_{−d}(P)` has zero volume, then `F_d(P)` is a zero summand. Applying `S_d` and `S_{−d}` to both sides of the defining equation and cancelling by Minkowski cancellability, Proposition 4.2, kills all the zero-volume clutter. Induction on `n` then uses the fact that a simplex has a direction where one face is a point and the opposite face is a simplex of one lower dimension. The bridge to functions is Lemma 5.3, via the standard support-function correspondence `τ` of §4.

**(iii) Where it fails.** It does not fail for real weights, and it is not a depth bound. It is a **dimension** obstruction on signed Minkowski combinations. It says nothing about how the polytopes were built, only about their dimensions.

**(iv) Value at `n = 11`.** It is exactly the tool Rueß et al. use, their Proposition 4.2 and Corollary 4.3, to fix the minimal ansatz parameter `k ≥ ⌊(n−1)/2⌋`. For `n = 11` this forces `k ≥ 5`, which is why their search stops at `n = 10`. The barrier at eleven is computational within that ansatz, not a proven obstruction.

## A6. Grillo, Hofmann (2510.14068) — sparse maxout, virtual polytopes

**(i) Statements.** Theorem 18: for `ℓ ≥ 2`, indegree vector `d ≥ 2`, rank vector `r`, and `n ≥ m_ℓ + 1` where `m_ℓ = Σ_k (r_k − 1) Π_{i>k} d_i`, there holds `N_n(ℓ, d, r) ⊊ N_n(ℓ, r)`. Theorem 19: `N_n(ℓ, 2, 2) = M_n(2^ℓ)`, a complete characterization for indegree two and rank two. Corollary 20 gives the resulting strict hierarchy up to `⌈log_2(n+1)⌉`.

**(ii) Mechanism.** Theorem 7 gives a bijection between functions computable by an indegree-constrained rank-`r` maxout network and a recursively defined class of **virtual polytopes** `V̌_n(ℓ, d, r)`, formal Minkowski differences forming the Grothendieck group of the polytope semigroup. Theorem 11 bounds `dim(V) ≤ Σ_k (r_k − 1) Π_{i>k} d_i` for `V ∈ V̌(ℓ, d, r)`, and Theorem 12 shows the bound is attained. Theorem 16 converts a dimension bound into `N_n(ℓ, d, r) ⊆ M_n(m_ℓ + 1)` via triangulation, using Lemma 15 from Bakaev et al. Lemma 17, imported from Hertrich et al., certifies membership outside `M_n(n)` by exhibiting a hyperplane whose union of codimension-one cells is nonempty and line-free.

**(iii) Where it fails for real weights.** It does not use weights at all. It fails at **`d_1 = n`**. The paper explicitly leaves the first layer fully connected, so `m_ℓ` contains the factor `Π_{i > k} d_i` with `d_1` absent from the products that matter. For a fully connected network the dimension bound is vacuous: `dim(V)` can be as large as `n`. The dimension invariant only bites under a genuine indegree constraint. The authors note in the Discussion that the same content can be phrased as the codimension of the lineality space, following Koutschan et al.

**(iv) Value at `n = 11`, fully connected.** None as stated. It does supply the cleanest available statement of the `k = 2` polytope class, used in C.

---

# B. Safran's result dissected, and the normal-form seed

**Depth convention.** Safran's "depth `k`" means `k − 1` hidden layers, per §1.2, "the depth of a network is defined as the number of hidden layers plus one". His depth-3 is **two hidden layers**, which is the campaign's regime.

**The width bound.** Theorem 2.1: if a depth-3 network computes `Max_d` on `[0,1]^d`, then its width is at least

```
(1/8 − 1/(4d) − 1/(2d²)) · d²
```

At `d = 11` this evaluates to `11.875`, so **width at least 12**. Theorem 1.1 extends this to `0.1 · d^(1 + 1/(2^(k−2) − 1))` for `3 ≤ k ≤ log_2 log_2 d`, which is vacuous at `d = 11` since equation (4) of §A.3 requires `d ≥ 256`.

Values of Theorem 2.1 at small `d`:

| `d` | Safran Theorem 2.1 bound | rounded up |
|---|---|---|
| 5 | 1.375 | 2 |
| 8 | 5.5 | 6 |
| 10 | 9.5 | 10 |
| **11** | **11.875** | **12** |
| 12 | 14.5 | 15 |

**The four steps.**

1. Proposition A.4, from Lemma A.3. Any network computing `Max_d` on `[0,1]^d` can be converted into one of the **same depth, at most twice the width**, that computes `Max_d` on all of `R^d`, is homogeneous with all biases zero, and has every first-layer weight vector supported on at least two coordinates. The construction shifts by a random `c ∈ U([0.4, 0.6])`, deletes negative-bias neurons, and replaces each positive-bias neuron `(w, b)` by the pair `(w, 0)` and `(−w, 0)` with a bias correction pushed one layer forward. This differs from the Hertrich et al. Proposition 2.3 homogenization in two ways Safran stresses: the target is only assumed homogeneous on a compact set, and a quantitative width bound plus the two-nonzero-coordinates property are needed.
2. §2.3. Build a graph `G_N` on `[d]`: each first-layer neuron deletes the edge given by the two smallest indices in its support. Turán, Theorem 1.2, guarantees a clique `I` when the width is small. Corollary A.5 is the quantitative form used.
3. §2.4. Set `x_i = −r (2W)^(i−r)` for `i ∉ I`, where `W` is the ratio of largest to smallest nonzero first-layer weight magnitude. Equation (7) shows the largest-index term dominates, so **every first-layer neuron has constant activation sign on `[0,1]^I`**.
4. §2.5. Collapse the now-affine first layer into the second, obtaining a depth-`(k−1)` network computing `Max_{|I|}` on `[0,1]^{|I|}`. Contradiction with Proposition A.2, no one-hidden-layer network computes `Max_3`. Proposition A.2 rests on Lemma A.1, which repairs a gap in Mukherjee and Basu's characterization of the non-differentiable set of a one-hidden-layer network.

**Yes, this is a necessary structural condition on the first layer.** Step 3 needs only one thing: every first-layer neuron has a nonzero weight **outside** `I`. That is `supp(w) ⊄ I`. Taking the contrapositive of the whole argument gives the following, which I state as a restatement of Safran rather than as something he writes.

> **Restated necessary condition.** Let `N` compute `Max_d` on `[0,1]^d` with two hidden layers, and let `Ñ` be its homogenization from Proposition A.4. Then for **every** subset `I ⊆ [d]` with `|I| ≥ 3` there is a first-layer neuron of `Ñ` with `supp(w) ⊆ I`. Since supports have size at least two and only supports of size two or three can sit inside a triple, the binding case is `|I| = 3`:
>
> **For every 3-subset `T ⊆ [d]`, some first-layer neuron has support of size 2 or 3 contained in `T`.**

Equivalently, writing `S_2` for the pair-supports and `S_3` for the triple-supports, every triangle of the complement graph `K_d \ S_2` must appear in `S_3`.

The general form, for `k` hidden layers, is a reduction rather than a contradiction:

> If a `k`-hidden-layer network computes `Max_d` and there is a set `I` with `|I| = r` such that no first-layer neuron of the homogenized network has support inside `I`, then there is a `(k−1)`-hidden-layer network of no greater width computing `Max_r` on `[0,1]^r`.

**A quantitative strengthening.** Minimizing `|S_2| + |S_3|` over all admissible families equals

```
min over graphs H on [d] of  ( C(d,2) − e(H) + #triangles(H) )  =  C(d,2) − ⌊d²/4⌋
```

I verified this by exhaustive search over all graphs for `d ≤ 6` and by randomized local search at `d = 11`, where the optimum is 25, attained by `H = K_{5,6}`. It follows in general from Erdős supersaturation: each edge beyond the Turán bound creates at least `⌊d/2⌋` triangles, so pushing past the Turán graph is always a net loss for `d ≥ 5`.

| `d` | Safran Theorem 2.1 | Minimum 3-covering family |
|---|---|---|
| 5 | 2 | 4 |
| 8 | 6 | 16 |
| 10 | 10 | 20 |
| **11** | **12** | **25** |

Moreover, homogenization is **support-preserving**: negative-bias neurons are deleted and positive-bias neurons are replaced by two neurons with the same support. So the set of distinct supports of `Ñ` is a subset of that of `N`, and the factor-two width loss does not apply to a count of distinct supports. This gives, for `d = 11`:

> **Any two-hidden-layer real-weight ReLU network computing `MAX_11` on `[0,1]^11` has at least 25 neurons in its first hidden layer, with 25 distinct supports of size 2 or 3 forming a 3-cover of all 165 triples.**

Asymptotically this is `d²/4 − O(d)`, twice Safran's stated constant. It does not contradict his remark that `1/8` is "the optimal constant achievable for depth 3 using our current framework", because his framework routes through a lossy one-edge-per-neuron accounting followed by Turán, whereas the covering formulation is exact. I flag this as my derivation, not his claim.

**One small gap I found, with a repair.** Lemma A.3 item 4 argues that after homogenization no first-layer neuron has a single nonzero coordinate, on the grounds that the random shift makes its bias nonzero almost surely. That does not follow: a positive-bias support-one neuron is replaced by two zero-bias neurons of the same support, which still has size one. The repair is immediate and costs nothing: on `[0,1]^I` a neuron with support `{j}, j ∈ I`, computes `max(0, w_j x_j)`, which is linear on `x_j ≥ 0`. Such neurons are therefore automatically frozen in Step 3 and never block the collapse. The covering condition is unaffected, since support-one neurons cannot serve as covering members either.

---

# C. The `P^k` and virtual-polytope framework at `k = 2`

The relevant chain is Hertrich, Basu, Di Summa, Skutella §5, restated identically by Haase et al. §2.4 and by Averkov et al. §2.2.

Proposition 5.1 of 2105.14835: `N` and `F` are inverse isomorphisms between the semirings `(CCPWL_n, max, +)` and `(Newt_n, conv, +)`, with `N(max{f_1, f_2}) = conv(N(f_1) ∪ N(f_2))` and `N(f_1 + f_2) = N(f_1) + N(f_2)`.

Definition of the classes: `Newt_n^(0)` = single points, and

```
Newt_n^(k) = { Σ_{i=1}^p conv(P_i, Q_i)  :  P_i, Q_i ∈ Newt_n^(k−1),  p ∈ N }
```

Theorem 5.2: a positively homogeneous CPWL function is computable by a `k`-hidden-layer ReLU network **if and only if** it is `g − h` with `g, h` convex positively homogeneous and `N(g), N(h) ∈ Newt_n^(k)`. The proof handles negative output weights by the identity `max{0, f_i} = max{g_i, h_i} − h_i`, equations (12) and (13). Conjecture 5.3 and Theorem 5.4 restate the depth conjecture as: there is no pair `P, Q ∈ Newt_n^(k)` with `Δ_n + Q = P`.

Averkov et al. write the same operator as `SU(X) = { Σ conv(A_i ∪ B_i) : A_i, B_i ∈ X }` and state it as Theorem 8, attributed to Hertrich's thesis Theorem 3.35, together with Corollary 9: `h_P ∈ ReLU_n(k)` iff `P + A = B` for some `A, B ∈ SU^k(P_0(R^n))`.

**Confirming the `k = 2` question.** `Newt_n^(1) = SU^1(P_0(R^n))` is exactly the Minkowski sums of segments `conv(P_i, Q_i)` between arbitrary real points, that is, **zonotopes with arbitrary generators and arbitrary translation**, degenerate cases included. Single points are zonotopes, taking `p = 1` and `P_1 = Q_1`, so their support functions, the linear functions, are already inside. Therefore

```
Newt_n^(2) = { Σ_i conv(Z_i ∪ Z'_i)  :  Z_i, Z'_i  zonotopes in R^n }
```

and, since `f_{conv(Z ∪ Z')} = max{h_Z, h_{Z'}}` and `λ · h_{conv(Z ∪ Z')} = h_{conv(λZ ∪ λZ')}` for `λ > 0` with `λZ` again a zonotope,

> **The positively homogeneous part of `ReLU_n(2)` is exactly the set of real signed sums `Σ_i λ_i · h_{conv(Z_i ∪ Z'_i)}` with `Z_i, Z'_i` zonotopes with arbitrary generators and translations.**

Your formulation is **correct**, and the "+ linear" is redundant: linear functions are already there as `h_{{v}}` with `{v}` a degenerate zonotope. The one caveat is that the signed sum must be read as a difference of two nonnegative sums, matching `f = g − h`, which is automatic once negative coefficients are collected on one side. Citations: Theorem 5.2 and Proposition 5.1 of 2105.14835, Theorem 8 and Corollary 9 of 2502.06283.

**Restated target.** `MAX_11 = h_Δ` with `Δ = conv{e_1, …, e_11} ⊂ R^11`, a 10-simplex. Equivalently in `R^10`, `Δ_10 = conv{0, e_1, …, e_10}`. The campaign question is exactly:

```
Do there exist  A, B ∈ SU²(P_0(R^10))  with  Δ_10 + A = B ?
```

Grillo and Hofmann's Theorem 7 gives the same content in the language of virtual polytopes, `V̌_n(ℓ, d, r)`, with `d_1 = n` unconstrained recovering the fully connected case, and Lemma 5 supplies the bijection between `V_n` and `C_n`.

---

# D. Averkov, Hojny, Merkert: the exact bound and its consequence at eleven

**Verified statement.** Theorem 2 is `⌈log_p(n+1)⌉` **hidden layers** for `F_n = max{0, x_1, …, x_n}`, where `p` is any prime not dividing `N`. Your recollection of `⌈log_p n⌉` is correct if `n` denotes the **arity** of the maximum, since `F_n` is the maximum of `n+1` quantities. The strongest instance is `p` = the smallest prime not dividing `N`, which is what Theorem 4's `ln n / ln ln N` bound optimizes. Sanity check against the integral case: for `N = 1` every prime is coprime, so `p = 2` recovers Haase et al. Theorem 3.

Since `MAX_11` and `F_10` are inter-representable at equal depth by the standard shift, Proposition 1.6 of 2105.14835,

```
max{ℓ_1, …, ℓ_{n+1}} = max{0, ℓ_1 − ℓ_{n+1}, …, ℓ_n − ℓ_{n+1}} + ℓ_{n+1}
```

the relevant table is:

| prime `p` | hidden layers forced for `MAX_11` |
|---|---|
| 2 | 4 |
| 3 | 3 |
| 5 | 2 |
| 7 | 2 |
| 11 | 1 |

Two hidden layers therefore require that no prime with `p² < 11` be coprime to `N`. That is `p ∈ {2, 3}`.

> **Consequence.** Any `N`-ary-fraction two-hidden-layer certificate for `MAX_11` must have `6 | N`. The weight ring must contain `1/2` and `1/3`.

The two divisibilities enter at different arities, which is worth recording because it is checkable against the existing `n ≤ 10` certificates.

- `2 | N` is forced already by the `MAX_5` sub-instance: `p = 2`, `k = 2` requires `4 < n+1 ≤ 8`, reducing to `n = 4` and the four-dimensional simplex.
- `3 | N` is forced only from `MAX_10` onward: `p = 3`, `k = 2` requires `9 < n+1 ≤ 27`, reducing to `n = 9` and the nine-dimensional simplex.
- `5 | N` would first be forced at `MAX_26`, so it is not forced at eleven.

Restriction of variables is legitimate here because setting surplus coordinates equal to an existing one turns `MAX_11` into `MAX_m` for any `m ≤ 11` without changing depth, and Averkov's own proof of Theorem 2 uses exactly this move to reduce to `n = p^k`.

There is a cleaner route than Lemma 16 when the first two layers already have integral weights, as in the Rueß construction. If `M` is the common denominator of the output coefficients, then `M · MAX_11 = h_{M Δ}` is integrally two-layer representable, and Theorem 15 with `p = 3`, `d = 9` forces `3 | Vol_9(M Δ_9) = M^9`, hence `3 | M`. The same with `p = 2`, `d = 4` forces `2 | M`.

**No valuation refinement is available.** I checked that `C(9,3) ≡ 3 mod 9` and `C(4,2) ≡ 2 mod 4`, so Proposition 11's additivity of `Vol_d` modulo `p` does not lift to modulus `p²`. The machinery yields divisibility only, never the exponent of `2` or `3` in the denominator.

---

# E. Conjectures, and the situation at eleven

**Stated conjectures.** Hertrich et al. Conjecture 1.4, `ReLU_n(0) ⊊ … ⊊ ReLU_n(⌈log_2(n+1)⌉) = CPWL_n`; Conjecture 1.5, `max{0, x_1, …, x_{2^k}} ∉ ReLU_{2^k}(k)`; Conjecture 5.3, the polytope form, no `P, Q ∈ Newt_n^(k)` with `Δ_n + Q = P`. Proposition 1.6 and Theorem 5.4 prove all three equivalent. Averkov et al. restate the first as their Conjecture 1.

**All three are now false.** Bakaev et al. give a two-hidden-layer `max_5`, refuting Conjecture 1.5 at `k = 2`; this is reported in Grillo, Hertrich, Loho §1 and in Rueß et al. §1.1. Rueß et al. Corollary 1.3 goes much further: every function in `CPWL_d` with `d ≤ 9` is two-hidden-layer representable, so `ReLU_9(2) = CPWL_9` while `⌈log_2 10⌉ = 4`. The conjectured hierarchy collapses badly.

**No paper in this set states a replacement conjecture about the true depth of `MAX_n` over the reals.** Grillo, Hertrich, Loho §1 say only that "it is already open whether there is a function that needs more than two hidden layers to be represented". Rueß et al. state no conjecture and give no barrier at eleven. Safran states none. Averkov et al. §4 say only that removing the `ln ln N` factor would settle the rational case up to a constant. Haase et al. §1.3 say the parity argument "seems not to be sufficient" for arbitrary weights and ask for a different invariant.

**Why the literature stops at ten, and what it does not say.** Rueß et al. §4.2 and Corollary 4.3 fix the ansatz parameter by Koutschan's Corollary 5.2: a solution requires `k ≥ ⌊(n−1)/2⌋`, which is `4` for `n ∈ {9, 10}` and `5` for `n = 11`. The number of isomorphism classes of two-edge-coloured multigraphs with `k` edges per colour explodes. Their stopping point is the size of the linear system, not a proven obstruction. **Nothing in any of these papers gives a reason to believe two layers fail at eleven.** The only genuine reasons to suspect a threshold anywhere are the two conditional bounds: braid conformality dies at arity five, and integrality dies at arity three.

---

# F. Ideas in these papers not yet exploited

Labelled by confidence. Items marked speculative are my proposals, not claims from the papers.

**F1. Use the restated Safran condition as a hard constraint on any certificate search. Not speculative.** The condition derived in B is finite, checkable, and independent of the weight field. Any candidate two-hidden-layer `MAX_11` network must have at least 25 first-layer neurons whose supports of size 2 or 3 form a 3-cover of the 165 triples of `[11]`. The extremal configurations are exactly the complements of triangle-free graphs, with the minimum attained at the complement of `K_{5,6}`. This is a strong prior for CEGIS: it says the first layer cannot consist only of pairwise comparisons drawn from a triangle-free pattern, and it pins the minimum first-layer width. Rueß et al.'s certificates use `C(n+1, 2)` first-layer neurons, comfortably above 25, so the constraint is consistent with what exists and is a lower bound to respect, not a contradiction.

**F2. The missing completeness theorem is precisely "first layer without loss of generality pairwise". Not speculative that it is open; speculative that it is true.** Rueß et al. Theorem 1.1 merely *observes* that their found certificates have a pairwise first layer, and Theorem 5.1 exploits that observation for recursion. Nobody proves it is necessary. If one could show

> `MAX_n ∈ ReLU(2)` implies `MAX_n ∈ ReLU(2)` with all first-layer neurons of the form `ReLU(α(x_i − x_j))`

then the `n = 11` question becomes a finite exact rational linear algebra problem of exactly the Rueß type, since the second-layer preactivations range over a fixed finite-dimensional rational space and the output coefficients enter linearly. Note that this normal form is **strictly weaker than braid conformality**, so Grillo et al. Theorem 5.2 does not refute it, as established at the end of A3. Safran's condition from B is evidence in its favour: it forces at least 25 first-layer neurons with supports of size 2 or 3, which is already most of the way to "pairwise".

**F3. Real solvability equals rational solvability inside any linear ansatz. Not speculative, but underused.** In the Rueß formulation the unknowns are the output coefficients `λ_{A,B}` and the constraint system, equations (2) and (3) of §4.1, has rational data. A real solution therefore implies a rational one. Combining this with D gives a genuinely usable statement: **within any ansatz whose first two layers carry integral weights, a real-weight `MAX_11` certificate exists if and only if a rational one does, and its output denominator must be divisible by 6.** A search restricted to denominators coprime to 6 is provably futile, and a solver can be told so.

**F4. Unify Safran's freezing with Averkov's face-closure. Speculative but concrete.** Safran's Step 4, substituting graded negative values and freezing the first layer, is the same operation as taking a face of the Newton polytope in a distinguished direction. Averkov et al. Lemma 10 proves `SU^k(P_0(Z^n))` is closed under faces, and Theorem 14 propagates the mod-`p` invariant **through faces**. These are the same phenomenon seen from the function side and the polytope side. The unexploited combination: Safran's freezing works over `R`, and face-closure of `SU^k(P_0(R^n))` also works over `R`. If one can find any real-valued invariant that is Minkowski-additive and behaves controllably under `conv(A ∪ B)`, Safran's freezing supplies the descent step that the parity argument gets from Lucas. The template for such an invariant is spelled out in Averkov et al. §4: a group homomorphism `φ` on the abelian group of CPWL functions vanishing on `ReLU(k)` but not on the target.

**F5. Candidate real invariants nobody in this set has tried. Speculative.** Haase et al. §1.3 explicitly ask for a replacement for volume parity and note that their subdivisions, Propositions 9 and 10, are valid for arbitrary real polytopes. Two candidates that are not in any of these papers:

- The **McMullen polytope algebra** `Π(R^n) = ⊕_r Ξ_r`, the graded ring in which Minkowski sum is multiplication and the top graded piece is volume. Zonotopes have a very rigid class, a product of segment classes, and the class of `conv(A ∪ B)` has a controllable expansion via the join subdivision of Proposition 10. The grading replaces "dimension at least `2^k`" by an algebraic filtration that does not need a lattice. This is the natural home for the invariant Haase et al. ask for.
- **Mixed volumes as a multilinear form rather than a scalar.** Averkov et al. use mixed volumes only to prove additivity mod `p`, discarding the multilinear structure. The full mixed-volume vector `(V(P, …, P, Q, …, Q))_i` is a real invariant that is Minkowski-multilinear by Theorem 5(b), and the simplex has an extremal mixed-volume profile.

**F6. Change the fan, as the braid authors themselves suggest. Speculative.** Grillo et al. §7 close with exactly this. The campaign-relevant instance: keep the first layer braid-conforming, which the known certificates satisfy, and analyse the operator `A` applied to `V_{B_n}(2)` **without** requiring the output of the ReLU to remain braid-conforming. The relevant question becomes the dimension of `span{max{0, f} : f ∈ V_{B_n}(2)}` inside the full CPWL space, rather than inside `V_{B_n}`. Their Lemma 4.5 and Proposition 4.6, the machinery for pushing supports down the Boolean lattice, is the only part that genuinely needs conformality; the set-function isomorphism Proposition 2.2 survives for the input side.

**F7. A dead end I checked so you do not have to.** The `p`-adic refinement of Averkov's argument fails. Proposition 11's additivity of `Vol_{p^t}` modulo `p` relies on `C(p^t, i) ≡ 0 mod p` for `0 < i < p^t`, and this does not hold modulo `p²`: `C(9,3) ≡ 3 mod 9` and `C(4,2) ≡ 2 mod 4`. So the machinery gives `6 | N` and cannot be pushed to constrain the exponents of 2 and 3.

**F8. Grillo and Hofmann's dimension bound applied to layer two only. Speculative.** Their Theorem 11 is vacuous when `d_1 = n`, but a two-hidden-layer network in the Rueß normal form has `d_2` equal to the number of first-layer neurons feeding each second-layer neuron. If one could prove that second-layer neurons may be taken to depend on boundedly many first-layer neurons, their `m_ℓ = Σ_k (r_k − 1) Π_{i>k} d_i` bound combined with Theorem 16 and Koutschan's Corollary 5.2 would give an immediate contradiction at `n = 11`. This is the sparsity route to the same completeness theorem as F2, and it is the only route in this literature that converts a **width or fan-in** restriction into a **depth** lower bound.

---

# Summary of what is and is not proved at `n = 11`

| Claim | Status | Source |
|---|---|---|
| `MAX_11` needs more than two hidden layers, real weights | **Open**, no partial result | none |
| `MAX_11` needs more than two hidden layers, integral weights | Proved, needs 4 | Haase et al. Theorem 3 |
| `MAX_11` needs more than two hidden layers, `N`-ary with `6 ∤ N` | Proved | Averkov et al. Theorem 2 |
| `MAX_11` needs more than two hidden layers, braid-conforming | Proved | Grillo et al. Theorem 5.2 |
| Two-hidden-layer `MAX_11` first layer has at least 12 neurons | Proved, real weights | Safran Theorem 2.1 |
| Two-hidden-layer `MAX_11` first layer has at least 25 neurons with 3-covering supports | Derived here from Safran Proposition A.4 and §2.4 | this report, section B |
| Any rational two-hidden-layer `MAX_11` certificate has denominator divisible by 6 | Derived here from Averkov et al. Theorem 2 | this report, section D |
