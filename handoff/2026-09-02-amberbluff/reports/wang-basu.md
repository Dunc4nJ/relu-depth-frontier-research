# Deep read: Wang & Basu, "Representing MAX functions using two-hidden-layer ReLU networks"

arXiv:2608.25221v1 [cs.LG], 25 Aug 2026. Zhimao Wang and Amitabh Basu, Johns Hopkins.
Source text: `/data/projects/relu-depth-frontier-research/literature/papers/2608.25221.txt`
Body is 11 pages, lines 1 through 577. Everything after that is two coefficient tables, Appendix A on pages 12 and 13 for MAX7, Appendix B on pages 13 through 24 for MAX8.

I read the entire paper, parsed both appendix tables in full, independently verified every identity in the paper with exact rational arithmetic, and independently reproduced all of its counting data from scratch.

---

## Bottom line

Wang and Basu use exactly the Rueß ansatz. There is nothing outside the braid arrangement, no biases, no new generator directions, no lower bounds, no conjectures, and no theory beyond three short lemmas. Their contribution is a second, independently found solution of a slightly different linear system, obtained by computer search over the same atom space. For the MAX11 campaign the paper is close to a null result on new ideas, but it yields two hard, actionable facts that I established by reproducing their numbers exactly.

**Fact one.** I recomputed their variable counts from scratch by Burnside's lemma over the symmetric group acting on unordered pairs of multisets of unordered index-pairs. Every number in their Table 1 and Section 1.3 came out exactly. Extending the same count to the campaign's target gives 12,179,657 for N equal to 11 at k equal to 5. That is precisely the campaign's stated column count. So the campaign's variable space is already the fully quotiented one, and Wang-Basu's "additional functional symmetries" buy nothing.

**Fact two.** I also recomputed the row counts. Their constraint counts equal N plus the number of ambiguous unordered pairs of eta-vectors. The campaign's row count of 657,833 instead equals the number of primitive ambiguous hinge rays plus N, which I computed as 657,822 plus 11. So the campaign is running Rueß's coarser and strictly better-conditioned system, and Wang-Basu's formulation would inflate the campaign's system to 2,324,333 rows while shrinking the feasible set. Do not adopt it.

| System, N = 11, k = 5 | rows | columns |
|---|---|---|
| campaign / Rueß, primitive ambiguous rays plus N | 657,833 | 12,179,657 |
| Wang-Basu, per-eta-pair zeroing plus N | 2,324,333 | 12,179,657 |

---

## 1. The construction for MAX5 through MAX8

### Architecture

Page 2, equation (1), and Definition 1.1 on page 3. An *atom pattern of degree k* is a list

```
P = [p_1, ..., p_k | q_1, ..., q_k],   p_i, q_i in {1,...,N} x {1,...,N}
```

with repetition allowed, including diagonal pairs of the form (a,a). With m_(a,b)(x) = max{x_a, x_b}, the pattern defines

```
L_P(x) = sum_i m_{p_i}(x)
R_P(x) = sum_i m_{q_i}(x)
A_P(x) = max{ L_P(x), R_P(x) }
```

The first hidden layer computes the pairwise maxima only. The second hidden layer computes the single outer maximum. Their representations are signed rational combinations of orbit-sums of such atoms. Verbatim from the abstract, the terms are

```
max{ sum_{r=1..s} max(x_{a_r}, x_{b_r}),  sum_{r=1..s} max(x_{c_r}, x_{d_r}) }
```

with all indices in {1,...,N}. They call these *atoms*, and *atoms of degree k* for fixed k.

### First-layer directions

Every first-layer neuron is max(x_a, x_b), whose only breakpoint hyperplane is x_a = x_b. All first-layer hyperplanes therefore lie in the braid arrangement. Diagonal pairs (a,a) contribute the linear term x_a and no breakpoint at all. There is no neuron with a direction outside the braid arrangement anywhere in the paper. There are no biases anywhere either. The whole ansatz is positively homogeneous of degree one, matching MAX_N, and the paper never discusses bias removal because the question never arises.

On the point that motivated the question: this paper provides no evidence that the Rueß ansatz is incomplete, and no evidence for generator directions outside {x_i = x_j}.

### Second-layer directions

The nonlinearity that matters lives in the second layer, whose ReLU breaks on the piecewise-linear hypersurface L_P = R_P. On the sorted chamber that surface degenerates to a hyperplane with normal eta_R - eta_L, a nonnegative-integer difference vector, not a braid direction. This is the only place where non-braid geometry enters, and it is the same place it enters in Rueß.

### The actual coefficients

For MAX5 the paper gives two identities. Theorem 2.1 on page 7:

```
2 MAX5 = -(2/5) G_{O[P0]} + (1/30) G_{O[P3]} + (1/120) G_{O[P16]} + (1/60) G_{O[P22]}
         + (1/60) G_{O[P37]} - (1/60) G_{O[P45]} - (1/60) G_{O[P81]}

P0  = [11,11 | 11,11]
P3  = [11,11 | 11,23]
P16 = [11,11 | 23,45]
P22 = [11,12 | 11,34]
P37 = [11,12 | 13,45]
P45 = [11,12 | 23,45]
P81 = [11,23 | 12,45]
```

Theorem 2.3 on page 8 gives a five-orbit alternative:

```
2 MAX5 = -(2/5) G_{O[P0]} + (1/15) G_{O[P3]} - (1/40) G_{O[P69]} + (1/20) G_{O[P95]} - (1/30) G_{O[P97]}

P69 = [11,22 | 34,35]
P95 = [11,23 | 24,25]
P97 = [11,23 | 25,34]
```

Theorem 3.1 on page 8 gives MAX6 at k equal to 2:

```
2 MAX6 = -(1/3) G_{O[P0]} + (1/90) G_{O[P22]} + (1/180) G_{O[P51]} - (1/360) G_{O[P71]}
         + (1/180) G_{O[P130]} - (1/90) G_{O[P135]} + (1/720) G_{O[P136]}

P0   = [11,11 | 11,11]
P22  = [11,12 | 11,34]
P51  = [11,12 | 34,56]
P71  = [11,22 | 34,56]
P130 = [12,13 | 14,56]
P135 = [12,13 | 24,56]
P136 = [12,13 | 45,46]
```

Theorem 3.3 on page 9 gives a nine-orbit MAX6 alternative. It is false as printed. See the erratum section below.

Theorem 4.1 on page 9 is MAX7 as 109 orbit terms at k equal to 3, listed in Table 2. Theorem 5.1 on page 10 is MAX8 as 1,290 orbit terms at k equal to 4, listed in Table 3. I parsed both tables in full; both are complete and consistently numbered, 1 through 109 and 1 through 1290 with no gaps.

### There is no closed-form family

Nothing in the paper is parameterized by N. Each identity is an independent numerical solve. The coefficient supports do not nest, the denominators follow no pattern, and there is no formula that could be pushed to N equal to 11. This is the single most disappointing finding relative to the brief: no closed form exists here to generalize.

### Statistics of the solutions

Extracted from my parse of Tables 2 and 3.

| | MAX7, k = 3 | MAX8, k = 4 |
|---|---|---|
| orbit terms | 109 | 1290 |
| negative coefficients | 52 | 642 |
| terms containing at least one diagonal pair | 89 | 1253 |
| terms sharing at least one letter between the two sides | 97 | 1244 |
| smallest and largest absolute coefficient | 1/40320 to 13/42 | 1/604800 to 77741/1280 |
| lowest common denominator of all coefficients | 241,920 | 116,121,600 |
| distinct-letter histogram | 1:1, 3:2, 4:5, 6:46, 7:55 | 1:1, 3:2, 4:8, 6:3, 7:4, 8:1272 |
| distinct atom classes, i.e. second-layer ReLUs | 276,997 | 28,362,384 |
| first-layer ReLUs, one per unordered pair | 21 | 28 |

Note the absence of terms using exactly 2 or exactly 5 distinct letters in both tables. The first hidden layer is tiny. The second layer is enormous. The solutions are dense and unstructured; they read like arbitrary points in a high-dimensional solution polytope, not like a family.

---

## 2. Every structural statement in the paper

There are exactly three results and one definition. That is the complete theoretical content.

### Lemma 1.2, page 3

On the sorted chamber `C = {x : x_1 >= x_2 >= ... >= x_N}`, every atom is a maximum of two linear forms, with a closed-form recipe. There exist eta_L and eta_R in the nonnegative integer lattice with both L1 norms equal to k such that `A_P(x) = max{<eta_L, x>, <eta_R, x>}` on C, where

```
(eta_L)_i = sum_{j=1..k} 1[min(p_j) = i]
(eta_R)_i = sum_{j=1..k} 1[min(q_j) = i]
```

The proof is one line: on C, max{x_a, x_b} = x_min(a,b), so each side-sum is a count of min-indices. This is the standard collapse the campaign already uses.

### Proposition 1.3, page 5

Any orbit-coefficient vector alpha induces coefficients c_T on a finite index set T of eta-pairs, with each c_T a linear function of alpha, giving a matrix equation `M alpha = c`. The paper notes on page 5 that this map is not injective, with the explicit example that

```
[(1,2),(2,3) | (2,3),(3,4)]   and   [(1,3),(2,4) | (2,4),(3,3)]
```

are inequivalent atom patterns of degree 2 over N equal to 4 that both produce eta_L = (1,1,0,0) and eta_R = (0,1,1,0). Their remark, verbatim: "the symmetries we consider above do not cover all the symmetries for functional equivalence of the atoms."

### Definition 1.4, page 5

An atom represented by a pattern P is *ambiguous over C* if there exist x, x' in C such that L_P(x) > R_P(x) and L_P(x') < R_P(x'). Equivalently, the pattern is unambiguous if and only if eta_R - eta_L lies in the polar cone of C or its negative.

There is a cleaner equivalent form that I verified and that the paper does not state. Write cum(eta) for the vector of partial sums. Then the pair is unambiguous if and only if cum(eta_L) and cum(eta_R) are comparable in the componentwise partial order. Ambiguity is exactly incomparability in that order. This turns the constraint count into a poset-comparability count and is how I computed every row count below in seconds.

### Sufficient condition (5), page 6

Splitting T into ambiguous part T_A and unambiguous part T_U, they impose

```
x_1 = sum_{T in T_U} c_T max{<eta_L^T, x>, <eta_R^T, x>},    c_T = 0 for all T in T_A.
```

Because each max on the right is linear on C for unambiguous T, this is a finite linear system in the orbit coefficients.

### What is absent

No normal forms. No necessary conditions on two-hidden-layer representations of MAX_N. No invariants. No "any representation must contain" statements. No symmetrization lemma beyond the standard restrict-to-one-chamber argument, which they attribute to Sections 3 and 4 of Rueß. No homogeneity or bias-removal lemma. No polyhedral or tropical characterization, no Newton polytopes, no virtual polytopes, no Minkowski differences.

The only geometry in the paper is one sentence on page 2: each side-sum is the support function of a zonotope, the outer maximum is the support function of the convex hull of the two zonotopes, and clearing denominators turns an identity into an equality of Minkowski sums of polytopes. That is the zonotope picture the campaign already has.

---

## 3. What they say about N >= 9, N = 11, all N, conjectures, obstacles

Almost nothing, and they offer no conjecture in either direction.

The abstract says the general question "remains completely open if the right answer is a constant number of hidden layers, possibly even 2, or not." That is the strongest statement of belief anywhere in the paper.

They stopped at 8 purely for compute reasons, stated in Section 1.3 on page 7 and repeated in Section 6 on page 10.

| N | k | constraints | variables | outcome |
|---|---|---|---|---|
| 5 | 2 | 20 | 131 | solved |
| 6 | 2 | 41 | 144 | solved |
| 7 | 3 | 1,057 | 4,469 | solved |
| 8 | 4 | 21,953 | 193,623 | solved |
| 9 | 4 | 51,984 | 210,540 | not solved, exact arithmetic too slow |
| 10 | 4 | 112,837 | 216,428 | not solved, exact arithmetic too slow |

Rows 1 through 4 are their Table 1 on page 6. Rows 5 and 6 are from Section 1.3, page 7. Their words on page 7: "We were unable to solve the systems with exact rational arithmetic in the amount of compute time available to us."

There is no discussion of a threshold, no growth analysis, no obstruction, and no speculation about where the ansatz might fail. Section 6 contains the one honest caveat worth quoting in full, page 10:

> "We emphasize that a solution to the corresponding linear system is a sufficient certificate for representation using ReLU networks with two hidden layers; it is not a complete characterization. In other words, nonexistence of a solution does not imply nonexistence of such a representation."

Note the scale in the table. A system with 51,984 rows and 210,540 columns is small by the campaign's standards. Wang and Basu failed at N equal to 9 on a system three orders of magnitude smaller than the campaign's. This is a linear-algebra engineering gap, not a mathematical one.

The one substantive discrepancy in outcomes is MAX8. Rueß obtain MAX8 at k equal to 3; Wang and Basu needed k equal to 4. In their formulation the k equal to 3 system for N equal to 8 has only 2,318 constraints and 4,716 variables, which I computed and which is trivially solvable, so their use of k equal to 4 means that system is infeasible for them. This is direct evidence that their per-eta-pair zeroing is strictly more restrictive than Rueß's per-ray aggregation. It is the clearest reason not to migrate the campaign to their formulation.

---

## 4. Proof technique for the constructions

Pure computer search over exact rational linear algebra. The pipeline, from Section 1.2 on pages 4 through 6:

1. Quotient atom patterns by three functional symmetries: reversal of an ordered pair, permutation of the k terms within each side independently, and swapping the left and right sides.
2. Take Sigma_N orbits of the resulting equivalence classes, giving the set P/Sigma_N.
3. Choose lexicographically minimal canonical representatives.
4. Form the symmetric orbit-sum functions G_O = sum over classes C in O of A_C.
5. Assemble the linear system from sufficient condition (5).
6. Solve over the rationals.

Correctness of the resulting identity follows because each G_O is symmetric by construction, so agreement on the single sorted chamber implies agreement on all of R^N. There is no explicit formula, no simplex subdivision, no induction, and no human-readable proof of any of the four identities. Each is a certificate, not an argument.

---

## 5. Lower-bound content

None whatsoever. The paper contains no impossibility result, partial or otherwise, and no obstruction argument.

Its only lower-bound statements are citations in the introduction on page 2: the general lower bound remains 2 and no continuous piecewise linear function is known that requires more than 2 hidden layers; integer weights force the logarithmic bound (Haase, Hertrich, Loho, ICLR 2023); decimal-fraction weights give a ceiling-log-base-3-of-n bound (Averkov, Hojny, Merkert, arXiv:2502.06283); and conditional super-constant lower bounds are due to Grillo, Hertrich, Loho via the braid arrangement (NeurIPS).

---

## 6. Relationship to Bakaev et al. and Rueß et al.

### Bakaev, Brunck, Hertrich, Stade, Yehudayoff, STOC 2026

Credited on page 2 with the MAX5 breakthrough and with showing that ceiling(log_3(n-1)) + 1 hidden layers suffice under arbitrary real weights. They note MAX_N was stated as open for N >= 6 in that paper.

Minor inaccuracy worth flagging: Rueß's own paper states the Bakaev bound as ceiling(log_3(n-2)) + 1, and describes Bakaev as constructing max5 and using it to represent max_n for n >= 4 with ceiling(log_3(n-2)) + 1 hidden layers. One of the two citations is off by one in the argument. Wang and Basu do not use or extend Bakaev's simplex-subdivision technique in any way.

### Rueß, Averkov, Brunck, Grillo, Hertrich, Loho, Stade, Stargalla, Sun, Winter, arXiv:2607.21651

The paper is explicit that the work is independent and concurrent, that Rueß reach N equal to 10 while they reach 8, and that Rueß get MAX8 more compactly at k equal to 3. Rueß's corollary, from their own abstract, is ceiling(log_5(n/2)) + 1 hidden layers for max_n.

Wang and Basu claim two technical differences, in Section 1.2 on page 4 and Section 1.3 on page 7. I checked both against Rueß's paper, which is present locally at `literature/papers/2607.21651.txt`.

**The symmetry claim is wrong.** Rueß Section 4.1.1 defines a *template* as an equivalence class of pairs (A,B) under

```
(A, B) ~ (B, A) ~ (tau A, tau B) ~ (tau B, tau A),   tau in S_n
```

where A and B are already multisets of unordered pairs from `E_n = {(i,j) : 1 <= i <= j <= n}`, diagonal elements included. That is the same quotient Wang and Basu describe. Multiset semantics already absorbs pair reversal and within-side reordering. Rueß even give the graph-theoretic reading: a template is a two-edge-colored multigraph on n vertices with the two colors interchangeable, enumerated with nauty. Wang and Basu write on page 7 that "the other symmetries seem to be unique to our approach," and that is incorrect. My Burnside count over the fully quotiented space reproduces both their variable counts and the campaign's column count, confirming the two spaces coincide.

**The constraint claim is real, and cuts against them.** Rueß's equations (2) and (3), page 7 of their paper, aggregate hinge coefficients by direction d:

```
sum_{A,B} lambda_{A,B} c_{A,B,d} = 0   for all d in union of D_{A,B}
sum_{A,B} lambda_{A,B} L_{A,B}(x) = x_n
```

Their Remark 4.1 then identifies d with -d via `ReLU(-d'x) = ReLU(d'x) - d'x`, identifies positive scalar multiples via positive homogeneity, and drops unambiguous directions from the constraint set because on C such a hinge is either identically zero or identically linear.

Wang and Basu instead force each individual c_T to vanish for every ambiguous eta-pair T. Per-pair zeroing implies per-ray zeroing but not conversely, so on the ambiguous side their system is strictly tighter. On the unambiguous side theirs is looser, since they let unambiguous terms contribute to the linear part rather than dropping them. The two systems are genuinely incomparable, which is why the two groups found different solutions, but the MAX8 evidence says the Rueß side of the trade is the better one.

---

## 7. Independent verification, and one erratum

I wrote an exact verifier and checked all four theorems plus both alternates on random integer points in full generality, evaluating the actual nested maxima rather than the sorted-chamber shortcut, with rational arithmetic throughout. Three findings.

### The orbit-sum convention in the paper is ambiguous, and only one reading is correct

Definition of G_O in Section 1.2 is a sum over distinct equivalence classes in the orbit. The appendix table captions instead say the coefficient belongs to "the function obtained by summing all atoms obtained when the letters range over all possible values."

These differ by the letter-automorphism factor of each pattern. I tested three readings: sum over distinct functional equivalence classes, sum over all N! permutations, and sum over all injective assignments of the abstract letters to distinct coordinates. Only the injection reading makes any identity true, and it makes all of them true. Anyone reusing these certificates must use the injection convention or every identity will be off by a per-orbit integer factor.

### Five of the six identities verify exactly

| identity | orbit terms | random test points | result |
|---|---|---|---|
| Theorem 2.1, MAX5, k = 2 | 7 | 6 | exact |
| Theorem 2.3, MAX5, k = 2 | 5 | 6 | exact |
| Theorem 3.1, MAX6, k = 2 | 7 | 6 | exact |
| Theorem 3.3, MAX6, k = 2 | 9 | 6 | FALSE |
| Theorem 4.1, MAX7, k = 3 | 109 | 6 | exact |
| Theorem 5.1, MAX8, k = 4 | 1290 | 4 | exact |

All checks used unsorted random integer points and exact Fraction arithmetic, so they certify the global identity, not merely the sorted-chamber restriction.

### Erratum: Theorem 3.3 on page 9 is false as printed

Not only do the printed coefficients fail; 2 MAX6 is not in the linear span of the nine listed orbit functions at all. I verified this by exact Gaussian elimination on a 40-point sampled system, which came out inconsistent. Because the three candidate conventions differ only by per-column positive scalars, the column span is convention independent, so no rescaling and no single coefficient correction can save it. I confirmed separately that freeing any single one of the nine coefficients leaves the system inconsistent.

I then enumerated all 144 degree-2 orbits for N equal to 6 and searched for a single-pattern substitution that repairs it. Exactly one exists:

```
P69 = [11, 22 | 34, 35]    should be    P69 = [11, 22 | 34, 34]
```

With that one change and the printed coefficients unaltered, the identity is exact. I confirmed it on 40 random integer points. The likely cause is a copy of the N equal to 5 pattern P69, which is genuinely [11,22 | 34,35] in Theorem 2.3, into the N equal to 6 list.

There is also a typographical inconsistency on page 9, where the MAX8 orbit count is written as 193623 in one sentence and 193263 in the next. The correct value is 193,623, matching Table 1 and my Burnside count.

---

## 8. Independent reproduction of all counting data, and projection to N = 11

I built two independent counters and validated them against every number the paper reports.

### Variable counts by Burnside's lemma

Orbits of Sigma_N acting on unordered pairs of size-k multisets of unordered index-pairs, computed via the cycle index. Every published value reproduced exactly.

| N | k | |P/Sigma_N| computed | paper value |
|---|---|---|---|
| 5 | 2 | 131 | 131 |
| 6 | 2 | 144 | 144 |
| 7 | 3 | 4,469 | 4,469 |
| 8 | 3 | 4,716 | not reported |
| 8 | 4 | 193,623 | 193,623 |
| 9 | 4 | 210,540 | 210,540 |
| 10 | 4 | 216,428 | 216,428 |
| 11 | 4 | 218,078 | not reported |
| 9 | 5 | 10,464,107 | not reported |
| 10 | 5 | 11,688,445 | not reported |
| **11** | **5** | **12,179,657** | **not reported; equals the campaign's column count** |

I also brute-force enumerated the classes for N equal to 5 and 6 as a cross-check: 7,260 equivalence classes giving 131 orbits, and 26,796 equivalence classes giving 144 orbits.

### Constraint counts

Wang-Basu constraints equal N plus the number of *ambiguous* unordered pairs of eta-vectors, where ambiguity is incomparability of the cumulative-sum vectors. Every published value reproduced exactly.

| N | k | eta-vectors | unordered pairs | ambiguous pairs | N + ambiguous | paper value |
|---|---|---|---|---|---|---|
| 5 | 2 | 15 | 120 | 15 | 20 | 20 |
| 6 | 2 | 21 | 231 | 35 | 41 | 41 |
| 7 | 3 | 84 | 3,570 | 1,050 | 1,057 | 1,057 |
| 8 | 3 | 120 | 7,260 | 2,310 | 2,318 | not reported |
| 8 | 4 | 330 | 54,615 | 21,945 | 21,953 | 21,953 |
| 9 | 4 | 495 | 122,760 | 51,975 | 51,984 | 51,984 |
| 10 | 4 | 715 | 255,970 | 112,827 | 112,837 | 112,837 |
| 11 | 4 | 1,001 | 501,501 | 228,228 | 228,239 | not reported |
| 9 | 5 | 1,287 | 828,828 | 399,399 | 399,408 | not reported |
| 10 | 5 | 2,002 | 2,005,003 | 1,003,002 | 1,003,012 | not reported |
| 11 | 5 | 3,003 | 4,510,506 | 2,324,322 | **2,324,333** | not reported |

### Rueß-style row counts, and the identification of the campaign's system

I then counted distinct ambiguous hinge directions up to sign, and again after dividing by the gcd to get primitive rays, matching Remark 4.1's two identifications.

| N | k | ambiguous directions up to sign | primitive ambiguous rays | primitive + N |
|---|---|---|---|---|
| 7 | 3 | 630 | 630 | 637 |
| 8 | 3 | 1,428 | 1,428 | 1,436 |
| 8 | 4 | 8,421 | 8,295 | 8,303 |
| 9 | 4 | 20,895 | 20,685 | 20,694 |
| 10 | 4 | 47,487 | 47,157 | 47,167 |
| **11** | **5** | 658,317 | 657,822 | **657,833** |

657,833 is exactly the campaign's row count. Combined with the column match at 12,179,657, this pins the campaign's system precisely: it is the Rueß formulation with the full Remark 4.1 reductions applied, over the fully quotiented template space. There is no compression left on the table from either paper.

---

## 9. What is new for the campaign

Against the campaign's existing toolkit of symmetrized pairwise-max templates, alternating finite-difference functionals, signed-mass strata, zonotope face gluing, modular rank tests, and CEGIS on hinge rows, this paper contributes no new technique. Concretely:

- **Nothing outside the braid arrangement.** All first-layer neurons are pairwise maxima. This paper is not evidence that the Rueß ansatz is incomplete, and gives no non-braid generator directions.
- **No new generator directions, no biases, no asymmetric constructions, no closed-form family, no lower bounds, no conjecture on a threshold.**
- **The extra symmetry quotient is illusory.** The campaign's 12,179,657 columns already equal the fully quotiented count, verified independently by Burnside.
- **Their constraint formulation is a downgrade.** Adopting it would take the campaign from 657,833 rows to 2,324,333 rows and shrink the feasible set. The MAX8 k = 3 versus k = 4 discrepancy is the smoking gun that per-eta-pair zeroing loses solutions that per-ray aggregation keeps.
- **Two usable side results.** First, the ambiguity criterion restates cleanly as incomparability of cumulative-sum vectors in the componentwise order, which makes row enumeration and row counting trivial and may help structure the campaign's hinge-row CEGIS. Second, their explicit non-injectivity example on page 5 is a reminder that distinct templates collapse onto the same eta-pair, which is exactly the column-merging structure the campaign should be exploiting if it is not already.

### One audit item to raise with the campaign

The row count of 657,833 confirms the system omits unambiguous hinge directions. For any unambiguous direction d whose inner product is nonnegative on the sorted chamber, `ReLU(d'x) = d'x` there, so that contribution must be folded into the N linear equations rather than silently dropped. If the campaign's assembler drops it instead, the system is the wrong one and any certificate it produces will fail verification. Rueß's Remark 4.1 phrases this purely as a constraint reduction and does not spell out the linear bookkeeping, so it is an easy place for a silent bug.

---

## 10. Artifacts produced

All under `/home/ubuntu/.cache/tmp/claude-1000/-data-projects-relu-depth-frontier-research/e3c7772e-be35-41c0-9f1a-451dc7cbd45b/scratchpad/`:

- `parse_wb.py`, `wb_tables.json` — the fully parsed MAX7 (109 entries) and MAX8 (1290 entries) coefficient tables in machine-readable JSON, each entry as sign, numerator, denominator, left pair list, right pair list.
- `verify_wb.py` — exact verifier for the appendix identities, with orbit stabilizer computation and vectorized permutation evaluation.
- `verify_small.py` — exact verifier for Theorems 2.1, 2.3, 3.1, 3.3.
- `orbits.py` — brute-force orbit enumeration for N = 5, 6, validating 131 and 144.
- `solve33.py`, `diag33.py`, `repair33.py`, `final33.py` — the Theorem 3.3 inconsistency proof, single-coefficient repair search, single-pattern repair search, and confirmation of the repaired identity.
- `burnside.py` — cycle-index variable counter reproducing Table 1 and Section 1.3, projecting to N = 11.
- `rows.py` — constraint counter reproducing Table 1 and Section 1.3, projecting to N = 11.
