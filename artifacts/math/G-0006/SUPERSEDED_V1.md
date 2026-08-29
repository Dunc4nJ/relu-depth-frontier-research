# Superseded G-0006 v1 normalization

The following discovery artifacts are retained for audit history but must not be cited as exact
residual evidence:

- `orbit_seed_solution.json` — SHA-256
  `a40b73344202c43a0b0aac70347d9041bf211404627c768988f11fbe2de205ba`;
- `orbit_seed_hinge_residual.json.gz` — SHA-256
  `c4fe55562685b76c591b49faadcded3daf4da81bf9dd54e3fa9cf953617459f2`.

The 364 orbit rows sum over distinct assignments of a repeated-value profile and use
`(# assignments) * MAX` as their target.  A full unnormalized symmetrized atom counts each such
assignment `product(count_i!)` times.  Consequently the v1 orbit coefficients represented
`11! * MAX`, but the v1 residual subtracted only `MAX` from the final linear coordinate.

The hinge coefficients themselves do not depend on target normalization and were nonzero, so the
bounded conclusion that this particular 192-term seed is not a certificate survives.  Nevertheless,
the v1 linear residual is wrong.  Version 2 divides serialized certificate coefficients by `11!`,
enforces the delivered family's loopless scope, and is subject to fresh adversarial replay.

No claim about the full 9,804-class span follows from either seed's failure.

The mathematically normalized v2 files
`orbit_seed_solution_v2.json` (`d8f3cd5a...`) and
`orbit_seed_hinge_residual_v2.json.gz` (`c73f920c...`) corrected the `11!` factor, but they predate
the custody hardening requested by the adversarial reviewer: the class file bound only candidate
metadata, and the solution did not bind the eight NPZ inputs or the raw/quotient matrices.  They are
therefore retained as intermediate discovery artifacts, not final evidence.  Version 3 additionally
binds the canonical pair list, source-certificate bytes, every orbit-input file, and both matrices.
