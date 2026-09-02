# MAX11 campaign — complete resume synthesis (2026-09-02)

Author: AmberBluff (Claude Fable 5.1, Agent Mail identity `AmberBluff`, session started 2026-09-02 ~00:50 UTC).
Mode: `resume` under `frontier-research-with-epistemic-humility`, P0 orientation + audit. **No ledger edits were made.** Everything below is self-contained: a successor who reads only this file and the folder `handoff/2026-09-02-amberbluff/` can continue without re-deriving anything.

Supporting material (all in `handoff/2026-09-02-amberbluff/`, hash-bound in `MANIFEST.sha256`):
- `reports/` — nine independent audit reports (cluster1–6, lit-scout, lower-bound, wang-basu), the Opus red-team review of my draft ranking (`red-team.md`), and a fresh-context Fable synthesis (`fable-synthesis.md`).
- `probes/` — my independent probe code (`cert_stats.py`, `count_simple_pairs.py`, `loopless_probe.py`, `loopless_probe_par.py`) and logs (`probe9p.log`, `probe9_p2.log`, `probe10p.log`).
- `systems/` — gzipped n=9 and n=10 loop-free systems (JSONL, one line per template: A, B, linear part, retained-hinge dict). Not committed (gitignored, ~1.2 GB uncompressed).
- `receipts/` — my re-runs of the campaign's G-0011 dual verifier, G-0017 bundle verifier, and G-0110 escape verifier.
- `wang-basu-tools/` — the Wang–Basu reader's parsers/verifiers/Burnside counters.
- `bakaev-yehudayoff-2607.03815.txt` — text of the simplex-symmetry paper the campaign's G-0063/65/66 depend on (not in the certified corpus).

---

## 0. How to resume (do this first)

1. `source scripts/activate-toolchain.sh && ./skill-runtime verify-quick` — expect exactly one finding: SE-10 on `ledger/gaps.toml` G-0015 (obligation text was rewritten in place in commit `7cf9d50`; append-only violation). Fix = append a new gap record with the updated obligation and mark G-0015 superseded; never edit history.
2. Do not trust `STATUS.md` (dated 2026-08-30, says 48 claims/round R-0002; ledger has 53 claims and work ran to 2026-09-01 13:50). Only 2 rounds were ever closed for 364 commits.
3. Register with Agent Mail (`macro_start_session`, human_key `/data/projects/relu-depth-frontier-research`). Prior agents were all GPT-5/Codex lineage; a Claude-lineage agent is a *different family* under the charter's own rule and can supply T2 review once the human authorizes it in `RESEARCH_CHARTER.md` §Minimum review bar (currently "Cross-family transport bound: NONE").
4. Read §7 (ranked paths) and §9 (immediate next actions). The decisive open experiment is a target-aware solve on the complete loopless degree-5 universe (gap G-0014). Nothing else in the campaign is on the critical path.

---

## 1. The exact object

Target (charter): for every n ≥ 1 there exist finite widths and real weights with `max_i x_i = a^T ReLU(W2 ReLU(W1 x + b1) + b2) + c` on all of R^n. First rung: n = 11. Known: n ≤ 10 (Rueß et al., arXiv:2607.21651, Theorem 1.1). For 3 ≤ n ≤ 10 the minimum is exactly two hidden layers (Mukherjee–Basu lower bound for one layer).

Biases are removable for positively homogeneous targets (HBDSS Prop 2.3; Safran Prop A.4). Equivalent polytope form (HBDSS Thm 5.2; Bakaev et al. Lemma 8; AHM Cor 9): MAX_11 ∈ ReLU_2 iff Δ_10 + A = B with A, B ∈ P^2, where P^0 = points, P^1 = zonotopes (arbitrary real generators and translations), P^2 = finite Minkowski sums of conv(Z ∪ Z') with Z, Z' ∈ P^1. Per second-layer neuron: ReLU(h_P − h_Q) = h_conv(P∪Q) − h_Q with P, Q the zonotopes of its positive/negative first-layer weights (campaign G-0084 Lemma 1, G-0110). The Rueß ansatz is the sub-case where every generator is a simplex edge e_i − e_j (or a point/loop), each branch has k = ⌊(n−1)/2⌋ of them, and the sum is S_n-symmetrized; k ≥ ⌊(n−1)/2⌋ is forced by Koutschan et al. Cor 5.2 (a k-simplex is not a signed Minkowski combination of lower-dimensional polytopes). For n = 11, k = 5.

**Asymmetry that governs everything:** a rational certificate in any finite family is a real network (positive settles the rung). A negative on any finite family, including the complete loop-inclusive k=5 universe, proves nothing about MAX_11 ∈ ReLU_2; both construction papers say so, and the campaign proved it concretely (G-0084 Theorem 5: the degree-6 pairwise space is not inside the degree-5 space even with symmetry; G-0110: a single non-braid segment atom is outside the 26,689-column catalogue span — I re-ran that verifier, verdict CONSISTENT). Refutation would be a new theorem.

## 2. Literature state (verified 2026-09-02)

Certified corpus: `literature/INDEX.md` REF-0001..0015. Lit scout (46 logged queries; arXiv API and Semantic Scholar returned HTTP 429, so arXiv coverage rests on the search UI and author homepages) found **nothing from June–September 2026 that settles n = 11 or gives any real-weight depth lower bound beyond one hidden layer.** Frontier movement in the window: Rueß et al. (22 Jul), Wang–Basu (25 Aug), Safran L2 hierarchy (24 Aug, not about MAX_n), Brandenburg–Grillo–Hertrich v2 (4 Jun).

Key facts per paper (locators in `reports/lit-scout.md`, `reports/lower-bound.md`, `reports/wang-basu.md`):
- Rueß et al.: ansatz §4.1; k_min via Cor 4.3; no mention of n=11, no conjecture, no completeness theorem; recursion Thm 5.1 gives ⌈log_5(n/2)⌉+1 layers. Certificates n=5..10 at github kilianar/max-relu-certificates (pinned in `literature/repos/`).
- Wang–Basu: same atom family (first layer entirely braid, no biases); could not solve n=9 (51,984×210,540) or n=10 (112,837×216,428) exactly; their per-η-pair zeroing is strictly tighter than Rueß's per-ray aggregation (they needed k=4 at n=8; Rueß k=3). Do not adopt their formulation. Their Theorem 3.3 (MAX6, 9 orbits) appears false as printed and repairable by one pattern change P69=[11,22|34,34] — agent-derived, **not verified by me**. The campaign's 657,833 rows × 12,179,657 columns is exactly the Rueß formulation with Remark 4.1 reductions; both counts were reproduced by me (Burnside) and by the Wang–Basu reader independently.
- Bakaev–Brunck–Hertrich–Stade–Yehudayoff (STOC'26): MAX5 in two layers via nine terms, one of which uses the non-braid first-layer neuron 2x_5 − x_1 − x_2; P^k framework; "it could be the case that two hidden layers suffice for all n"; full-additivity Lemma 9 and subdivision Lemma 10.
- Grillo–Hertrich–Loho (NeurIPS'25): braid-conforming two-layer nets compute exactly span{σ_M : |M| ≤ 4} (Thm 5.2), Ω(log log d) for conforming nets; the n ≤ 10 certificates violate conformality in the second layer, so this is not target-specific.
- Averkov–Hojny–Merkert (ICLR'25) Theorem 2 (verified against text): N-ary weights, p ∤ N ⇒ ≥ ⌈log_p(n+1)⌉ hidden layers for max{0,x_1..x_n}. Consequence: any rational two-layer MAX_11 certificate has 6 | denominators (2 forced from MAX_5 on, 3 from MAX_10 on; 5 only from MAX_26). Cannot be refined p-adically (C(9,3) ≡ 3 mod 9).
- Safran (COLT'26): depth-2 width ≥ (1/8 − 1/(4d) − 1/(2d²))d² → ≥ 12 first-layer neurons at d=11; the lower-bound reader derived (unverified by me) a sharper necessary condition: ≥ 25 first-layer neurons whose supports of size 2–3 form a 3-cover of all 165 triples.
- Bakaev–Yehudayoff arXiv:2607.03815 (Jul 2026, **not in corpus**): ρ_Δ(P) ≤ 2^d − 1 for depth-complexity-d polytopes (Thm 7); Thm 9/10 sub-additivity rules. Basis of campaign G-0063/65/66.
- Also missing from corpus: 2507.07779 (Bakaev–Brunck–Yehudayoff, approximation depth; log2 bound holds only in the unsigned model), 2410.04907 (decomposition polyhedra), 2509.21286 (maxout polytopes).

## 3. Facts I verified myself this session

Certificate structure (`probes/cert_stats.py` on the pinned upstream JSON):

| n | k | terms | loop-free | both sides forests | full-dim atoms | denominator primes |
|---|---|---|---|---|---|---|
| 5 | 2 | 3 | no (2/3 have loops) | 2/3 | 2 | 2,3,5 |
| 6 | 2 | 4 | yes | 3/4 | 3 | 2,3,5 |
| 7 | 3 | 57 | no (52/57 have loops) | all | 23 | 2,3,5,7 |
| 8 | 3 | 69 | no (44/69) | 66/69 | 25 | 2,3,5,7 |
| 9 | 4 | 337 | **yes** | all, dim (4,4) | 246 | 2,3,5,7 |
| 10 | 4 | 402 | **yes** | all, dim (4,4) | 252 | 2,3,5,7 (lcm 304,819,200) |

Template counts (`probes/count_simple_pairs.py`, Burnside; loop-inclusive column reproduces the campaign's import audit exactly):

| n | k | loop-inclusive multiset templates | loop-free simple-graph-pair templates |
|---|---|---|---|
| 9 | 4 | 210,540 | 10,976 |
| 10 | 4 | 216,428 | 12,248 |
| 11 | 5 | 12,179,657 | 462,627 |
| 12 | 5 | — | 490,480 (Fable's Burnside, unverified by me) |

Loop-free span probe (`probes/loopless_probe_par.py`; independent subset-DP column code validated against brute force and against the upstream n=6 certificate as a known-answer control: linear part e_6, all hinges cancel):

| n | columns | retained hinge rows | rank(A) | rank([A|b]) | member | primes checked | nullity |
|---|---|---|---|---|---|---|---|
| 5 | 19 | 5 | 8 | 8 | yes | 1000003, 1000033, 999983 | 11 |
| 6 | 25 | 15 | 13 | 13 | yes | same three | 12 |
| 7 | 357 | 200 | 90 | 90 | yes | same three | 267 |
| 8 | 430 | 545 | 140 | 140 | yes | same three | 290 |
| 9 | 10,976 | 6,326 | 1,506 | 1,506 | yes | 1000003, 1000033 | 9,470 |
| 10 | 12,248 | 16,709 | 2,166 | 2,166 | yes | 1000003 | 10,082 |

(n=9 and n=10 are planted positives: the upstream certificates live in this family, so the pipeline is trustworthy. n=9 nnz 10.5M, avg 956/col; n=10 nnz 33.2M, avg 2,709/col; n=10 rank of the 16,719×12,249 dense flint matrix took 200 s.) Rank jumps ×6.9 (6→7) and ×10.8 (8→9) at new-k arities, ×1.4–1.6 within a k. Rank/retained-rows: 43%, 25%, 24%, 13% for n=7..10. **Extrapolation for n=11 (loop-free): rank ≈ 25k–40k; red-team ceiling 160k; measure before sizing any sketch.** One n=11 column: 1.6–6.1 s in Python, 2.5k–28k retained hinges; whole family ≈ 5e9 nonzeros. Loop-free atoms never see the minimum coordinate, so their retained hinge rows all have d_0 = 0 (campaign G-0179 observation, consistent with my retained-row fractions).

Other re-runs: G-0011 exact rational left dual verifier PASS (9,804 columns); G-0017 bundle verifier PASS (37 files); G-0110 escape certificate CONSISTENT (receipts in `receipts/`).

## 4. What the prior campaign established (audited; details in `reports/cluster*.md`)

Quotients to keep distinct: 12,179,657 raw Rueß templates ⊃ 7,015,841 loop-inclusive signed-W function orbits (+carriers 5E, 5L) ⊃ 754,017 loopless signed-W orbits (G-0027; mass-5 stratum 735,732; β=0 trees 12,459) ⊃ 462,627 simple-pair templates (61% of loopless orbits; multi-edge classes unreachable) ⊃ 163,740 MAX10-lift classes (21.7% of loopless; the CEGIS family) ⊃ 26,689 (8,107 Y-spoke + 18,582 closure) ⊃ 9,804 same-component lifts.

Exact-rational negatives (all bounded to their family; standing COMPUTED_BOUNDED, T1 only):
- C-0009: MAX11 ∉ span of the 9,804-class same-component MAX10 lifts (+6,740 β2 lifts, which add no functions). Dixon-lifted 12,517-bit dual; I replayed.
- C-0013: signed mass ≤ 3 exact-Q obstruction on the complete 10,065-row D3 system (rank 488 proper + 3 seeds).
- C-0033 / G-0078: MAX11 ∉ span of 8,104 Y-spoke atoms + 3 carriers (230-row rational functional; note Y-spoke walls are non-braid, so this family is outside the Rueß ansatz).
- C-0041 / G-0081: one prime only, 26,689 columns, rank 8,868 vs 8,869. No second prime, no rational dual, no review of the executed runner (gap G-0013).
- 163,740-column MAX10-lift family (G-0116..G-0176): twelve exact-Q finite members on 301..924 sampled rows, each refuted globally (nonzero hinge directions never below 147k); the family itself never decided; 540-row matrix has exact rank 349; the last three members were uncertified /tmp runs. Structurally a treadmill: each iteration refuted one basic solution of a ~163k-dimensional affine space.
- Mass-4 program: 1,465 full-support mass-4 seeds + exact low-mass core excluded over Q (rank 1,288, nullity 70); 821 of 132,728 proper mass-4 columns excluded mod two primes only; gap G-0008 open.
- STAR loop quarantine (G-0179..G-0194): 478-dim kernel of the d_0=1 restriction; 20 (then 35) directions classified in O; 8 nonzero face-confined mass-4 directions undecided (if any is not in O, loop atoms add a genuinely new d_0-free function — never flagged by the authors); 435 mass-5 directions untouched; G-0194 outcome exists only as JSON, no ledger claim.

Structural results over R (exact scope):
- C-0011 / G-0047: Λ = 11th finite difference on the binary profile annihilates every proper-support symmetrized atom; any certificate in the symmetric pairwise ansatz needs a full-support signed core. Lean checks only the coefficient-space step.
- G-0063/65/66 (Bakaev–Yehudayoff ρ_Δ ≤ 3 for P^2): any Δ_10 + A = B forces 1/3 ≤ ρ_Δ(A) < 3 and λ_Δ(A) ≥ 21/8; single-zonotope stabilizers need λ ≥ 55/14 with the equality case excluded; no known certificate has a zonotope stabilizer. Walls, not obstructions.
- G-0083: any two-layer representation of a full-dimensional non-zero-summand d-polytope has first-layer hinge-direction span ≥ d−1 (nearly vacuous at d=10).
- G-0084: symmetrization of an arbitrary representation gives orbit averages of [conv(P∪Q)]−[Q] with arbitrary real generators (Theorem 2); explicit G ∈ V_{11,6} \ (V_{11,5}+Aff) (Theorem 5). Missing bridges named GNF and DR5-MAX; DR5-MAX is nearly a restatement of the conclusion.
- G-0110: catalogue incompleteness for single-segment symmetric S2 atoms (verified by me).
- G-0060: any invariant depending only on {0,1}^n values cannot obstruct (subset-zeta network matches MAX_n on the cube).
- G-0064/85/86: facet gluing is always solvable; the constructive route is stuck at off-facet wall cancellation (gap G-0012); RANGE11 kills the projected-face-shape criterion (D-0004).
- Dead: leaf induction (D-0005/6), transfer laws (G-0114/0115 withheld tests fail), tree-only families (G-0005 separator theorem), J_2 subdivision program (uninformative, G-0082), primitive-only T_{3,2} dictionaries (G-0083).

Process state: ~60% of 364 commits are custody/audit ceremony (cluster5 estimates 80–85% in its range); 6 reviews, all T1 same-lineage; STATUS/QUEUE stale; artifacts G-0087..G-0097, G-0100, G-0105, G-0108, G-0110..G-0112, G-0109 docs and `artifacts/cleanroom/G-0108-exact` are **untracked in git**; route H-0002 still "active" though its falsifier fired; C-0011 still ASSERTED despite a clean-room audit.

## 5. Reconciled probabilities (mine, after red-team and Fable)

- P(MAX_11 ∈ ReLU_2): 0.70 (range 0.6–0.8). For: six consecutive successes at k = k_min; experts say constant depth is plausible; no obstruction mechanism exists even in principle for real weights. Against: each new k is a new regime; nobody could run n=11.
- P(MAX_11 ∈ complete loopless k=5 signed-W span + carriers): 0.50. Loop-free simple-pair subfamily: 0.45. Loop-inclusive k=5: 0.55. Some degree-6 or real-generator enlargement given all k=5 negative: ~0.3 conditional.
- P(unconditional refutation proved in this campaign): ≤ 0.03.

### 5a. Probability that THIS campaign settles the rung (decomposition — do not confuse with P(true))

| Quantity | Estimate |
|---|---|
| MAX_11 is representable at all (fact about the world) | 0.70 |
| A certificate exists in the loopless k=5 family we can actually solve (unconditional) | 0.50 |
| We complete the two-prime decision on that family in ~3 weeks | 0.60 here, 0.75 with a rented 256–512 GB node |
| Exact rational lift + full-row verification succeed, given a mod-p member | 0.85 |
| **We produce a verified MAX_11 witness via path 1 in ~3 weeks** | **≈ 0.25 (≈ 0.32 with node)** |
| Added by enlargement paths (loops, non-braid generators, degree 6) over ~3 months | ≈ +0.06 |
| We prove impossibility instead | ≤ 0.03 |
| **We settle n = 11 either way within ~3 months** | **≈ 0.30–0.40 (0.40–0.45 with node + enlargement funded)** |
| We settle the all-n question | ≈ 0.05–0.10 |

Only a positive result can come from computation. If MAX_11 is representable but not by any family we can afford to solve, the honest terminal is a bounded null (report Shape 2), not a solution.

## 6. Corrections forced by the red-team (all accepted)

1. The loopless universe *was* enumerated (G-0027) and priced once (G-0028, Rust, 627.8 records/s); what is missing is the target-aware solve (gap G-0014). Run it on the 754,017-class universe, not only on my 462,627 simple pairs.
2. 163,740/754,017 = 21.7% (I had propagated an agent's "2.2%" without checking).
3. My first rank extrapolation reported only the favourable scaling; state the range and measure at n=10 first (now done: rank 2,166).
4. n=9 was one-prime in the draft (now two primes); n=10 one prime; no rational witness has been produced at any n by my pipeline. "No real-weight lower bound" must say "no *depth* lower bound" (Safran gives width bounds; GHL gives fan-conditional depth bounds).
5. Loops are used in the n=5,7,8 certificates; the correct statement is "the loop-free span still contains MAX_n at every n ≤ 10".
6. Resource model for the decisive solve must be stated: streaming echelon reduction against a rank-sized basis (~28 GB working set at rank 35k over ~100k sketched rows; ~13 h on 16 cores at the axpy rate measured on the n=10 probe), not a dense 100k×462k matrix (370 GB).
7. The β=0 (spanning-tree) stratum alone is *not* a valid first experiment: G-0005 proves balanced two-coloured trees cannot span MAX_n for odd n, and G-0007 confirmed at n=9 (rank 360 vs 361). Red-team's suggestion there is rejected.

## 7. Ranked paths (mechanism · cost · kill condition · probability)

1. **Decide MAX_11 membership in the complete loopless k=5 universe (754,017 signed-W orbits + 5E, 5L), exactly.** Mechanism: compile the column kernel (Rust/C++ subset-DP over back-degree words; validate column-for-column against `systems/loopless_system_n9.jsonl.gz` and n10); stream columns through two independent sparse random row sketches of size m ≈ 2–3× the measured rank (start m = 96k; saturation check rank < m at both sketches and two primes); blocked modular elimination (FFPACK-style GEMM against a dense echelon basis, ~10–30 GB); if rank([SA|Sb]) = rank(SA) at two primes, solve the r×r pivot system and Dixon-lift, then verify the integer-cleared certificate on all 657,822 rows exactly; if not, lift a left-kernel vector to a rational separator (as G-0011 did). Cost: ~1 week engineering, 1–2 days compute here; rent a 256–512 GB node if rank > ~60k. Kill: sketch saturates at m = 128k, or compiled column cost > 2 s. P(decisive two-prime answer within 3 weeks) 0.6 here / 0.75 with a node; P(positive) ≈ 0.5; a positive settles the rung and gives n = 12 (k=5, ~490k templates) nearly free.
2. **Calibration prerequisites (days).** Exact-Q witness recovery for n=9,10 from my saved systems (tests the Dixon/verification leg); compiled-kernel benchmark; n=10 sketch-vs-full-rank agreement test; confirm d_0=0 row universe size at n=11. P(complete) 0.9; settles nothing.
3. **Residual-guided enlargement if path 1 is negative.** Price the loop-inclusive 7,015,841-record universe with the exact separator using the existing G-0040 pricer (20–60 min per dual); then non-braid generators 2e_k − e_i − e_j and e_i + e_j − e_k − e_l (Bakaev's max5 needs the former; G-0110 shows they add functions); then degree 6 (loop-free templates ≈ 18.4M by Fable's count, unverified). P(positive | loopless negative): ~0.15 loops, ~0.3 enlarged classes; degree 6 needs a large node.
4. **Span structure across n = 5..10 (cheap, parallel, only route to all-n).** Compute exact left kernels of my saved systems; test whether the 7:1 column redundancy is generated by local moves on signed graphs (red-team B); test the Fable vertex-collapse candidate lemma ("every loop-free n=11 column is the sum over the 11 labels v of the loop-inclusive n=10 column obtained by placing v at the minimum", **unverified**); exact rank of that image inside the n=10 loop-inclusive span. P(settles n=11 alone) 0.05.
5. **Refute track, protected ≤ 15% budget.** DR5-MAX target-fibre degree reduction; Minkowski-linear invariants on virtual identities (polytope algebra / mixed-volume multilinear profile — speculative); Safran-type first-layer 3-cover condition as a hard constraint on any witness search. P(settles) ≤ 0.03; yield = walls.
6. **Process repair before any promotion.** Append a superseding gap for G-0015 (SE-10); close a round R-0003 recording this audit; reconcile STATUS/QUEUE to real IDs; commit the untracked artifact directories; admit the four missing papers via `literature/CERTIFICATION.md`; mark H-0002 killed with `killed_by` G-0114/G-0115; ledger the G-0194 outcome; bind the T2 transport (human authorization of Claude lineage as a different family); replace per-run custody audits with a light standard for exploratory compute and full custody only for promoted claims.

Deprioritized with reasons: CEGIS on MAX10 lifts with sub-thousand rows (information-free at this rank); coefficient laws/lifts (refuted exactly); naive completeness theorem GNF (false by G-0084/G-0110); β=0 tree-only families (dead by G-0005).

## 8. Candidate lemmas and unverified items (to check before use)

- Fable vertex-collapse lemma (path 4). Elementary if true; would make span(loop-free, n=11) the image of a linear map from the n=10 loop-inclusive family.
- Fable's Burnside counts for n=12 (490,480) and degree-6 n=11 (18,436,223).
- Lower-bound reader's 25-neuron 3-cover condition from Safran Prop A.4 and §2.4.
- Wang–Basu Theorem 3.3 erratum and the injection orbit-sum convention.
- G-0188 deletion lemma ("template identity at n=K persists for all n ≥ K"), frozen, never verified.
- The 8 undecided face-confined mass-4 STAR directions.

## 8a. Effort plan in execution order, with decision gates

1. **Compile the column kernel and calibrate (2–3 days).** Port `probes/loopless_probe_par.py::column_dp` to Rust; validate column-for-column against `systems/loopless_system_n9.jsonl.gz` and `..._n10.jsonl.gz`; recover exact rational witnesses for n=9 and n=10 from those systems (tests the Dixon/verification leg on known answers); measure the streaming-elimination rate. Every later number becomes a measurement.
   - *Gate:* if the measured/extrapolated n=11 rank exceeds ~60k, request the rented node (human approval required by charter) before step 2.
2. **Decide the complete loopless k=5 universe (1–2 weeks after step 1).** 754,017 signed-W classes + carriers 5E/5L; rows = all d_0=0 primitive ambiguous directions + 11 linear; two primes; sketch sized at 2–3× measured rank with saturation check; Dixon lift + full-row exact verification if member; rational separator if not. Preregister as EXP-0036 first (see §9.3).
   - *Gate:* member → exact lift → external (T2/human) referee → promotion. Non-member → step 5 with the separator in hand.
3. **Span structure at n = 5..10 (parallel with step 2; days).** Exact left kernels of the saved systems; test whether the 7:1 column redundancy is generated by local moves on signed graphs; test the vertex-collapse lemma; rank of the collapse image inside the n=10 loop-inclusive span. Option value: shrinks the n=11 solve and is the only route to an all-n theorem.
4. **Process repair + T2 unlock (1–2 days, before any promotion).** SE-10 fix, close R-0003, reconcile STATUS/QUEUE, commit untracked artifacts, admit missing papers, kill H-0002 with `killed_by`, ledger G-0194, record human authorization of Claude lineage as a different family in the charter.
5. **Residual-guided enlargement (only if step 2 negative; weeks; needs node).** Loop-inclusive universe priced with the exact separator (G-0040 pricer), then non-braid generators 2e_k−e_i−e_j and e_i+e_j−e_k−e_l, then degree 6.
6. **Refute track at 10–15% continuous.** DR5-MAX, Minkowski-linear invariants, first-layer 3-cover constraint. Yield = walls; never single-track advocacy.

Recommended start: steps 4 and 1 in parallel on day one.

## 9. Immediate next actions when work resumes

1. Charter amendment (human): authorize Claude lineage as T2-eligible; record budget extension for the solve; approve or decline a rented node.
2. Process repair (path 6), then `./skill-runtime verify-quick` green, close R-0003.
3. Preregister the loopless-universe solve as EXP-0036 (family `max11-loopless-k5-complete-target-aware-solve-v1`), declaring: subject = G-0027 universe + 5E/5L; rows = all d_0=0 primitive ambiguous directions + 11 linear rows; two primes 1,000,003 and 1,000,033; sketch parameters; known-answer gates = n=9 and n=10 loop-free systems (member) and n=9 β=0 trees (non-member, G-0007); plant/null/reconciliation controls per `domains/mathematics.md`.
4. Engineering: port `column_dp` to Rust; validate against `systems/`; run n=11.
5. In parallel: path 4 kernel structure at n=7..10; path 5 at low budget.

## 10. Glossary

atom / template = (A,B) pair of k-edge multisets, Φ_{A,B} = max(Σ_A m_ij, Σ_B m_ij); loop = diagonal pair (i,i) = bare coordinate; signed-W = B'−A' after cancelling common edges (function-level class); signed mass = |A'| = |B'|; carriers 5E/5L = five common non-loop / loop edges; sorted cone C = {x_1 ≤ … ≤ x_11}; retained hinge = primitive zero-sum direction whose proper prefix sums take both signs, oriented first-nonzero-positive; d_0 = first coordinate of the hinge (loop count at the minimum vertex); Λ = 11th alternating finite difference; O = span of the 163,740 MAX10-lift classes + carriers; STAR = one-edge-per-branch lifts sharing the new apex; P^k = depth-k polytope class; GNF/DR5-MAX = the unproved bridges from arbitrary networks to the degree-5 pairwise dictionary.

---

## 11. Prior updates as verified results land (append-only, dated)

**2026-09-02 ~14:30 UTC (swarm day 1, three results verified by AmberBluff re-execution):**
- Column generation is exact and fast enough: the Rust generator (`tools/colgen`) reproduces all 10,976 n=9 and 12,248 n=10 saved columns coefficient-for-coefficient and the frozen G-0028 price vectors at both primes. Measured n=11 cost: 0.28 CPU-s per column, median 29k retained hinges, ~31.7k nonzeros per column, so the 754,017-column universe holds ~2.4e10 nonzeros (5x my earlier 5e9) and one full pass is ~10 h at 6 threads. (Bead .1, closed with evidence.)
- The exact-lift leg works on real known answers: exact rational MAX_9 and MAX_10 witnesses recovered from the loop-free systems (supports 415 and 424, verified over Q on every row; n=10 denominator lcm 304,819,200 = 2^10·3^5·5^2·7^2, identical to the upstream certificate's). Dixon solve 11 s at r=2,166. (Bead .2, RESULT pending.)
- Vertex-collapse lemma PROVED (bead .5): F_n(A,B) = sum over labels v of F_{n-1}(collapse_v(A,B)) on the sorted cone. So span(loop-free, n=11) is a subspace of span(loop-inclusive degree-5, n=10), and a MAX_11 loop-free certificate is the same thing as a degree-5 loop-inclusive MAX_10 certificate whose coefficients factor through the collapse map. Local two-term/quadratic moves do NOT generate the column relations (explicit counterexamples at n=7,8), so no cheap algebraic collapse of the universe exists along that route. Burnside counts 490,480 (n=12) and 18,436,223 (degree 6) confirmed.

Revised decomposition (compare §5a): P(MAX_11 in loopless k=5 span) unchanged ≈ 0.45–0.50 (nothing yet bears on n=11 membership itself); P(two-prime decision completes on this box within ~3 weeks) 0.60 → ≈ 0.80 (pipeline risk retired faster than planned; residual risk = n=11 rank above ~60k forcing a rented node, and the ~1-day-per-prime sketched elimination); P(exact lift succeeds | member) 0.85 → 0.90. Net P(verified MAX_11 witness via path 1 within ~3 weeks) ≈ 0.25 → ≈ 0.35.

Plan refinements adopted: (i) a stratified first experiment (bead .7) may give a positive early at 5–10x lower cost; (ii) if the loopless family is NON-MEMBER, the exact rational separator (bead .8) prices the 7,015,841-record loop-inclusive universe in one streaming pass, and only the violated columns join the next rank computation — that is the enlargement strategy, not a fresh 10x solve.
