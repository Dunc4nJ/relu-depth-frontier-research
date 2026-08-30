# G-0116 clean-room adversarial audit preregistration

Registered before implementing or running the clean-room evaluator.

Consumer: the research lead deciding whether the G-0116 cycle-cut evaluator
may be integrated into the frozen G-0113 301-row scan.  This audit exists
because G-0116's accelerator and exhaustive control share the signed-edge,
level-difference, and panel-folding code, so their agreement is not a fully
independent semantic check.  It retires when that integration decision is
made.

## Frozen objects

- `artifacts/math/G-0116/src/main.rs`
- `artifacts/math/G-0116/cycle_cut_panel_benchmark_v1.json`
- `artifacts/math/G-0113/panel_solver_input_v1.json`
- `artifacts/math/G-0111/dual_rows_v1.json`
- G-0113 panel-solver preregistration/preparation and G-0109 formulas

## Checks and decisions

1. Recompute SHA-256 bindings and reject any mismatch with the frozen
   execution record or official report.
2. Audit all 163,740 prepared records: canonical loopless occurrences,
   equal occurrence mass, exact active support, disjoint cancelled sides,
   absolute cycle rank at most four, and a constructive feedback-vertex
   witness of size at most the cycle rank.
3. Audit all 301 rows: four strictly increasing levels beginning at zero,
   positive profile summing to 11, and the formal (not collapsed numeric)
   stabilizer.  Recompute the target normalization stored in the G-0113
   input.
4. Independently evaluate official controls 0 and 3 using a literal
   two-branch maximum,

   `sum max(S_A', S_B') + (5-s) * sum max(x_0,x_1)`,

   rather than G-0116's `5 E + relu(S_B'-S_A')`/signed-q encoding.  Require
   the complete 301-entry little-endian i128 hashes to equal the official
   report.  Also enumerate the distinct full formal assignments directly on
   rows 0, 150, and 300 for both controls and require exact entry agreement.
   Control 3 is cyclic and active on all eleven labels; control 0 exercises
   inactive-label multiplicities and nonzero common-edge padding.
5. Re-run the frozen binary under default and four Rayon threads and require
   identical semantic hashes.  Run one thread as an adverse performance
   probe; a semantic change is FAIL, while failure of the 10x timing gate is
   a deployment limitation that must be reported rather than a semantic
   failure.

`PASS_BOUNDED` permits integration only for the exact frozen input and row
documents.  It proves no 163,740-column rank, panel membership, global CPWL
identity, completeness result, or MAX11 theorem.
