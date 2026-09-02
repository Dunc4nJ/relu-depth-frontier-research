# Audit of artifacts/math G-0004 through G-0018

Auditor: cluster1-bounded-theorem. Workspace: /data/projects/relu-depth-frontier-research. Date: 2026-09-02.

**Bottom line.** The range establishes exactly one theorem-grade result: MAX11 is outside the real span of the frozen 16,000-raw/9,804-class same-component pair-atom family, and the 6,740 beta2-common lifts add no new functions to that family. The separating certificate is exact over Q, replayed by two separate scripts, and I re-ran both the standalone dual verifier and the bundle verifier myself with PASS. Everything else in the range is a bounded calibration, a finite-field discovery step, or a design note. Nothing constrains unrestricted two-hidden-layer networks, and every document in the range says so.

**Identifier warning.** Directory numbers under artifacts/math are not the ledger gap numbers. Ledger gap G-0007 is "no T2 reviewer" and ledger gap G-0011 is the later 26,689-column Schur run, while directories G-0007 and G-0011 hold the MAX9 calibration and the exact dual. Directories G-0004 and G-0013 do not exist and never existed in git history. No cleanroom directory corresponds to this range; artifacts/cleanroom holds EXP-0002, the dropped Stage A clean-room verifier, and G-0032 onward. Everything in this range was committed on 2026-08-29, proof core in bc92a01 and round close in 5c47f4f.

## 1. Definitions and the linear-algebra setup

**Atom.** From Rueß et al. Section 4.1: for multisets A, B of k unordered index pairs, the atom is

```
Phi_{A,B}(x) = max( sum_{ij in A} max(x_i,x_j) , sum_{ij in B} max(x_i,x_j) )
```

Hidden layer one computes the pairwise maxima, hidden layer two the outer max, and certificate coefficients sit at the linear output. The campaign fixes n=11, k=5 because Corollary 4.3 forces k >= 5, and loopless edges. The symmetrised atom is the unnormalised sum of the atom over all 11! coordinate permutations.

**Template.** The equivalence class of a pair under simultaneous vertex relabelling plus one global A/B swap, equivalently a two-edge-coloured multigraph up to isomorphism with interchangeable colours. Artifacts also say "class", "quotient representative", or "graph orbit". The symmetrised atom is invariant under both operations, so quotienting does not change the span. That is what "quotient transport" means.

**Orbit.** Two meanings coexist. In G-0006, G-0008, and G-0009 an "orbit row" is one of the 364 S_11-orbits of the grid {0,1,2,3}^11, an evaluation row storing the sum of the atom over all distinct assignments with that level profile. Elsewhere "orbit" means a template class.

**Same-component family and the census 252-source/16,000-raw/9,804-class.** The pinned MAX10 certificate has 402 terms. Exactly 252 have 4+4 edges, 8 distinct loopless union edges, all ten vertices active, and a union with exactly two components. The component census is (2,8):168, (3,7):39, (4,6):32, (5,5):13. Add vertex 11 by one A-edge {a,11} and one B-edge {b,11} with a and b in the same component, a=b allowed. The count of ordered endpoint choices is sum(|K1|^2+|K2|^2) = 16,000 raw pairs, quotiented to 9,804 classes. The cross-component family takes a and b in different components: 9,200 raw, 3,615 classes, every union a spanning tree. The beta2-common family appends one internal loopless edge e to both A and B with vertex 11 left isolated: 6,740 raw, 4,916 classes; in 2,016 raw cases e already sat in one branch, so the branches are edge multisets.

**Ordered-cone semantics and hinge rows.** On the sorted cone `C = {x_1 <= ... <= x_11}` each pairwise max is the higher-index coordinate. For each ordering the atom becomes `L_A + max(0, d.x)` with d the integer zero-sum coefficient vector of `L_B - L_A`. Write d = g*h with h primitive and first nonzero entry positive. If every prefix sum of h is nonnegative, the ReLU is zero or linear on C; otherwise h is active and contributes g*ReLU(h.x) plus a linear correction. Summing over the 11! orderings gives an exact normal form: 11 linear coefficients plus integer coefficients on the active primitive directions. A hinge row of the matrix is one such direction. The matrix keeps 7,135 directions selected adaptively by cutting-plane rounds; the campaign does not claim they exhaust the active directions, whose complete per-column count reaches 104,086 in G-0014. Active hinges are linearly independent modulo linear functions on C by a gradient-jump argument, so a functional identity forces equality of every coordinate and hence of any projection. Infeasibility of the projected system is therefore a valid necessary-condition obstruction. Feasibility of a projected or finite-grid system proves nothing globally.

**The matrix and the target.** M is the 7,146 x 9,804 integer matrix: rows 0..7,134 are hinge coefficients, rows 7,135..7,145 are linear coefficients of x_1..x_11, and column j is the frozen representative of class j. Coefficients are internal a_j = 11! * c_j so that orbit rows keep integer targets. The target b is 11!*MAX11, which on C equals 11!*x_11: zero on every hinge row and 39,916,800 on row 7,145. "MAX11 in the span" means b lies in the real column span of M, which is necessary for MAX11 to equal a real combination of the atoms. A left dual is a row vector lambda with lambda^T M = 0 and lambda^T b != 0; a rational lambda excludes every real coefficient vector. "Cut-only" means lambda is supported on hinge and linear rows only, with no orbit rows.

## 2. Results, exact scope, and no-claim boundaries

**G-0005, balanced-tree separator theorem.** Statement: for odd n >= 5 with k=(n-1)/2, let T be a simple spanning tree with edge classes A and B of size k each, and take the four sorted points z=(0,0,1,1,2^{n-4}), u=(0^4,2^{n-4}), v=(0^3,2^{n-3}), w=(0^2,2^{n-2}). Then

```
C_z F(z) + C_u F(u) + C_v F(v) + C_w F(w) = 0
C_z = 12n(n-2)(n-3), C_u = -5n(n-2)(n-3), C_v = -4n(n-4)(n-2), C_w = -(n-3)(3n^2-2n+4)
```

with coefficient sum 12, while MAX_n equals 2 at every point, so the functional is 24 on MAX_n. At n=11 the reduced tuple is (792,-330,-231,-230) with value 2 on MAX_11. The proof is an induced-subgraph count whose key identity is B_4 = 5A_4 + k^2 + (n-4)A_3. Field: integer identity, valid over R. Scope: only the span of balanced, simple, edge-disjoint two-coloured spanning-tree templates. The audit exhausted all 235 tree shapes and 29,610 balanced colourings at n=11, all zero, and exhibited nonzero values when any single hypothesis is dropped. I replayed check_tree_separator.py: OK, with negative control value -958,003,200. Consequences the artifacts state or imply: the entire 9,200-raw cross-component family is dead as a standalone family; so are the 12,459 full-support coloured trees of G-0007 as a standalone family; at n=9 the theorem predicts G-0007's exact 360 to 361 tree computation. It is a disjunction saying some non-tree template is needed, not a lower bound.

**G-0006, minimal-lift quotient.** Three separate objects. First, the exact isomorphism quotient of the 16,000 raw same-component lifts into 9,804 classes, with NetworkX VF2 as authority and Weisfeiler-Lehman hashing as bucket accelerator only, reproduced by an independent quotient implementation. Second, an orbit-grid sieve on the 364 rows: candidate rank 192 modulo 1,000,003 and 1,000,033 with the target in the modular span, and an exact rational solution of one 192 x 192 subsystem. Third, the complete hinge residual of that 192-term seed is nonzero, confirmed by an independent dynamic program at the off-grid point (0,0,0,0,0,0,0,1,1,2,4). Version 1 subtracted MAX instead of 11!*MAX in the linear residual; v2 fixed the factor; v3 bound custody. No claim about the 9,804-class span is made. "Minimal lift" means one edge per colour from the new vertex, the smallest escape from the G-0005 family.

**G-0007, MAX9 calibration and ansatz.** Exact over Q with python-flint on the pinned upstream expansion kernel: the 739 full-support two-coloured tree atoms of degree 4 have rank 360 and rank 361 with MAX9 appended; 710 bridge trees plus 186 published non-tree atoms have rank 505 and contain MAX9; the resulting 391-term certificate passes the upstream verifier in 13 minutes. Structural census: MAX9 has 337 terms with beta histogram 0:151, 1:123, 2:53, 3:9, 4:1; MAX10 has 402 terms with beta 0:252, 1:104, 2:37, 3:8, 4:1; both are loopless. PROPER_SUBSET_NO_GO is a short human proof that no real linear combination of maxima over proper subsets equals MAX_N, by symmetrising and comparing coefficients on the ordered chamber. It says nothing about nonlinear composition. The proposed MAX11 ansatz is the loopless family with cycle rank at most 4. Shared kernel, single-route NetworkX enumeration, no ledger claim.

**G-0008, cutting-plane rounds.** Round 1: 512 hinge plus 11 linear rows on top of the 364 orbit rows, rank 688 mod p; an exact 678-term rational solution of the 887 constraints whose complete residual has 112,659 nonzero hinges. Round 2: 511 new directions, a 1,398 x 9,804 system of rank 1,183; a 1,169-term exact solution; 114,916 nonzero residual hinges. Round 3: 2,041 more directions for 3,064 total; a modular v2 solve of rank 3,114 with the target a member mod p. Round 4: 7,135 directions and the 7,146 x 9,804 cut block; the 7,510-row system including orbit rows has rank 5,269 and augmented rank 5,270 at both primes, so the target leaves the modular span. A modular left dual was extracted with support 5,270 = 5,078 hinge plus 192 orbit rows and failing hinge row 5,890. A 7-prime rational reconstruction probe recovered 3,274 of 5,269 coefficients with only 1 holdout-validated, showing the heights far exceed CRT reach. Field: rounds 1 and 2 give exact Q solutions of finite cut systems; rounds 3 and 4 are F_p. Every file says "finite-field discovery only".

**G-0010, anchored and cut-only modular duals.** The anchored search fixes the G-0005 functional as four orbit rows with weights (22,-55,-77,-230), the gcd 725,760 removed, and solves for coefficients on 5,269 cut rows mod 1,000,003 so the sum annihilates all 9,804 columns; target pairing 110; support 5,267 hinge plus 2 linear rows. The cut-only variant drops the orbit rows, fixes those 5,269 pivot cut rows plus row 7,145 at coefficient 1, and solves the 5,269 x 5,269 minor at 11 primes from 1,000,003 to 1,000,159; every solve replays on all 9,804 columns with integer target pairing 11!. CRT reconstruction from 10 primes under a 200-bit modulus with one holdout prime left only 2 of 5,269 coefficients stable. Field: F_p only. G-0005 plays no logical role in the final theorem; it served as a support-discovery device.

**G-0011, exact rational left dual.** Dixon lifting over Q of the fixed minor gives integers n_i and D with

```
sum_i n_i * (M[i,:]/g_i) + D * (M[7145,:]/4) = 0   on all 9,804 columns
```

with common denominator 12,517 bits, target pairing 39,916,800, and a 202 s solve under a 12 GiB address-space cap. G-0018 corrects the support description: 5,267 hinge rows plus linear rows 7,136 and 7,138 plus failing row 7,145. I replayed the standalone verifier: PASS, 9,804 columns, 16.8 s, certificate SHA fe6768c8. Field: Q and hence R. Scope: the frozen columns and rows only.

**G-0012, independent exact audit.** With no G-0011 imports: 51,667,080 relation entries replayed, 11 prime reductions matching the G-0010 probes across 57,959 coefficient comparisons, 6 hostile mutations rejected, verdict PASS_BOUNDED_EXACT_IDENTITY. Custody at the time showed 10 inputs untracked. The file self-describes as not disjoint lineage.

**G-0014, semantic matrix audit.** A fresh evaluator regenerated all 70,059,384 entries from the pinned certificate with zero mismatches, reproduced the 16,000 raw pairs and 9,804 classes with its own canoniser, validated all 7,135 directions, checked the target row, and passed n=4..7 controls against direct permutation enumeration plus a rejected endpoint-sum mutant, in 1h31m. The stated caveat: the raw serialization order was corrected after the frozen hash exposed a mismatch, so the reconstruction is not blind; same host and lineage, tier T1.

**G-0015, G-0016, G-0017: theorem, referee, bundle.** Normative statement: MAX11 is not in the real span of the 16,000-raw/9,804-class family union the 6,740 beta2-common lifts. The proof composes the ordered-cone normal form, hinge independence, projection, the G-0011 dual, quotient transport, and the common-edge multiset lemma

```
Phi(A+e, B+e) = Phi(A,B) + 2 * 9! * F_2^(11)
```

which maps every beta2 atom to the coincident-endpoint lift of the same base, itself already in the family. Referee G-0016: same-family T1, PASS_BOUNDED_PROOF_LOGIC, lemma-by-lemma table with no counterexample. G-0017: a 37-file bundle specification with a PASS receipt; it recovered the v1 extractor bytes from a Codex patch event matching SHA ccb12f78. I replayed verify_theorem_bundle.py to the scratchpad: PASS_BOUNDED_THEOREM_BUNDLE with 37 tracked-clean files. Ledger standing: C-0009@1 is COMPUTED_BOUNDED with disposition "challenged"; E-0009 is CONSISTENT; EXP-0003 preregisters only the replay, after adaptive discovery; V-0001 is a same-family "holds"; gap G-0007 is open; C-0010 is verifier identity only. Lean formalises only abstract lemmas, per formalization/OBSTRUCTION_STATEMENT_MATCH.md. C-0011 and C-0012 belong to G-0047 and G-0038, outside this range.

**G-0018, pricing oracle and cross probe.** A design for a split-6 trie oracle with 17,908 terminal words and 2,587 prefix plus 8,181 suffix nodes, unimplemented and unbenchmarked. A signed-graph collapse: with five edges per branch the symmetrised atom depends only on W = 1_B - 1_A. The beta2 mapping audit passes on all 6,740 records with three mutants rejected. The cross class-0 probe evaluates the G-0011 functional on one regenerated column: a nonzero 12,580-bit integer, agreeing mod 2^61-1, recorded as dead end D-0001.

**G-0009, lift identities and bounded redundancy.** On an 886-row system of 364 orbit, 511 held-out hinge, and 11 linear rows, the same-component baseline has exact Q-rank 694, and appending the 3,615 cross or 4,916 beta2 columns leaves 694. Standalone sparse duals kill the cross-only family with a 4-orbit-row dual of pairing 5 and the beta2-only family with a 2-row dual of pairing 1/5. The common-edge identity is proved algebraically with an exhaustive n=6 check. Widening to the 183,064-raw independent-chord family was not executed because the preregistered gate demanded new held-out rank. The 511 rows are G-0008's round-2 residual batch, so the "holdout" is adaptive.

### Summary table

| Artifact | What it shows | Field and rows | Boundary |
|---|---|---|---|
| G-0005 | Four-point separator kills the span of balanced two-coloured spanning-tree templates for odd n>=5; n=11 tuple (792,-330,-231,-230), value 2 on MAX_11 | integer identity, 4 evaluation points | tree family only; kills cross family alone |
| G-0006 | 9,804-class quotient; grid rank 192 mod two primes; 192-term seed fails hinge residual | Q on one 192x192 subsystem, else F_p | one seed only |
| G-0007 | MAX9: 739 trees rank 360 vs 361 with target; hybrid 896 family rank 505 contains MAX9; 391-term certificate | Q, upstream kernel | calibration, shared kernel |
| G-0008 | CEGIS rounds; round 4 rank 5,269 vs 5,270 mod 1,000,003 and 1,000,033; modular dual with 192 orbit rows; CRT lift fails | F_p, rounds 1-2 exact Q | discovery only |
| G-0010 | G-0005-anchored modular dual, then cut-only dual at 11 primes, pairing 11!; CRT leaves 2/5,269 stable | F_p | discovery only |
| G-0011 | Exact Dixon lift: 5,269 pivot rows plus row 7,145, denominator 12,517 bits, pairing 39,916,800 | Q hence R, 7,146 rows | frozen 9,804 columns only |
| G-0012 | Independent exact replay, 51,667,080 entries, 11-prime consistency, 6 mutants rejected | Q | same lineage |
| G-0014 | Clean-room regeneration of all 70,059,384 entries, zero mismatches, 1h31m | integer | raw order fixed against frozen hash |
| G-0015/16/17 | Theorem, same-family T1 referee PASS, 37-file bundle receipt PASS | R | no T2, no completeness bridge |
| G-0018 | Oracle design, signed-graph collapse, beta2 mapping PASS, cross class 0 pairing nonzero | Q | oracle never built |
| G-0009 | Cross and beta2 add zero rank on 886 rows; sparse duals pairing 5 and 1/5; common-edge identity | Q on 886 rows | adaptive holdout |

## 3. Audits, dead routes, next steps, and weak points

**Referee objections and their disposition.**

- G-0006 v1 target normalisation off by 11!: fixed in v2, custody binding added in v3. Resolved.
- G-0006 grid rank 192 is modular only: acknowledged, never lifted, and not needed. Open but harmless.
- G-0015 earlier overbreadth claiming the normal form for unequal branch sizes: narrowed to five-edge-per-branch atoms. Resolved.
- G-0011 support described as hinge-only: G-0018 corrected it to include linear ranks 1 and 3. Resolved.
- G-0012 custody with untracked inputs: resolved by commit bc92a01 and confirmed by my G-0017 replay.
- G-0017 lost extractor bytes: recovered from a Codex event log by the same user. Resolved as far as hashes go.
- G-0014 raw order corrected against the frozen hash: disclosed, unresolved as independence.
- No different-family or human T2 review anywhere: unresolved, tracked as gap G-0007, dropped from the queue as off the critical path.
- No completeness bridge from arbitrary two-hidden-layer networks to symmetrised pair atoms: unresolved, route H-0004 only "proposed".

**Sub-routes that died.** Balanced two-coloured spanning trees, and hence the cross family alone, by G-0005. Linear proper-subset lifts, by the G-0007 human proof. Tree-only MAX9 atoms, by exact rank. The 192-term orbit-grid seed, by hinge residual. The G-0008 round 1 and 2 exact candidates, by residual. The same-component family union beta2, by the exact dual. CRT rational reconstruction of the dual, by coefficient height, replaced by Dixon lifting. Reuse of the G-0011 dual for the cross union, recorded as D-0001. The 183,064-raw chord widening, never run.

**Next steps stated at round close.** H-0001, build the split-6 oracle and search for a new dual for the same-component-plus-cross union; obtain T2 review; the TASKS.md "next mathematical expansion" list, including a normal-form or symmetrisation theorem connecting finite atom families to arbitrary real-weight networks. The oracle was never built, and H-0001 was later dropped from the queue.

**Weak or overstated points.**

1. **Everything is ansatz-relative.** All no-go results concern fully S_11-symmetrised degree-five pair-max atoms with loopless edges. Nothing in this range constrains asymmetric networks, other first-layer directions, or real inner weights. The artifacts say so consistently; the risk lies in downstream readers dropping the qualifier.
2. **The G-0009 widening gate is demonstrably blind.** The nonzero G-0018 pairing on cross class 0, combined with the dual annihilating all 9,804 same-component columns, proves that the class-0 cross function lies outside the real span of the same-component family. Yet G-0009 reported zero rank gain for the cross family on its 886 rows. The decision not to enumerate the 183,064-raw chord family therefore rested on an insensitive test. No artifact states this consequence.
3. **Same lineage throughout.** Every PASS, including the G-0016 referee verdict, comes from the same model family on the same host, and the "independent" evaluators were written after reading the same formulas. The ledger tier is T1 everywhere.
4. **Modular versus rational is handled correctly.** Only discovery steps are finite-field; the theorem's arithmetic is exact and I replayed it. Every "target in span" statement in rounds 1 to 3 and in G-0009 is finite-row only and globally meaningless, which the files state.
5. **Custody is hash-based only.** Same user, no signatures. The G-0011 generator hash was captured during the run rather than before launch.
6. **Adaptive selection.** The family, the 7,135 rows, and the dual support were all discovered adaptively; preregistration covers only the replay. That is fine for a no-go, but "preregistered PASS" language should not be read as prospective.
7. **Terminology.** "Orbit" carries two meanings. "Minimally cyclic" is disowned by the G-0005 audit. The "beta2 lifts" add no new functions, so the theorem's union is the same-component span restated.
8. **Redundancy.** G-0009's cross-only dual is a translated and homogeneously rescaled form of the G-0005 functional and adds no information over G-0005.
9. **Environment drift.** The G-0014 evaluator ran on numpy 2.4.2 while every other artifact records numpy 2.5.2.

**Key files.** artifacts/math/G-0015/THEOREM_DRAFT.md, artifacts/math/G-0016/REFEREE_REPORT.md, artifacts/math/G-0011/RESULT.md, artifacts/math/G-0018/DUAL_PRICING_ORACLE.md, artifacts/math/G-0005/TREE_TEMPLATE_SEPARATOR.md, artifacts/math/G-0009/REPORT.md, artifacts/math/G-0017/bundle_spec_v1.json. My replay outputs are in the session scratchpad as g0011_verify.json and g0017_bundle.json.
