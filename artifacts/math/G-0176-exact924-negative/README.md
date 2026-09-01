# G-0176 — exact 924-row member, globally refuted

This directory freezes the current bytes of a provisional 924-row member in
the 163,740-column distinct-nonloop MAX10-lift family and the decisive exact
global counterexample to that member.

## Decisive outcome

- The finite system has 924 rows and the selected integer minor has rank 659
  over `Q` (witnessed modulo both 1,000,003 and 1,000,033).
- The stored primitive integer coefficient vector has 349 nonzero terms and
  replays all 924 finite rows with exactly zero residual.
- The hinge direction
  `[0,0,0,0,0,1,-3,1,1,-2,2]` has the nonzero exact coefficient recorded in
  `global_replay_924_member.json`. An independent implementation recomputed
  that coefficient from all 349 support terms exactly.
- Therefore this finite member is **not** a global MAX11 identity.

## Interpretation correction

The 64 selected heuristic pairs are not 64 literal global column equalities.
An independent scan found 328 nonzero entries in the pair-difference quotient
block. The actual modular decomposition is rank 63 for the representative
block plus rank 1 for the pair-difference block, totaling the reported rank 64
at both primes. This correction does not change the finite rank or the decisive
global nonzero witness.

## Custody and claim boundary

The mathematical negative witness has a bounded independent result audit, but
promotion remains blocked: these exploratory producers were not independently
source-certified before their outcomes were observed. The full 162,522
nonzero-direction census, 11,239,811 processed-entry count, complete residual
digest, and lexicographic-first label were not independently regenerated.
The replay digest also retains a stale `668-MEMBER` domain tag. Accordingly,
only the explicit exact nonzero hinge witness is relied on here.

This is evidence against one 349-term finite-panel member, not nonmembership
of MAX11 in the 163,740-column family, not a family-completeness theorem, and
not a lower bound for unrestricted two-hidden-layer ReLU networks.

The 167,669,760-byte raw pair matrix is intentionally not committed. Its bound
SHA-256 is `6ac563464a3e8cb8e87b9517507d9395da9b9a2e6918810e6861a2171be74372`.
