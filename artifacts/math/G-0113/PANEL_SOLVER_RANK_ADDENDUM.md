# G-0113e rank-consumer addendum — deterministic left-annihilator oracle

Registered after the 301-row input was frozen and before any all-record panel
scan or modular-rank outcome was observed.  This addendum refines only the
implementation of the preregistered two-prime incremental rank decisions.

## State and update

For each frozen prime independently, maintain an ordered basis
`L = (ell_0, ..., ell_{d-1})` of the left annihilator of all accepted columns,
where each `ell_j` is a length-301 row over the prime field and
`d = 301 - rank`.  Initialize `L` to the 301 identity rows.

For each streamed exact integer column `c` in the preregistered scan order:

1. reduce `c` modulo the prime and compute `u_j = ell_j dot c` for every row
   of `L`, in current order;
2. if all `u_j` vanish, classify `c` as rank-neutral;
3. otherwise let `j` be the least index with `u_j != 0`, compute
   `a_k = u_k / u_j`, and replace every row with `k != j` by
   `ell_k - a_k ell_j`, preserving the relative order of the surviving rows;
4. discard `ell_j`, classify `c` as rank-growing, and retain its sequence,
   descriptor, and exact 301-entry vector for that prime's support.

The update leaves exactly the old annihilator vectors that also annihilate
`c`, so the surviving rows are a basis of the new left annihilator.  Therefore
`u = 0` is equivalent to `c` lying in the current column span, and the retained
columns are independent.  This is algebraically the same incremental-rank
oracle required by the main preregistration; it changes neither scan order nor
candidate selection.

After the DISJOINT boundary and after the union boundary, record
`rank = 301 - len(L)`.  Reduce the exact frozen target modulo the prime and
classify target membership exactly by whether every row of `L` pairs to zero.
If `L` becomes empty, later columns remain rank-neutral without further rank
arithmetic, but they must still be evaluated and included in the exact vector
hash chain and audit controls.

## Determinism and arithmetic

- Use the two already frozen primes `2,000,081` and `3,000,017`.
- Canonicalize every field element to the integer interval `[0, p)` after each
  dot product and row update.
- Choose the least nonzero annihilator coordinate as the pivot; do not use
  magnitude, topology, coefficients, target residuals, or timing.
- Compute inverses by deterministic prime-field exponentiation or an exact
  extended-Euclidean algorithm.
- The p1 retained support remains the canonical exact-Q candidate support.
- Test the rank oracle itself on frozen synthetic matrices covering duplicate,
  zero, full-rank, rank-deficient member, and rank-deficient nonmember cases,
  with direct modular Gaussian-elimination agreement required at both primes.

All validity, exact-Q, separator, and finite-panel claim boundaries from
`PANEL_SOLVER_PREREGISTRATION.md` remain unchanged.
