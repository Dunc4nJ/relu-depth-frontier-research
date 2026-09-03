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

**2026-09-02 ~16:10 UTC (swarm day 1, second batch of verified results):**
- Exact leg proven end-to-end at n=10 (bead .8, closed): random 6,498-bucket sketch -> pivot set -> exact lift -> byte-identical upstream certificate (SHA 4bcb155a...) -> both verifiers; exact rational separators for the n=9 tree family at two primes (739/739 columns annihilated). Honest gap: the dense exact solve does not fit at r >= 35k (projected 90 GiB); bead .10 builds the compact mod-p LU + sparse Dixon + early-termination path.
- Strata (bead .7, closed; decision-relevant claim replayed by AmberBluff with independent code): no natural sub-family carries the full loop-free span at much lower n=11 cost (s=k alone misses exactly one dimension at both n; connected W is NON-MEMBER at n=10), but {s=k, beta<=1} CONTAINS MAX_n at both n=9 (rank 1,152 of 1,506) and n=10 (rank 1,807 of 2,166) and has only 120,946 of 754,017 records at n=11 (6.2x fewer columns). {s=k, beta<=2} (355,166) is also MEMBER at both. EXP-0036 is therefore staged (bead .4, comment 2): stage A = s=5, beta<=1 + carriers; stage B = stage-A basis + all columns violating the stage-A exact separator; only the all-column separator check certifies a family null. Stage-A record list: artifacts/math/stream-rank-engine/stageA-order-s5-beta-le1.json (120,947 indices incl. record 0, SHA 42cbef6f...).
- Gap in the evidence base: every ranked system so far is simple-W (entries in {-1,0,1}); 510,550 of the 754,017 n=11 records are multi-edge and unranked at any n. Bead .9 (NavyTiger) ranks the complete loopless degree-4 universes at n=9,10 to settle whether multi-edge W add span.
- n=11 rank pilot (bead .3, WildWillow; 20k uniformly sampled records in index order, m=96k, two sketches, p=1,000,003): rank 1,921 @3,072; 2,392 @4,096; 3,416 @5,120; 5,020 @7,168; 12,127 @15,360 columns. A saturating model rank(c) = R(1 - e^{-c/R}) fitted at c=15,360 gives R ≈ 30k for the full universe, consistent with the 25k-40k extrapolation; the curve is still rising within the top-mass stratum, so R could be higher. Cost: ~257 s per 1,024-column batch at rank 12k with the current kernel (~2e9 ops/s), i.e. days for the full universe and ~1-2 days for stage A unless the reduction kernel reaches FFLAS-class throughput (steer sent). Memory: ~7 GB at rank 12k with two sketches; ~19 GB at rank 25k; the box has ~14-20 GB free with other sessions running, so sketches may have to run one at a time.

Priors: unchanged on membership (≈0.45-0.50 loopless). Schedule: stage A is now the near-term shot at a positive; P(stage-A verdict within ~1 week on this box) ≈ 0.7; the remaining engineering risk is the reduction kernel and the r≈25-35k exact lift.

**2026-09-02 ~16:30 UTC (20k pilot complete; rank prior revised UP):**
- Pilot (bead .3): 20,000 uniformly sampled G-0027 records in index order, m=96k, two sketches, p=1,000,003: rank 16,767 / augmented 16,768 (NON-MEMBER on the sample, expected), 3,787 s wall, 14.7 GB peak, reducer ~1,150 s per sketch. Pivot fraction by stratum: every record from s<=4 and from s=5 with beta<=2 was a pivot (they arrived first); s=5 with beta=3/4/5 were 76%/56%/50% pivots against the 16.8k basis. Because the order is by index, this curve cannot be extrapolated to the full rank; the saturating-model estimate R≈30k from the partial curve is withdrawn.
- Bead .9 (NavyTiger, n=9, both primes): cumulative rank over max multiplicity 1/2/3/4 = 1,506 / 2,148 / 2,232 / 2,232 over 6,197 / 14,920 / 16,185 / 16,311 W-orbits. Multi-edge W add 48% more dimensions at n=9; all ranked systems before today were simple-W only.
- Revised working estimate: full loop-free k=5 universe rank R ≈ 50k-80k (range 40k-160k). Consequences: (i) the full-universe run needs a rented node (dense basis 20-40 GB per sketch at m=128k; elimination ~R·m·N ≈ 8e15 ops, ~2 days per (sketch, prime) at 5e10 ops/s); (ii) stage A (120,947 columns, s=5, beta<=1 + carriers) may fit here if its rank stays under ~45k (basis 17 GB per sketch, one sketch at a time); the stage-A run itself is the measurement, with an abort gate at rank 45k / RSS 20 GB. Human approval for a node is required by the charter; the gate is the trigger.
- Priors: membership unchanged. P(decision on the complete loopless family within ~3 weeks on this box alone) drops from ≈0.8 to ≈0.3; with a node ≈0.7. P(stage-A verdict here within ~1 week) ≈ 0.6.
- **~16:50 UTC, exact-leg risk retired (bead .10, closed, re-executed):** `tools/exactlift lift-large` (Rust dense mod-p block LU + sparse Dixon + early-termination reconstruction + CRT fallback) solves a dense synthetic r=20,000 system with 599M nonzeros exactly in 591 s at 4.0 GB, reproduces the n=10 certificate byte-for-byte, and projects r=35k at ~45 min / 13 GiB and r=60k at ~3.5 h / 28 GiB. The exact lift is no longer a schedule risk up to r≈60k on this box. Bead .11 (AzureAspen) builds exact all-column separator pricing for the stage-B selection and family-null certification.

**2026-09-02 ~18:30 UTC (deep pass; plan refinements):**
- Stage A (s=5, beta<=1, 120,948 columns) rank plateaued near 8.3k by 50k columns (one 64k sketch, p=1,000,003, host). Because the 20k index-order pilot already found 16.8k independent columns, stage A carries at most ~55% of the full loop-free span (at n=10 the analogous family carried 83% and contained the target), so the n<=10 precedent transfers weakly: P(stage A MEMBER) ≈ 0.3 (was ≈ 0.5). The decision is the full-universe run on the rented H100 (bead .12, CUDA reducer); stage A is the cheap early ticket.
- Positive-branch gap closed in advance: the pinned upstream verifier enumerates 11! permutations per term and is infeasible at n=11 in Python; bead .14 (fourth agent, pane %77) ports its semantics to Rust with a subset DP and validates on all n=5..10 certificates, so any MEMBER verdict can be checked by independent semantics within hours.
- Soundness of the sketched decision, restated: a sketch cannot produce a false NON-MEMBER (Sb is in colspan(SA) whenever b is in colspan(A)); a false MEMBER has probability ~1/p per sketch and is caught by the exact lift; a rational certificate invisible mod both primes would need denominators divisible by both 1,000,003 and 1,000,033; the exact separator (NON-MEMBER) or the exact certificate (MEMBER) is the unconditional artifact.
- If the whole degree-5 pairwise ansatz is negative (loopless, then loop-inclusive via separator pricing), the next enlargement is mixed generators with one non-braid neuron 2e_k - e_i - e_j per atom (Bakaev's MAX5 uses one; G-0110 shows they add functions), before degree 6. Not started; wait for the degree-5 verdicts.
- Compute: H100 (49669562) and A100 (49669563) Vast boxes provisioned; charter authorization recorded.

**2026-09-02 19:35 UTC — EXP-0036 STAGE A, first arm: MEMBER (mod p, one sketch).** H100 CUDA replica, 120,948 columns (s=5, beta<=1, + 5E record 0, + 5L), m=64,000, seed 2026090201, p=1,000,003: rank 21,222 = augmented rank, unsaturated, 1,728 s (pivot SHA 2ac8d122...). The host CPU run is on the identical rank curve at every matched checkpoint. Pending before it is a verdict: second sketch, second prime, CPU/GPU pivot agreement, and the exact rational lift on the A100 (r = 21,222, lift-large) with all-row verification and the independent-semantics verifier (bead .14, IndigoCarp, already validated on n=5..10, ~6 min per 5,000 terms). If the exact lift passes, MAX_11 is representable by a two-hidden-layer ReLU network and the n=11 rung is settled positively, subject to T2 review. P(exact lift passes | this mod-p MEMBER) ≈ 0.9 (false MEMBER probability ~1/p per sketch; the exact leg is the proof).
- **20:55 UTC — stage A modular verdict complete: MEMBER on all four arms.** p=1,000,033 with both seeds: rank 21,222 = augmented, unsaturated, identical pivot list to the p=1,000,003 arms and to the host CPU replica (JSONs in artifacts/math/n11-stageA/). Exact lift running on the A100 on two paths. Full-universe pass 1 (754,018 columns, m=128k, p=1,000,003, seed 1) launched on the H100 at 20:42 UTC (bead .12). n=12 universe census done (bead .15): 787,523 loopless degree-5 signed-W records, n=11 replay identical to G-0027, n=12 stage-A family 148,629 columns.

---

## 12. Live operational state (for a successor after compaction; supersedes §0 items 1-4 while the swarm runs)

**Result status (2026-09-02 22:40 UTC):** MAX_11 ∈ span(stage-A family) is established MODULO p on all four preregistered arms (two sketches × primes 1,000,003 / 1,000,033; rank 21,222 = augmented; identical pivot lists; CPU and CUDA engines agree byte-for-byte; JSONs in `artifacts/math/n11-stageA/`). Stage A = G-0027 records with signed_mass=5, abs_beta<=1, plus record 0 (5E) and the 5L linear carrier: 120,948 columns. **No exact certificate yet.** The greedy pivot solution is dense (support 15,895/21,222) with astronomical height (>1,024 bits), so it is a generic point of the 99,726-dimensional solution space, not a sparse witness. Bead .4 comments 1-9 hold the preregistration and every arm/trial; amendment 3 (comment 9) governs the exact leg now.

**What is running where (Vast.ai, authorized by Duncan, no cap; I create/destroy; `vastai show instances`):**
- H100 PCIe `49669562`, `ssh -p 29562 root@ssh1.vast.ai` (WildWillow, bead .12): full-universe pass 1 (754,018 columns, m=128k, p=1,000,003, seed 1; ~490k/754k at 22:15; JSON under `/workspace/relu/artifacts/math/n11-full-universe/`), and the sparse-witness DESCENT families F1/F2/F3 (order files `artifacts/math/stream-rank-engine/stageA-sub-F*-order.json`, committed; JSONs to `/workspace/relu/artifacts/math/cuda-reducer/`).
- A100 `49669563`, `ssh -p 29562 root@ssh5.vast.ai` (AzureAspen, beads .11/.10 code): exact lift pipeline under `/workspace/relu/artifacts/math/n11-stageA-exact-lift/` (run1 = dead Python RREF, to be killed; run3/4/5/6 = sketched-minor attempts, dense; run7 = insurance dense Dixon, 40k steps, ~4-5 h). Tools: `tools/exactlift/lift_large.py`, `tools/exactlift/lift_large_rs` (binary `max11-lift-large solve-big`), `tools/exactlift/support_lift.py`, `sketch_separator.py`.
- H100 NVL `49685464`, `ssh -p 15464 root@ssh1.vast.ai` (NavyTiger, bead .16 = EXP-0037, n=12 stage A, 148,629 columns, four arms sequential, 60-thread binary cdf835b2...; universe `artifacts/math/n12-universe/`).
- Host: IndigoCarp (pane %77, bead .14, `tools/verify11`, validated on n=5..10; ~6 min per 5,000 terms; being hardened for 100k-digit coefficients). Swarm session `relu-depth-frontier-research--swarm`, panes %74 WildWillow, %75 AzureAspen, %76 NavyTiger, %77 IndigoCarp; dispatch with `ntm --robot-send=<session> --panes=%N --type=codex --msg=...`.

**Decision tree for the exact leg:**
1. Smallest MEMBER family among F1 ⊂ F2, F3 (and stage A itself) → AzureAspen: gather exact pivot columns (tools/colgen emit-universe over the pivot indices) → build the pivot-bucket sketch minor (dimension = that family's rank) → mod-p support diagnostic → Dixon with reconstruction (Hadamard bound ≈ rank × 17 bits; ~0.15-0.4 s per 16-bit digit) → exact check on EVERY real row of the union of supports + 11 linear rows → `to-upstream` JSON.
2. Independent semantics: IndigoCarp runs `tools/verify11` (DP mode) on the upstream JSON plus a literal-permutation spot check on 20 terms. Both must say OK.
3. Then T2 review (charter requirement, Claude lineage differs from all four Codex authors): the referee re-executes, from the committed files only, (a) verify11 on the certificate, (b) the exact all-row check, (c) the translation from our column basis to the upstream template format on 20 random terms by hand-derivation, and (d) recomputes 5 random columns of the certificate by literal S_11 enumeration. Only after that: promote (claim version, evidence class INDEPENDENTLY_REPLAYED → REFEREED), append the ledger records, and report Shape 1.
4. If every family's pivot solution is dense and the insurance Dixon also fails to reconstruct within 40k digits: report honestly as "MEMBER mod two primes, no exact certificate recovered under this protocol", and open the next amendment (sparse-solution search: pivot order trials, L1-guided selection).

**Parallel high-leverage paths (in tandem):** n=12 stage A (EXP-0037) already running; full-universe n=11 rank (structural, gives the complete family's rank); after a sparse certificate exists: analyze its template shapes/denominators against n=9,10 for a uniform lift pattern (the all-n route); T2 review; external reproducibility package (certificate JSON + verify11 + the pinned upstream verifier).

**How to read status in one command each:** panes: `tmux capture-pane -p -t %74 | tail`; boxes: `ssh ... 'tail -1 /workspace/relu/artifacts/math/*/*.log'`; beads: `br list`; mail: fetch_inbox for AmberBluff; git: `git log --oneline -8`.

### §11 addendum, 2026-09-02 23:05 UTC — exact rational solution recovered (not yet independently verified)

- run7 (dense insurance Dixon on the A100, lift binary `max11-lift-large-a50338c3`, prime 65521, 16 threads) reconstructed the full solution at Dixon step 2,000 of 40,000 (32,000-bit modulus). Solver report `artifacts/math/n11-stageA-exact-lift/run7-dense-insurance/stageA_sketch_big_solver_report.json` (SHA `ddf6c29cc53bfac02c99a2e60276601a0de52be90e4aea7db5fee1f4da6fdb9c`): verdict PASS; exact rows verified 190,483/190,483 = 21,222 sketch rows + 11 linear rows + 169,250 union hinge rows; recovered support 15,896/21,222; denominator lcm ≈ 530 bits; +1 mutation control breaks 29,917 rows; total 1,319 s; RSS 15.4 GB. Because MAX_11 equals x_1 on the sorted cone, the target has no hinge rows, so the union of column hinge supports plus the linear rows is the complete row set: this is a full sorted-cone identity check for the 21,222-column pivot system.
- Prior update: the greedy pivot solution is dense but NOT tall; the Hadamard bound (≈360k bits) overestimated the height by two orders of magnitude, as at n=10. P(verify11 + T2 pass on the translated certificate within hours) ≈ 0.85; residual risk is in the universe→upstream translation at this scale and in verify11 scaling (15.9k terms, kilobit coefficients).
- Descent families (WildWillow, H100, one prime/one sketch): F1 forest-pair+full11 NON_MEMBER (10,949 vs 10,950), F3 full11 NON_MEMBER (14,720 vs 14,721), F2 forest-pair MEMBER rank 15,904. Structural reading: a forest-pair certificate exists at n=11 but requires terms with fewer than 11 active vertices; not yet exact.
- Dispatched: AzureAspen finalize + `universe_to_upstream.py` on run7 (then the F2 member pipeline); IndigoCarp verify11 DP + literal spot check + planted negative into `artifacts/math/verify11/n11-run7/`; NavyTiger runs the remaining n=12 arms concurrently. T2 referee (Claude lineage) per §12 once `member_upstream.json` lands.

### §11 addendum, 2026-09-02 23:50 UTC — certificate translated; verification in flight

- run7 finalized (AzureAspen, commits 001c8e8 + e7e596d): `member_exact_lift_report.json` PASS (real rows 169,261/169,261; combined 190,483/190,483; support 15,896/21,222; denominator lcm 215 digits = 2^26·3^13·5^5·7^3·11·19·83·223·652357·C183, C183 composite and unfactored — amendment 4 bounded the report-only factorization). `member_upstream.json` SHA `8bd2270a801f6af679ccbf00aa7357f4e89ebb069d1211671082f3f5f07d25c5`, n = 11, 15,896 terms.
- Verification: T1 = IndigoCarp `max11-verify11 analyze` (DP, 4 threads) running on the host; T2 = Claude-lineage referee (Opus subagent, fresh context) launched 23:47 UTC with a semantics audit, 20 translation spot checks, an independent build and `verify` run, a 20-term literal cross-check, a planted negative, and the method-disjoint lattice falsifier (bead 2t4) when it lands; report to `artifacts/math/t2-review/n11-run7/`.
- Full loopless universe pass 1 (bead .12, closed): rank 41,856 MEMBER over 754,018 columns, one sketch/one prime; pass 2 aborted for the H100 reallocation to n=12 arms 3–4.
- New parallel beads: 2t4 (lattice falsifier), 2q7 (class-sum span test at n = 9, 10), ksi (naive induction test: S_11-lift of the 402 n = 10 terms, WildWillow, H100).

### §11 addendum, 2026-09-03 00:15 UTC — class-sum span test at n = 9, 10 (bead 2q7): negative

- Question: does a certificate exist whose coefficients depend only on a coarse invariant of the signed graph W (a uniform-formula shape)? Method: replace columns by class sums S_c and test b ∈ span{S_c} exactly (MEMBER = exact rational solution on every row; NON_MEMBER = exact rational dual). Data: saved loop-free systems n = 9 (10,976 cols, 6,335 rows) and n = 10 (12,248 cols, 16,719 rows); commit d2c7515.
- Result: every coarsening below ≈4,600 classes is NON_MEMBER at both n, including the 86-class "unordered pair of iso types of the positive and negative graphs" (full column rank 86, target outside the span), vertex-type multisets, degree sequences, and (active vertices, components, cycle ranks). Membership returns only when the isomorphism type of the unsigned union graph A ∪ B is part of the key (C11: 4,605 of 6,197 orbits at n = 9; 5,363 of 7,203 at n = 10). Re-executed by me at n = 9 for C0, C2, C7: identical.
- Reading: the coefficients are a function of how the two branches intertwine, not of the branch shapes; a "few-parameter" uniform formula is dead at n = 9, 10 (P ≈ 0.03 it exists for all n). The all-n route must be recursive or orbit-level (e.g. a Möbius-type rule over union-graph containment), not invariant-based. Live structural tests: bead ksi (naive S_11-lift of the n = 10 certificate) and a sparse legible n = 11 certificate (new bead) for pattern reading against the n = 9/10 upstream certificates.

### §11 addendum, 2026-09-03 00:58 UTC — BOUNDED POSITIVE: MAX_11 is computed by a two-hidden-layer ReLU network (n = 11 rung settled)

- **Object:** exact rational certificate `artifacts/math/n11-stageA-exact-lift/run7-dense-insurance/member_upstream.json` (SHA `8bd2270a801f6af679ccbf00aa7357f4e89ebb069d1211671082f3f5f07d25c5`, n = 11, 15,896 loop-free pairwise-max terms with 5-edge branches, coefficient denominator lcm 215 digits) in the pinned upstream certificate format; a second, forest-pair certificate with 11,320 terms (SHA `767f9e66…`) is in verification.
- **Evidence chain (each file re-read by the orchestrator):** (a) exact rational lift verified on all 190,483 rows of the sorted-cone identity, +1 mutation rejected (lift report SHA `76e8661c…`); (b) T1: `max11-verify11` DP mode (GPT-lineage author/operator) OK, 0 bad rows of 11 linear + 169,166 hinge, 2,765 s (report SHA `5a2091d2…`); 20-term literal enumeration over all 11! permutations matched the DP 20/20; (c) T2 by lineage: Claude (Opus) referee, fresh context, independent build, `verify` mode exit 0, OK, 0 bad rows, 47 min (report SHA `7c7d785d…`), 20/20 translation spot checks; (d) T2 by method: lattice falsifier (independent counting evaluator, bead 2t4) PASS on 179,195 lattice points in {0,1}^11 ∪ {0,1,2}^11, twice; controls re-executed by the orchestrator (upstream 6_2 and 10_4 PASS, 5_2 +1 mutant FAIL).
- **Standing:** COMPUTED_BOUNDED, INDEPENDENTLY_REPLAYED (T2 lineage + disjoint method). Not REFEREED by a human, not FORMALIZED. **No-claim:** the statement is exactly "MAX_11 ∈ ReLU_2 with real weights"; nothing is claimed for n ≥ 12 or for all n; the certificate is dense (not minimal) and its coefficients carry a 183-digit composite denominator cofactor.
- **Pending, not load-bearing:** referee RESULT.md and planted-negative run; IndigoCarp's run7 mutant; T1/T2 on the F2 certificate; upstream authors' verifier deferred to a sparse certificate (38 h projection on the dense one).
- **Companion results tonight:** degree-4 (k = 4) loopless span at n = 11 is NON_MEMBER on two sketches (rank 3,514 vs 3,515; bead kwa, PurpleWolf), so 5-edge branches are necessary at n = 11 within the ansatz, matching k = ⌊(n−1)/2⌋; class-sum test negative at n = 9, 10 (bead 2q7).

### §11 addendum, 2026-09-03 01:25 UTC — degree-4 (k = 4) loop-free span at n = 11: NON_MEMBER (bead kwa)

- Complete loop-free degree-4 signed-W universe at n = 11: 18,285 orbits + 4L (universe SHA `72d0f4b5…`); streamrank CUDA, m = 64,000, p = 1,000,003, two sketches: rank(A) = 3,514, rank([A|b]) = 3,515, NON_MEMBER, unsaturated (seeds 2026090201/02). Controls: n = 9 and n = 10 saved simple-pair systems reproduce 1,506 / 2,166 MEMBER; the n = 10 degree-4 universe (multigraph W, 17,775 orbits) gives 3,109 MEMBER, re-run by the orchestrator on the host. Second prime ordered.
- Reading: within the loop-free pairwise-max ansatz, 4-edge branches do not suffice at n = 11 while 5-edge branches do (run7/F2), matching k = ⌊(n−1)/2⌋ from the upstream table. Scope gap: loops at degree 4 are not yet excluded (n = 5, 7, 8 upstream certificates use loops) — bead relu-depth-frontier-research-sou (loop-inclusive degree-4 universe at n = 11) closes it. No-claim: a bounded modular null for a named finite family, not a network lower bound.

### §11 addendum, 2026-09-03 01:35 UTC — induction test (bead ksi): the S_11-lift of the n = 10 certificate spans MAX_11 (one prime, first sketch)

- Family: 163,740 loop-free orbits obtained by lifting the 402 upstream n = 10 certificate terms to 11 vertices (mapped into the G-0027 universe by CobaltGull, `artifacts/math/n11-lift-test/max10-lift-map-report.json`), plus record 0 and 5L. streamrank CUDA, m = 64,000, p = 1,000,003, seed 2026090201: rank(A) = rank([A|b]) = 30,200, MEMBER, unsaturated (JSON SHA `5f8741e1…`). Second sketch running; n = 9 → 10 control pending.
- Reading: the prior campaign's CEGIS treadmill on exactly this family never reached a verdict; the full-row sketch settles it in 65 minutes. If seed 2 and the 9 → 10 control agree, "cert(n) ⊆ span(lift(cert(n−1)))" holds at two consecutive rungs, which is the first computed evidence for an inductive construction. Next: exact lift on the lift family's pivot set (rank 30,200) to obtain a certificate whose every term is a relabeled n = 10 certificate term; then read the coefficient structure against the n = 10 coefficients.
- Prior update: P(inductive construction exists for all n) 0.10 → 0.20 conditional on seed 2 + control; the class-sum negative says any such construction must be orbit-level (union-graph aware).

### §11 addendum, 2026-09-03 01:45 UTC — T2 referee final report (commit 50ffe88): PASS, with two follow-ups

- Adds to the 00:58 entry: the referee re-derived the full upstream file independently (byte-identical, 15,896/15,896), recomputed every term with its own DP validated against the pinned Python reference on 373 columns (OK, hinge union 169,166), and predicted the planted-negative residuals exactly. Semantics certified: Σ_t c_t · Σ_{σ∈S_11} Φ_t(σx) = max(x) for all x ∈ R^11, coefficient 1, no normalization.
- Follow-ups before write-up: (1) bead relu-depth-frontier-research-u0j — verify11 unchecked i128 multiply on an unreachable branch becomes checked; (2) the lift report's 169,250 hinge rows vs the certificate's 169,166 (84 directions belonging, by hypothesis, to unused pivot columns) to be confirmed from the problem file; (3) the write-up must state the standard depth-2 realization max(u,v) = (u+v)/2 + (ReLU(u−v)+ReLU(v−u))/2 explicitly, since the verifier certifies the identity, not the network.
- Note: all 15,896 terms have signed mass 5; the 5E and 5L carriers are unused by this certificate.
