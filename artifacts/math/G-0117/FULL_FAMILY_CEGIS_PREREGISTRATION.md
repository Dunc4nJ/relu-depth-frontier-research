# G-0117d preregistration — full-family fresh-Q residual CEGIS

Registered after the corrected G-0113 process crossed the 133,449-record
DISJOINT boundary but before either boundary target decision was printed or
observed, before the 163,740-record outputs existed, and before exact-Q
postprocessing.  The only observed boundary values were the matching modular
ranks `113,113`.

## Branch and question

Run this branch only if the frozen G-0113 postprocessor returns an exact-Q
finite-panel member.  Can repeated exact global residual rows either produce a
complete normal-form identity or certify exact nonmembership in the fixed
163,740-column family?

If G-0113 is a nonmember, do not build this cache merely to create activity;
use the already frozen all-column separator replay.

## One-time exact panel cache

Re-run the frozen G-0116/G-0113 evaluator over sequences `0..163739` and write
all 301 entries of every panel column in sequence-major order as signed
little-endian `i128`.  The expected payload size is exactly

```text
163740 * 301 * 16 = 788571840 bytes.
```

The manifest must bind the frozen input, row document, evaluator, evaluator
gate, completed corrected-scan report, cache producer, embedded-at-build
sources, executable, dimensions, layout, width, endianness, minimum/maximum,
and data SHA-256.  It must reproduce the completed scan's
`all_vectors_i128_le_sha256`, `ordered_vector_digests_sha256`, all eight control
hashes, value range, and complete record census.  Checked narrowing is required
where later solvers use a smaller type; the canonical cache remains `i128`.

Truncating the last record, transposing row/column order, reversing one column,
or changing one byte must be rejected.

## Initial global row set

Before the first expensive full-normal-form replay, append all 11 exact linear
normal-form rows over the full family.  Obtain them from one binding-clean
G-0117 coordinate-pricer execution with `emit_values=true`; require 163,740
hinge values, 163,740 linear vectors, current embedded-source and executable
bindings, and the independently frozen linear-vector stream hash.

The unscaled rational target is always

```text
panel target (301 entries), followed by (0,...,0,11!) for the 11 linear rows.
```

Later hinge rows have target zero.  A certificate's denominator-cleared
`target_scale` is an output normalization for that one certificate only.  It
must never be frozen as the target scale of the next rational solve.

## Fresh-Q full-family solve invariant

For every iteration, let `A_R` be all 163,740 columns on every accumulated row
and let `b_R` be the original rational target above.  The solver must:

1. preserve every earlier row and reject duplicate coordinate descriptors;
2. reopen all 163,740 columns, never only the previous support;
3. use two fresh modular rank/membership scans only to select candidate support;
4. solve the selected basis over `Q` and replay every accumulated row exactly;
5. if a selected support misses, derive an exact integer left separator and
   price it against every full-family column before declaring nonmembership;
6. if a violating column exists, add it and continue column generation; and
7. clear denominators afresh only after an exact-Q member is obtained.

A modular miss is not a Q obstruction.  A separator over retained support is
not a full-family obstruction.  A previous support may seed the next scan but
may not define its search space.

## Global loop

Convert each exact-Q member into a binding-clean v2 certificate and run the
exact BigInt global normal-form replay.

- Exact normal-form zero advances to symmetry and architecture compilation.
- A nonzero linear residual is impossible after the 11 linear rows replay; if
  observed, it invalidates the row binding or solver.
- A nonzero hinge residual is exact-confirmed, priced over all 163,740 columns
  by the subset-DP pricer, appended with target zero, and triggers a fresh-Q
  solve under the invariant above.
- Exact full-column nonmembership is a bounded obstruction for this family,
  not an unrestricted two-hidden-layer lower bound.

Each new residual row is outside the span of the old augmented row system:
otherwise every old solution would already satisfy it.  Since the family and
its degree-five normal-form direction universe are finite, exact iterations
terminate in either a global identity or a finite separating subsystem.  This
is not a practical iteration-count bound.

## Fixed hostile controls

1. Reproduce all scan hashes and controls, including a far-tail sequence.
2. Reject truncated, transposed, byte-mutated, stale-binary, and stale-source
   cache artifacts.
3. Reproduce the reviewer's planted example where freezing the old support
   falsely reports nonmembership but reopening all columns finds a solution.
4. Reproduce the planted example where freezing the previous integer target
   scale falsely rejects a valid new rational solution.
5. Reject a coefficient-plus-one mutant on every accumulated exact row.
6. For the nonmember branch, require a primitive separator to annihilate every
   cached column and pair nontrivially with the exact target; mutate one
   separator entry and require rejection.
7. Bind every appended hinge row to its canonical direction, query, kernel,
   executable, 163,740-value digest, and exact residual reproduction.

The ordered-chamber normal-form uniqueness lemma is a logical dependency of
hinge-row use and is pinned separately in `NORMAL_FORM_UNIQUENESS_LEMMA.md`.
