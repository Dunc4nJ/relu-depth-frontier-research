# G-0113e preregistration — exact-Q panel postprocessing

Registered during the corrected all-record scan, before its first slice
boundary and before any target-membership decision was observed.

## Frozen input checks

The postprocessor must bind the corrected scanner producer SHA-256
`8be4583119a49d63ef41ab4c86d2f9eb1ee473c99578047c8c62bdcaa01ed47f`,
the frozen input and row hashes, the retained-file hash recorded by the scan
report, both prime reports, every selected sequence, and every retained exact
vector hash.  It must reject modular disagreement at either boundary.

Construct the exact integer matrix from the union of columns selected by p1 or
p2, in scan/sequence order.  Gate-control-only columns are excluded unless they
also selected at a prime.  Compute exact candidate and augmented ranks over Q
with FLINT.

## Member branch

- If the p1 union rank is 301, use its 301 selected columns as the canonical
  support.  Their nonzero p1 minor proves exact column independence.
- Otherwise, select exact pivot columns from the union's deterministic RREF,
  then select coordinate rows from the deterministic RREF of the transposed
  exact basis.
- Solve the resulting square rational system, replay all 301 rows exactly, and
  report every coefficient as a reduced rational string.
- Add exactly one to the first nonzero solved coefficient and require the full
  301-row replay to fail.  If every coefficient is zero or the mutant still
  replays the target, the member branch is invalid.
- Exact replay gives a finite-panel CEGIS seed only.  It must immediately
  advance to complete ordered-cone normal-form replay and residual-row CEGIS.

## Nonmember branch

RREF the transpose of the exact union matrix.  Enumerate free coordinates in
increasing row-index order; for each, set that free coordinate to one and use
the RREF equations to obtain a left-null vector.  Choose the first such vector
whose exact target pairing is nonzero.  Clear denominators, divide by the gcd,
and orient the primitive integer vector so its first nonzero entry is positive.

The resulting vector is only a separator of the retained exact span.  It is
reportable as a separator of all 163,740 candidates only after a fresh exact
all-column evaluator pass verifies zero pairing for every streamed column and
nonzero target pairing.  A modular nonmembership result or retained-span
separator alone is not a characteristic-zero all-family lower bound.

Any exact rank exceeding the agreed modular rank is recorded explicitly as a
bad-prime/retained-union event and receives no all-family interpretation.
