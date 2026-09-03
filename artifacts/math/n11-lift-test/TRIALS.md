# Trial log — naive MAX10 lift test

All counts name their denominator. These trials concern one finite source-
derived dictionary; they are not exact MAX11 decisions.

- The first synthetic self-test failed before mapping 0 / 163,740 signed-W
  orbits. Its intended multiplicity mutant added an edge to only one branch,
  so the input was rejected as unbalanced instead of testing orbit
  discrimination. The control was corrected to add different nonloop edges to
  both branches; the balanced mutant is distinguished, and all self-tests pass.
- The first full mapping attempt audited 1,193,940 / 1,193,940 raw extensions
  by stored source-fiber multiplicity and mapped 163,740 / 163,740 signed-W
  orbits, but failed after writing the order and before writing its report: a
  relative output path was passed to `Path.relative_to` without normalization.
  The orphan order is retained as
  `max10-lift-g0027-order.failed-relative-path-run.json`, SHA-256
  `0ca84e6b40e9aedfac0c6d294822c11c2d314a38c24c37ad3771c04af92a1d56`.
- One retry command misspelled the directory as `n-lift-test`; Python exited 2
  before processing 0 / 163,740 signed-W orbits and wrote no output.
- The corrected full run completed. Its final order is byte-identical to the
  orphan order above, giving a deterministic replay check in addition to the
  exact certificate controls recorded in `max10-lift-map-report.json`.

No-claim: these failures and controls audit dictionary construction only. They
do not establish modular or exact-rational target membership.
