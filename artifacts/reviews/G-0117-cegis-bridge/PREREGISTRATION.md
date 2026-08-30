# G-0117 exact-global CEGIS bridge audit preregistration

**Reviewer:** DarkCardinal (fresh Codex context; same model family, therefore T1 at most)  
**Mode:** adversarial audit of the proposed bridge, not an attempt to promote the target theorem  
**Frozen before:** inspecting any G-0113/G-0117 implementation or output artifact in this session  
**Date:** 2026-08-31 (Europe/Berlin)

## Exact audit object

The proposed handoff is:

1. consume a completed G-0113 exact-rational solution on a fixed 301-row panel;
2. bind its atom identifiers and rational coefficients into a G-0117 certificate;
3. replay that certificate against the complete global coordinate family;
4. if a nonzero global residual coordinate is found, append that exact row to a one-time cached
   `301 x 163740` atom matrix and re-solve over `Q`;
5. iterate until either a complete global identity is certified or a valid obstruction is
   certified.

This audit asks whether that loop is mathematically sound and implementation-bound. It does not
ask whether the loop terminates quickly, whether the candidate family is globally complete for the
unrestricted neural-network target, or whether finite modular evidence proves a rational/global
claim.

## Preregistered kill criteria

The bridge fails if any one of the following is observed:

1. **Statement/cousin mismatch:** G-0113 and G-0117 use different target functions, atom
   normalizations, orbit multiplicities, linear-correction conventions, sequence orderings, or
   candidate universes without an exact proved conversion.
2. **Schema underbinding:** a certificate can omit, reorder, duplicate, mutate, or misassociate
   support sequences and coefficients while still passing parsing or replay.
3. **Noncanonical rational parsing:** coefficient strings admit ambiguous, floating, overflowed,
   zero-denominator, or silently reduced/modular-only interpretations.
4. **Modular overclaim:** agreement or zero residual modulo one or more primes is treated as exact
   equality over `Q` without a proved integer/rational height bound or full exact replay. A nonzero
   residue modulo a valid prime may refute an exact rational identity only after denominators are
   shown invertible modulo that prime and the modular computation is bound to the exact numerator.
5. **Cache-row mismatch:** cached columns are not demonstrably the same 163740 atoms in the same
   order/normalization as the exact pricer and solver, or cached values are truncated/overflowed.
6. **Incorrect augmented solve:** appending residual rows does not solve the simultaneous system
   `A_S c = b_S` over `Q`, instead freezes old coefficients, projects approximately, or drops prior
   rows.
7. **Invalid separation inference:** failure of the current support or retained basis is reported
   as nonmembership in the full 163740-column span; or a separator is not replayed against every
   full-family column and target over exact arithmetic.
8. **Coordinate incompleteness:** "global" replay omits a class of coordinates needed to imply
   equality of the represented piecewise-linear functions, or the implication is not established.
9. **Unsound stop condition:** the loop declares success on finite checked rows, repeated modular
   zeros, unchanged support, rank stabilization, or solver exhaustion rather than a complete exact
   global replay/proof.
10. **Mutation blindness:** changing one support ID, coefficient sign/numerator/denominator, target
    binding, matrix order, or pricer convention is not detected by the end-to-end bridge.

## Preregistered independent controls

Subject to available artifacts, I will run or construct read-only controls for:

- exact field algebra on a small planted rational system where a panel solution fails a hidden row,
  then succeeds after the row is appended;
- a full-span nonmember case whose exact left-null separator annihilates every column but not the
  target;
- permutation/reordering of support terms, duplicate-term aggregation, and coefficient mutation;
- denominator primes: a rational certificate whose denominator is divisible by a replay prime;
- modular false positives: a nonzero integer residual divisible by all chosen replay primes;
- integer-width limits for the declared cached value type and accumulated dot products;
- independent recomputation of at least one G-0113 panel column through the G-0117 evaluator, if
  the frozen artifacts expose enough information.

## Decision rule and typed outcomes

- `PASS_BOUNDED`: exact-Q simultaneous re-solving and complete-coordinate replay are soundly bound,
  hostile mutations fail, and all claims remain within scope. This only licenses running the loop.
- `PASS_WITH_OBLIGATIONS`: no demonstrated false result, but missing bindings/checks must be
  discharged before a global claim can stand.
- `FAIL_INVALID`: a concrete counterexample or implementation path can produce a false exact/global
  conclusion.
- `INDETERMINATE`: required artifacts are absent or the global-coordinate completeness lemma is not
  available for audit.

No number of same-family checks upgrades this beyond T1. Formalization is out of scope until an
unrestricted decisive result exists and the statement-match obligation is discharged.
