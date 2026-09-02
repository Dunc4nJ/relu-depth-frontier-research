# Literature refresh: MAX_n at two hidden layers, as of 2026-09-02

Scout report for the ReLU depth frontier campaign. All searches run 2026-09-02.

## Bottom line

Nothing published between June and September 2026 settles MAX_11, settles MAX_n for
all n, or gives any depth lower bound beyond two hidden layers for unrestricted real
weights. The frontier is unchanged: n <= 10 constructible (Ruess et al.), n >= 11
open, and the best unconditional lower bound on depth for any CPWL function is still
2. I found four papers not in the local corpus that are genuinely relevant, three of
them on the obstruction side.

---

## 1. Search log, all queries run 2026-09-02

| Query | Engine | Hits examined | Outcome |
|---|---|---|---|
| maximum function two hidden layers ReLU network exact representation 2026 | WebSearch | 8 | Only 2607.21651, 2608.25221, 2505.14338. No new work. |
| MAX_11 ReLU two hidden layers open problem arXiv | WebSearch | 6 | No MAX_11 result exists. Confirms 2608.25221 is the most recent. |
| arXiv September 2026 ReLU network depth lower bound maximum function real weights | WebSearch | 9 | Safran 2601.01417 (COLT 2026) is the only unconditional lower bound; it is width-vs-depth, not depth-only. |
| "Ruess"/"Ruess" Hertrich shallower ReLU exact linear algebra max10 follow-up | WebSearch | 6 | No follow-up paper. |
| arXiv 2026 "virtual polytopes" OR "Minkowski summand" ReLU depth lower bound real weights | WebSearch | 7 | Surfaced 2410.04907 (Decomposition Polyhedra), not in corpus. |
| Grillo Hofmann sparse maxout networks expressivity virtual polytopes 2026 | WebSearch | 10 | Surfaced 2509.21286 (Maxout Polytopes), not in corpus. Confirms 2510.14068 accepted to Indagationes Mathematicae 2026. |
| "maxout polytopes" arXiv 2509.21286 depth lower bound | WebSearch | 9 | Balakin, Cox, Loho, Sturmfels. Non-negative weights after layer one. Surfaced 2607.11540. |
| "Hertrich conjecture" ReLU depth disproved log3 lower bound unrestricted weights 2026 | WebSearch | 10 | Nothing new; confirms STOC 2026 publication of 2505.14338. |
| tropical rational functions depth two ReLU "Newton polytope" simplex indecomposable 2026 | WebSearch | 10 | Surfaced 2507.07779 (Approximation Depth of Convex Polytopes), not in corpus. |
| Safran "Every Layer Counts" 2608.23877 abstract | WebSearch | 10 | Confirms local copy; no MAX_n depth-only bound. |
| "generalized permutahedra"/"hinging hyperplanes" ReLU depth two hidden layers lower bound | WebSearch | 9 | Nothing new. |
| "two hidden layers" ReLU max n=11 construction certificate 2026 arXiv new | WebSearch | 8 | Nothing. |
| arXiv 2026 exact representation CPWL R^10 two hidden layers new preprint Aug/Sep | WebSearch | 8 | Nothing. |
| Grigsby Lindsey polyhedral geometry ReLU functional dimension depth lower bound 2026 | WebSearch | 10 | Surfaced 2606.07728 (ICLR 2026); checked, not a depth result. |
| "polyhedral complex"/"difference of zonotopes" ReLU depth two obstruction impossibility 2026 | WebSearch | 8 | Nothing. |
| "MAX_9"/"MAX_10"/"max_11" ReLU two hidden layers September 2026 | WebSearch | 8 | Nothing. |
| arxiv listing new September 2026 ReLU depth polytope Hertrich Loho Averkov Stade Brunck | WebSearch | 30 (3 sub-searches) | Surfaced 2411.03006 (Virtual Extended Formulations). No 2609.* preprint in this area. |
| "neural polytopes" workshop 2026 open problems n=11 | WebSearch | 9 | Workshop site is 404. Nothing. |
| Valerdi minimal depth simplex log2(n+1) ICNN monotone lower bound | WebSearch | 10 | Confirms Valerdi 2402.15315 lower bound is for the unsigned P^k model. |
| arXiv full-text search: ReLU depth maximum function, sorted by date, 50 results | WebFetch (arxiv.org/search) | 50 | Exactly one submission in the June-Sept 2026 window: 2607.21651. |
| arXiv Atom API, `abs:"two hidden layers" AND abs:ReLU`, date-sorted | WebFetch | 0 | HTTP 429. Retried once, 429 again. Not retrieved. |
| arXiv Atom API, `abs:"maximum function" AND abs:ReLU` | WebFetch | 0 | HTTP 429. Not retrieved. |
| Semantic Scholar `/graph/v1/paper/search` (3 distinct queries) | WebFetch | 0 | HTTP 429 on all three attempts. Not retrieved. |
| arXiv API via curl (Bash) | Bash | 0 | Network egress blocked in this environment, sandboxed and unsandboxed. |
| Hertrich homepage preprint list | WebFetch | full page | Two 2026 preprints: 2607.21651 and 2607.11540. No unlisted MAX_11 work. |
| Loho homepage preprint list | WebFetch | full page | Five 2026 items, none on MAX_n depth beyond the braid paper. |
| github.com/kilianar/max-relu-certificates README | WebFetch | full page | Scope explicitly "n <= 10". No n=11, no k=5, no template counts, three commits. |

Two engines failed outright and I want that on the record: the Semantic Scholar graph
API and the arXiv Atom API both returned HTTP 429 for every attempt, and Bash has no
network egress. The arXiv coverage in this report therefore rests on the arXiv
full-text search UI, targeted web search, and author homepages, not on a programmatic
listing sweep. A campaign that wants a certified-complete arXiv sweep should redo the
Atom API pass from a host with working egress.

---

## 2. Ruess, Averkov, Brunck, Grillo, Hertrich, Loho, Stade, Stargalla, Sun, Winter (arXiv:2607.21651v1, 22 July 2026)

**The ansatz, exactly.** Section 4.1. Let E_n be unordered index pairs including
diagonals, so |E_n| = C(n,2) + n. For a pair (i,j) write m_ij(x) = max{x_i, x_j}. Fix
k, let M_{n,k} be multisets of cardinality k drawn from E_n. For each pair (A,B) in
M_{n,k} x M_{n,k} define the block as the max of the two side-sums of pairwise maxima.
Symmetrize over all of S_n without the 1/n! factor to get F_{A,B}. The question asked
is whether max_n lies in the linear span of the F_{A,B}.

**Reduction to linear algebra.** Proposition 3.1 gives the symmetrization argument: a
symmetric identity holds on all of R^n iff it holds on the sorted cone C. On C every
first-layer pairwise max collapses to a coordinate projection onto the larger index,
so the first layer contributes no breakpoints. Rewriting each outer max via
max(u,v) = u + ReLU(v-u) and collecting identical difference vectors yields equations
(2) and (3) on page 7: every hinge coefficient must vanish, and the surviving linear
part must equal x_n.

**Enumeration.** Section 4.1.1. Blocks are invariant under swapping A and B and under
simultaneous relabelling, so the search enumerates equivalence classes called
templates, which is a two-edge-coloured multigraph isomorphism problem with the
colours themselves interchangeable, solved with nauty. Remark 4.1 lists the
reductions: hinge directions with fixed sign on C are dropped, d and -d are
identified, positive scalar multiples are identified.

**Certificate sizes and growth.** This is the one place the paper is thin. They give
no table of system dimensions. The only certificate printed in full is n = 6, k = 2,
which uses four templates with coefficients 1/720, 1/360, -1/1440, -1/360. For n = 7
through 10 the certificates are described as "much larger" and deferred to the GitHub
repository. Width is bounded in the paragraph on page 10: first hidden layer at most
C(n+1,2) = O(n^2) as rank-2 maxout, or C(n,2) + 2n as plain ReLU; second layer at most
Q <= s*n! where s is the number of supporting templates, or 3Q for plain ReLU. They
explicitly decline to optimise this and note it sits far above Safran's quadratic
lower bound.

**The k lower bound, which is the real structural content.** Proposition 4.2 restates
Koutschan et al. Corollary 5.2 in support-function language: a k-simplex is not a
signed Minkowski combination of polytopes of dimension strictly less than k. Corollary
4.3 then derives k >= k_min = floor((n-1)/2). The argument: the sum over A of m_ij is
the support function of the zonotope Z_A of dimension at most k, the block is the
support function of conv(Z_A union Z_B) of dimension at most 2k+1, and max_n is the
support function of an (n-1)-simplex, so 2k+1 >= n-1.

**n = 11 and all-n statements.** There are none. I grepped the full text. The paper
never mentions n = 11, never states a conjecture about all n, and never names an
obstacle at any specific n. The single sentence closest to the campaign's framing is
Section 4.2: "It is therefore natural to ask for the smallest value of k that is not
ruled out by theoretical obstructions." The "k = 5 / 12 million templates" barrier is
the campaign's own arithmetic, not the paper's. For the record it checks out:
k_min(11) = 5, |E_11| = 66, and |M_{11,5}| = C(70,5) = 12,103,014.

**Completeness or normal form.** None. This is important and I want to be blunt about
it. Theorem 1.1 is one-directional. There is no theorem of the form "any
two-hidden-layer representation of max_n can be normalised to this shape." The ansatz
is a sufficient family, and failure of the linear system rules out nothing.

**The recursive depth bound, exact statement.** Theorem 5.1. Assume max_l has a
two-hidden-layer representation B_l whose first hidden layer consists only of pairwise
comparisons, and set r = floor(l/2) >= 2. Then for every integer s >= 0, max_{l*r^s}
has an exact representation with 2 + s hidden layers whose first hidden layer again
consists only of pairwise comparisons. Consequently max_n needs at most
2 + max{0, ceil(log_r(n/l))} hidden layers. The substitution replaces each first-layer
comparison max{y_p, y_q} by a copy of B_l computing the max over S_p union S_q, which
is a max of 2r <= l inputs, with repeated-coordinate padding. Corollary 1.2
instantiates l = 10, r = 5 to give ceil(log_5(n/2)) + 1. Corollary 1.3 pushes it
through Wang-Sun to CPWL_d with (d+1)/2 in place of n/2, hence two hidden layers for
all d <= 9. Remark 4.4 combines with Mukherjee-Basu to conclude that for n in
{3,...,10} the minimum number of hidden layers is exactly two.

---

## 3. Wang and Basu (arXiv:2608.25221v1, 25 August 2026)

Independent, weaker in reach, but with better-documented numerics and one sharper
conceptual point.

**Ansatz.** Definition 1.1, the same atoms, written as ordered-pair patterns with a
left and right list of length k. Lemma 1.2 gives the closed form on the sorted
chamber: the atom equals the max of two inner products with vectors eta_L, eta_R in
the non-negative integer lattice with L1 norm exactly k, where each coordinate counts
how many pairs have their minimum index at that position.

**The one real methodological difference.** Section 1.2, item 2, and Definition 1.4.
They do not extract a linear term and kill all hinges. Instead they call an atom
ambiguous over the sorted chamber if neither side dominates, equivalently if
eta_R - eta_L lies outside the polar cone and its negative, and they impose c_T = 0
only for ambiguous terms while letting all unambiguous terms contribute. Section 1.3
states that Ruess et al. drop unambiguous non-trivial terms, and identifies this as
the likely reason the two families of certificates differ.

**Certificate sizes, Table 1 page 6.** This is the growth data the campaign wants.

| N | k | constraints | variables |
|---|---|---|---|
| 5 | 2 | 20 | 131 |
| 6 | 2 | 41 | 144 |
| 7 | 3 | 1,057 | 4,469 |
| 8 | 4 | 21,953 | 193,623 |

Section 1.3 adds the two systems they could not solve: N = 9, k = 4, with 51,984
constraints and 210,540 variables; N = 10, k = 4, with 112,837 constraints and 216,428
variables. They state plainly that these were computationally inaccessible with exact
rational arithmetic in the compute available to them.

**Support sizes.** MAX_5 uses 7 orbit classes (Theorems 2.1 and 2.3 give two distinct
identities). MAX_6 uses 7 classes (Theorems 3.1 and 3.3). MAX_7 uses 109 of 4,469
orbits with k = 3 (Theorem 4.1). MAX_8 uses 1,290 of 193,623 orbits with k = 4
(Theorem 5.1). All identities are stated as 2*MAX_N = a sum of rational multiples of
orbit sums.

**Note their k for N=8 is worse.** They use k = 4 where Ruess et al. use k = 3. Since
k_min(8) = 3, Ruess et al. hit the theoretical floor and Wang-Basu did not.

**The completeness disclaimer, verbatim, Section 6.** "We emphasize that a solution to
the corresponding linear system is a sufficient certificate for representation using
ReLU networks with two hidden layers; it is not a complete characterization. In other
words, nonexistence of a solution does not imply nonexistence of such a
representation." This is the sharpest statement in either paper of why an exhausted
search at n = 11 would prove nothing.

**n = 11 or all-n.** Nothing. The abstract's framing is the useful quotable: "The best
lower bound is 2, while the current upper bound is logarithmic in N. It remains
completely open if the right answer is a constant number of hidden layers (possibly
even 2!) or not."

---

## 4. Bakaev, Brunck, Hertrich, Stade, Yehudayoff (arXiv:2505.14338v3, 19 Feb 2026; STOC 2026)

**Construction.** Section 2.1, equation (2).
MAX_5 = 0.5*(P_1 + P_2 + P_3 + P_4 + Q - R_13 - R_14 - R_23 - R_24), nine explicit
rank-2-maxout terms. Claim 4's proof is a case analysis exploiting invariance under
1<->2, 3<->4, and (1,2)<->(3,4); when x_1 is largest, P_2 = R_23, P_3 = R_13,
P_4 = R_14, R_24 = Q, and everything collapses to 0.5*P_1 = x_1.

**Recursion.** Section 2.2. T_{a,b} is the max of a terms of shape
max(x_1,x_2)+max(x_3,x_4) plus b loose arguments. Claim 5: T_{a,b+4} lies in the span
T_{a+1,b+1}. Claim 6 iterates it 3^{n-1} times. Claim 7 trades one layer for the
first-layer pairing. Theorem 1: MAX_{3^n+2} is in ReLU_{n+1}. Remark 1 notes all
weights are binary fractions, so the construction sits inside the
Averkov-Hojny-Merkert restricted class and nearly matches their bound.

**The geometric frame the whole field now uses.** Section 3.1. P^0 is points; P^{k+1}
is finite Minkowski sums of convex hulls of pairs from P^k. Lemma 8, attributed to
Hertrich's thesis Theorem 3.35: the number of hidden layers needed for h_X is the
minimum k such that there exist P, Q in P^k with X + P = Q. The formal Minkowski
difference is the entire difference between the ReLU question and the ICNN question.
Lemma 9 is full additivity, the inclusion-exclusion extension of the valuation
property, which they note has a genuinely deep proof going through the Euler
characteristic. Lemma 10 converts a polyhedral subdivision of the simplex into a
formal difference for free, because intersections of cells are faces and P^k is closed
under faces.

**Their all-n statement, verbatim.** Section 1.1: "it could be the case that two
hidden layers suffice for computing the maximum of n numbers for all n." And earlier:
"While we resolve the previously open question of whether MAX_5 can be represented
with two hidden layers, it intriguingly remains open whether the same is possible for
MAX_6." That n = 6 sentence is now obsolete, which is exactly the pattern the campaign
should expect at n = 11.

---

## 5. Lower-bound machinery, and precisely which hypothesis fails

**Grillo, Hertrich, Loho, braid arrangement (arXiv:2502.09324v2, NeurIPS 2025).** The
invariant is not a polytope invariant at all. Theorem 2.2 establishes that functions
representable by a network conforming with the braid fan form a finite-dimensional
vector space isomorphic to set functions on subsets of [d]. They then build subspaces
F_L(k) indexed by a lattice L and a rank parameter, and the engine is Proposition 4.7:
applying one rank-2 maxout layer maps F_L(k) into F_L(k^2+k). Iterating from k_1 = 2
gives Theorem 4.8, M^2_{B_d}(l) contained in V_{B_d}(2^{2^l}-1), hence Corollary 4.9,
the Omega(log log d) bound. Section 5 gives a purely combinatorial reproof that
max{0,x_1,...,x_4} needs three hidden layers under the same hypothesis.

The failing hypothesis is stated crisply and the authors themselves flag it in Section
7: B_d^0-conformity requires every neuron's breakpoints to lie on hyperplanes
x_i = x_j or x_i = 0. Bakaev et al.'s MAX_5 network manifestly violates this, since it
creates breakpoints on x_1+x_2 = x_3+x_4 and on 2x_5 = x_i+x_j. The conclusion in
Section 7 is explicit: "this implies that considering B_d^0-conforming networks is a
real restriction. While this indicates that the doubly-logarithmic lower bound may not
extend to all networks." They conjecture nothing about MAX_n. They propose only a
direction: use different underlying fans instead of the braid fan.

**Grillo and Hofmann, sparse maxout (arXiv:2510.14068, Indagationes Mathematicae
2026).** The invariant is the dimension of a virtual polytope, where Definition 8 sets
dim(V) = min{dim(P+Q) : V = P-Q}, a minimum over all representations as a formal
difference. Theorem 7 is the duality: functions computed by indegree-constrained
maxout networks correspond bijectively to a class of virtual polytopes, as a vector
space and semigroup isomorphism. Theorem 11 is the bound, dim(V) <= sum over k of
(r_k - 1) times the product of d_i for i > k. Theorem 12 shows it is attained. Theorem
16 converts it: with m_l that same quantity, the network class sits inside functions
expressible with maxima of at most m_l + 1 affine terms, using the fact that a
polytope of dimension d is a signed combination of simplices of dimension at most d.
Theorem 18 then exhibits an explicit separator, a sum of n-2 ReLUs maxed against a
pairwise max, which is in the two-hidden-layer fully connected class but outside
M_n(n).

The failing hypothesis is the indegree constraint d_i. The whole bound is a product of
the d_i, so with unrestricted width d_i equals the previous layer's width and m_l is
unbounded, and Theorem 11 becomes vacuous. This machinery cannot in its current form
say anything about unrestricted-width networks. There is no MAX_n conjecture in the
paper.

**Koutschan, Moser, Ponomarchuk, Schicho (arXiv:2305.16933).** The invariant is the
zero-summand property. A polytope P is a zero summand if P plus some zero-volume
polytopes equals a sum of zero-volume polytopes. Lemma 5.1 shows the property descends
to faces, Corollary 5.2 concludes by induction on dimension that an n-simplex is not a
zero summand, and Theorem 5.4 gives the arity result: max(0,x_1,...,x_n) is not a
linear combination of maxima of fewer than n+1 affine functions. This is the only
lower-bound tool in the whole cluster that is stated for signed combinations over the
reals with no weight or breakpoint restriction, which is why it survives into Ruess et
al. as Proposition 4.2. It bounds arity and hence k, not depth.

---

## 6. Four items not in the local corpus

**Bakaev, Brunck, Yehudayoff, "Approximation Depth of Convex Polytopes"
(arXiv:2507.07779v1, 10 July 2025, math.MG).** Directly on the campaign's target and I
recommend adding it. It studies the P^{n,d} hierarchy verbatim, defines two distances
(in-out distance, and an empty-corner distance defined only for the simplex), and
proves stable indecomposability: Theorem 1 says Minkowski summation cannot decrease
in-out distance to the simplex, Theorem 2 the analogue for the empty-corner
co-distance. Main consequence: if a sequence of polytopes in P^{n,d} converges to the
simplex in Hausdorff metric then d >= ceil(log_2(n+1)).

The critical caveat, and I want the campaign to not misread this. Their neural model
has inner gates computing sums of c_j*max(a_j, b_j) with c_j > 0 strictly. That is the
unsigned model. Their sentence "The depth complexity of the simplex Delta_n is known
to be d = ceil(log_2(n+1)), the lower bound was proved by Valerdi" is a statement about
membership in P^{n,d}, not about the formal-difference model of Bakaev et al.'s own
Lemma 8. So the log_2 lower bound is proven, robustly, for exactly the model that lacks
negative coefficients. Signed cancellation is the single hypothesis separating a proven
ceil(log_2(n+1)) from a completely open problem.

**Brandenburg, Grillo, Hertrich, "Decomposition Polyhedra of Piecewise Linear
Functions" (arXiv:2410.04907, v2 revised 4 June 2026).** In the June-Sept window by
revision. Decomposing a CPWL function as a difference of two convex CPWL functions
with as few pieces as possible, framed as a polyhedron whose vertices are the minimal
solutions. Adjacent to the campaign's signed-decomposition machinery.

**Balakin, Cox, Loho, Sturmfels, "Maxout Polytopes" (arXiv:2509.21286).** Parameter
spaces and extremal f-vectors for maxout networks with non-negative weights after the
first layer, plus separating hypersurfaces when a layer is added. Non-negative weights
again, so it is on the ICNN side of the divide, but the separating-hypersurface
analysis is the kind of layer-addition invariant the campaign is hunting for.

**Hertrich and Stargalla, "Tropical Circuits with Scalar Multiplication Gates"
(arXiv:2607.11540, July 2026).** Checked; exponential size separations between
monotone and non-monotone maxout networks for spanning trees and matchings. Size, not
depth. Not directly useful.

I also checked and rejected: 2606.07728 (ICLR 2026, region adjacency graph geometry,
no depth bound), 2411.03006 (virtual extension complexity, size lower bounds only),
2605.03601 (parameter identifiability).

---

## 7. What is genuinely known and what is conjectured, as of 2026-09-02

**Proven, unrestricted real weights, exact global representation on all of R^n.**

- For every n with 3 <= n <= 10, the minimum number of hidden layers for max_n is
  exactly 2. Upper bound Ruess et al. Theorem 1.1, lower bound Mukherjee-Basu.
- For every n > 10, max_n needs at most ceil(log_5(n/2)) + 1 hidden layers. Ruess et
  al. Corollary 1.2.
- For d <= 9, every CPWL function on R^d has a two-hidden-layer representation.
  Corollary 1.3.
- No CPWL function, in any dimension, is known to require more than two hidden layers.
  This is stated in those words by Ruess et al., Wang-Basu, Bakaev et al., and
  Grillo-Hertrich-Loho.
- Safran (arXiv:2601.01417, COLT 2026): width Omega(d^(1+1/(2^(k-2)-1))) is necessary
  at any depth k with 3 <= k <= log_2 log_2(d), unconditional, unrestricted weights.
  This is a width bound at fixed depth. It does not exclude depth 3 at unbounded
  width, so it does not touch MAX_11.
- Safran (arXiv:2608.23877, 24 Aug 2026): exponential L2 depth hierarchy for every
  adjacent pair of fixed depths from 3 upward, unrestricted weights. The separating
  functions are constructed for the purpose; this says nothing about max_n
  specifically.

**Proven only under a restricted hypothesis. The quantifiers matter and I am stating
them exactly.**

- Integer weights: ceil(log_2 n) hidden layers necessary for max_n. Haase-Hertrich-Loho,
  ICLR 2023.
- Decimal-fraction weights: ceil(log_3(n+1)) necessary for F_n = max{0,x_1,...,x_n}.
  N-ary fractions: Omega(ln n / ln ln N). Averkov-Hojny-Merkert, ICLR 2025.
- Networks conforming with the braid fan, meaning all breakpoints on x_i = x_j or
  x_i = 0: Omega(log log d), and three layers necessary for max{0,x_1,...,x_4}.
  Grillo-Hertrich-Loho, NeurIPS 2025.
- Indegree-constrained sparse maxout: strict depth hierarchy from the virtual-polytope
  dimension bound. Grillo-Hofmann.
- Non-negative-coefficient model, no formal Minkowski difference, equivalently ICNN and
  monotone networks: ceil(log_2(n+1)) for the simplex, Valerdi, and stably so under
  approximation, Bakaev-Brunck-Yehudayoff 2507.07779.
- Arity, unrestricted signed real combinations: max(0,x_1,...,x_n) is not a signed
  combination of maxima of fewer than n+1 affine functions. Koutschan et al. Theorem
  5.4. This is the one unrestricted lower-bound tool in the cluster and it constrains
  k, not depth.

**Conjectured or open.**

- Whether two hidden layers suffice for max_n for all n. Bakaev et al. say it could be
  the case. Wang-Basu say it remains completely open. Nobody conjectures either way in
  print.
- MAX_11 specifically. Not mentioned in any of the three construction papers. No
  claimed attempt, no reported failure, no obstruction named.
- The original Hertrich-Basu-Di Summa-Skutella conjecture that ceil(log_2(n+1)) is
  necessary is disproved for CPWL depth as a whole by Bakaev et al.

**Two things a campaign at n = 11 must not confuse.**

First, both construction papers explicitly disclaim completeness. Wang-Basu Section 6
states that non-existence of a solution to the linear system does not imply
non-existence of a two-hidden-layer representation. Ruess et al. make the same point
more quietly in Section 2, that an unsolvable system means only that the candidate set
is insufficient. Exhausting all 12,103,014 k=5 multisets at n=11 and finding no
certificate would establish a negative result about that ansatz and nothing about
MAX_11.

Second, Corollary 4.3 gives k >= 5 as necessary at n = 11, not sufficient. The bound
comes from 2k+1 >= n-1 via a dimension count on conv(Z_A union Z_B), and there is no
result anywhere saying k = k_min suffices. Empirically it did at n = 8 for Ruess et al.
and did not for Wang-Basu.

**Frontier changes to flag: none.** No new n=11 construction, no new real-weight depth
lower bound, no extension of the exact-linear-algebra method, and no published
discussion of an n=11 obstacle exists as of today. The only movement in the
June-September 2026 window is the Ruess et al. preprint itself (22 July), the
Wang-Basu preprint (25 August), the Safran L2 hierarchy (24 August, not about max_n),
and the v2 revision of the decomposition-polyhedra paper (4 June).

**Files worth adding to the corpus:** https://arxiv.org/abs/2507.07779,
https://arxiv.org/abs/2410.04907, https://arxiv.org/abs/2509.21286. The first is the
one I would prioritise, because it is by the same team as the STOC paper, it
formalises exactly the P^k model the campaign is working in, and it makes precise that
signed cancellation is the sole hypothesis standing between the field and a proven
logarithmic lower bound. A local copy of its PDF is already at
`/home/ubuntu/.claude/projects/-data-projects-relu-depth-frontier-research/e3c7772e-be35-41c0-9f1a-451dc7cbd45b/tool-results/webfetch-1788311198389-tacsow.pdf`
with extracted text alongside it as `ad.txt`.

---

## Sources

- https://arxiv.org/abs/2607.21651 - Ruess et al., Shallower ReLU Network Representations via Exact Linear Algebra
- https://arxiv.org/abs/2608.25221 - Wang & Basu, Representing MAX functions using two-hidden-layer ReLU networks
- https://arxiv.org/abs/2505.14338 - Bakaev et al., Better Neural Network Expressivity: Subdividing the Simplex
- https://arxiv.org/abs/2502.09324 - Grillo, Hertrich, Loho, Depth-Bounds for Neural Networks via the Braid Arrangement
- https://www.arxiv.org/pdf/2510.14068 - Grillo & Hofmann, On the expressivity of sparse maxout networks
- https://arxiv.org/abs/2601.01417 - Safran, A Depth Hierarchy for Computing the Maximum in ReLU Networks
- https://arxiv.org/abs/2608.23877 - Safran, Every Layer Counts
- https://arxiv.org/pdf/2507.07779 - Bakaev, Brunck, Yehudayoff, Approximation Depth of Convex Polytopes
- https://arxiv.org/pdf/2410.04907 - Brandenburg, Grillo, Hertrich, Decomposition Polyhedra of Piecewise Linear Functions
- https://arxiv.org/abs/2509.21286 - Balakin, Cox, Loho, Sturmfels, Maxout Polytopes
- https://arxiv.org/abs/2607.11540 - Hertrich & Stargalla, Tropical Circuits with Scalar Multiplication Gates
- https://arxiv.org/abs/2606.07728 - Characterizing the Discrete Geometry of ReLU Networks (checked, not relevant)
- https://arxiv.org/abs/2411.03006 - Neural Networks and (Virtual) Extended Formulations (checked, size only)
- https://arxiv.org/pdf/2402.15315 - Valerdi, On Minimal Depth in Neural Networks
- https://arxiv.org/abs/2502.06283 - Averkov, Hojny, Merkert, Rational ReLU Networks With Bounded Depth
- https://christophhertrich.gitlab.io/ - Hertrich publication list
- https://lohomath.github.io/ - Loho publication list
- https://github.com/kilianar/max-relu-certificates - certificate repository for n <= 10
