# G-0168 preregistration — first-row exact admission, then Fresh128 pricing

## Exact target

Let `A` be the frozen `540 x 163740` integer family matrix certified in
G-0140 and reused by the G-0164 member.  Its exact rational rank is 349.
Let `c` be the frozen primitive-integer G-0164 member, so `A c = s b`, where
`b` is the frozen 540-entry target and `s > 0` is the frozen target scale.

G-0164's complete global replay returned a nonzero residual.  Let `h` be the
exact full-family price row of its signed-lexicographically first fresh hinge
direction, and let `r = h c` be that frozen nonzero residual coefficient.  A
correction must satisfy

`A delta = 0` and `h delta = -r`.

Equivalently, the corrected member must solve `[A; h] x = [b; 0]` over `Q`.
The appended hinge target is exactly zero; the global residual coefficient is
not an appended target.

## Stage A — one-row Schur-complement admission

Reuse the certified 349 basis sequences `B` and 349 coordinate rows `R` from
G-0140/G-0164.  Reconstruct the exact nonsingular square matrix
`S = A[R,B]`, requiring its frozen digest.  For the G-0170 row, solve exactly

`S^T lambda = h[B]`.

Scan the 163,740 family columns in canonical sequence order and compute

`Delta_j = h_j - lambda^T A[R,j]`.

Fixed modular primes may identify an early candidate violation, but every
reported violation is recomputed over exact integers after clearing the
denominators of `lambda`.  Modular arithmetic never supplies a terminal
decision.

There are exactly two scientific branches:

1. `FIRST_ROW_EXACT_RANK_GROWTH`: the first exact nonzero `Delta_j` is
   reported.  It certifies rank 350 through the Schur-complement minor
   `det(S) * Delta_j`; the scan may stop at that first exact witness.
2. `FIRST_ROW_EXACT_INCOMPATIBLE_DEPENDENCY`: all 163,740 exact residuals are
   zero.  The cleared relation `z^T A - d h = 0` is replayed on every column,
   and `z^T b != 0` is required.  The bridge identity
   `d r = s (z^T b)` must hold exactly.  Then `(z,-d)` is a primitive exact
   separator for the frozen 541-row target.

A zero residual, bridge mismatch, altered rank/basis digest, missing column,
noncanonical direction, custody drift, or any other contract failure is
`INVALID_NO_SCIENTIFIC_RESULT`, never a third mathematical branch.

## Stage B — complete Fresh128 pricing if Stage A grows rank

Only after `FIRST_ROW_EXACT_RANK_GROWTH`, price all 128 G-0164 fresh residual
directions on all 163,740 canonical records using the audited G-0117 exact
hinge kernel.  Emit the direction-major `128 x 163740` signed-i64 matrix.
For every row, require the arbitrary-precision dot product with all 304 frozen
G-0164 terms to equal the corresponding frozen residual coefficient.  All 128
new target entries are exactly zero.

The next correction decision is

`A delta = 0`, `H delta = -r`,

or, equivalently, whether `-r` lies in the image of `H` restricted to
`ker(A)`.  The old complete basis is reused; `A` is not re-certified merely to
repeat G-0140.  Fixed-prime quotient and augmented-rank calculations may triage
the branch, but an exact member or exact separator is required for a terminal
claim.

## Custody and stopping rule

No outcome-bearing G-0168 admission or Fresh128 pricing run may occur until
the relevant producer bytes, all transitive input bindings, a branch-total
manifest, and an outcome-blind source-audit PASS are committed.  Outputs are
exclusive and all bound inputs are rehashed at the end.  G-0170's row/bridge
and G-0164's member/global result are inputs, not conclusions inherited by
name.

`FIRST_ROW_EXACT_RANK_GROWTH` says only that one row enlarges the frozen
family matrix rank.  `FIRST_ROW_EXACT_INCOMPATIBLE_DEPENDENCY` excludes only
the frozen 163,740-column family under the exact 541-row system.  A later
Fresh128 member would still require complete global replay.  None of these
branches proves family completeness, an unrestricted lower bound, minimality,
an all-`n` theorem, refereed status, formalization, or a Lean theorem.
