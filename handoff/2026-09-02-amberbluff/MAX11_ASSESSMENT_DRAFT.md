# MAX11 campaign — resume assessment (draft core, 2026-09-02)

Author: AmberBluff (Claude Fable 5.1). Mode: resume, P0 orientation only; no ledger edits made.

## 1. The exact object
MAX_11 = h_Δ, Δ = conv{e_1..e_11}. Two hidden layers, real weights, no biases WLOG (homogenization).
Equivalent (HBDSS Thm 5.2 / Bakaev Lemma 8): Δ_10 + A = B, A,B ∈ P^2 = { Σ conv(Z_i ∪ Z'_i) : Z_i, Z'_i zonotopes, arbitrary real generators/translations }.
Rueß ansatz = generators restricted to simplex edges e_i−e_j (plus points), branches of k=5 edges, S_11-symmetrized, decided by exact linear algebra on the sorted cone: 657,833 rows × 12,179,657 templates (both counts reproduced independently by me and by the Wang–Basu reader).

## 2. Verified facts (my own checks)
- n=9,10 upstream certificates: all templates loop-free simple-graph pairs, both sides forests; 246/337 and 252/402 full-dimensional. Denominators 2,3,5,7-smooth.
- Loop-free simple k-edge pair templates (Burnside, validated against the campaign's loop-inclusive numbers): n=10: 12,248; n=11: 462,627.
- Probe (independent subset-DP columns; brute-force validated; n=6 certificate replays exactly): MAX_n ∈ loop-free span mod 1,000,003 for n=5..9; rank(A)=8,13,90,140,1506; nullity 11,12,267,290,9470. n=9 uses 6,326 retained hinge rows (of 20,685 possible), 10.5M nnz.
- One n=11 loop-free column: 1.6–6.1 s Python, 2.5k–28k retained hinges. Whole family ≈ 5e9 nnz.
- G-0110 escape certificate re-run by me: CONSISTENT (a non-braid one-segment atom lies outside the 26,689-column catalogue span).
- AHM Theorem 2 verified: ⌈log_p(n+1)⌉ layers for N-ary weights, p ∤ N ⇒ any rational 2-layer MAX11 certificate has 6 | denominators.
- verify-quick red: SE-10 (gap G-0015 obligation rewritten in place, commit 7cf9d50). 364 commits, ~60% custody/audit ceremony, 2 rounds closed, STATUS.md stale (08-30), many artifacts untracked.

## 3. What the prior campaign established (bounded)
Exact-Q negatives on subfamilies: 9,804-class same-component MAX10 lifts (C-0009); 8,107 Y-spoke (C-0033); one-prime 26,689 (C-0041); signed-mass ≤3 (C-0013). Structural: Λ forces full-support cores (C-0011); ρ_Δ stabilizer bounds (G-0063/65/66); G-0084 (degree 6 ⊄ degree 5 even with symmetry); G-0110 (catalogue incomplete for S2 atoms); 163,740-column MAX10-lift family: 12 CEGIS members (300–924 rows) each refuted globally; family never decided (540-row matrix rank 349). STAR loop quarantine: 20/478 kernel directions classified.
Never tested: complete loop-free family (462,627 templates / 754,017 signed-W orbits) or complete loop-inclusive (7,015,841).

## 4. Ranked paths (draft; probabilities pending red-team and Fable synthesis)
(see final message)
