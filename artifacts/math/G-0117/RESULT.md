# G-0117 — exact global residual CEGIS

## Current bounded result

The missing bridge from the finite G-0113 panel to exact global
ordered-chamber verification is operational and has completed its first real
iteration.

The corrected exhaustive G-0113 scan returned an exact rational member on all
301 preregistered panel rows.  The binding-clean converter independently reran
the frozen exact postprocessor on the actual scan and retained-column files,
then denominator-cleared the result to a v2 certificate with 92 nonzero
integer-weighted atoms.  Its bindings are frozen in
`PANEL_SEED_HANDOFF_FROZEN.md`.

Complete modular normal-form replay of that real seed processed 3,672,345,600
labelled permutations and refuted the seed globally.  The first canonical
nonzero hinge direction was

```text
(0,0,0,0,0,0,0,0,1,-5,4)
```

with residues

```text
mod 1,000,000,007: 482,908,994
mod 1,000,000,009:  83,090,671
```

One nonzero residue is already a characteristic-zero refutation because the
certificate was cleared to integers.  This outcome therefore does not rely on
the false converse that two modular zeros imply an exact zero.  The direction
is the first exact counterexample row for full-family fresh-Q CEGIS.  It does
not refute the 163,740-column family, much less unrestricted two-hidden-layer
MAX11.

## Exact machinery now frozen

- The subset-DP coordinate pricer computes one hinge row over all 163,740
  atoms together with every atom's 11 exact linear coordinates.
- The certificate converter hashes the actual G-0113 input, rows, scan,
  retained columns, postprocessor, and preregistration; reruns the frozen exact
  postprocessor; compares every decision-bearing field; and only then clears
  denominators.
- The modular replay supports the integer-scaled v2 certificate and rejects
  stale sources, stale binaries, malformed integers, unknown fields, forged
  receipts, duplicate sequences, and input drift.
- The exact replay independently aggregates the full normal form with
  arbitrary-precision integers.  Exact zero, hinge-residual, linear-residual,
  large-integer, and coefficient-mutation paths are exercised.
- `NORMAL_FORM_UNIQUENESS_LEMMA.md` proves that distinct normalized active
  directions give distinct chamber-crossing hyperplanes.  Consequently a
  nonzero hinge coefficient rigorously refutes equality on the open ordered
  chamber.

The post-fix fresh-context review found no arithmetic or uniqueness-lemma
defect and assigned the exact replay seam `PASS_BOUNDED`.  It remains a T1
same-model-family review; the campaign has no available T2 transport.

## Next exact decision

`FULL_FAMILY_CEGIS_PREREGISTRATION.md` governs the live branch.  The next
solve must:

1. bind the complete 301 by 163,740 i128 panel cache to the corrected scan;
2. add all 11 linear normal-form rows and the new hinge row above;
3. reopen all 163,740 columns under fresh modular support selection;
4. solve over Q and exactly replay every accumulated row; and
5. either globally replay the new member or verify an exact left separator
   against every column.

The old 92-term support is a seed only.  Freezing it, freezing its denominator
scale, or declaring nonmembership from a support-restricted solve would be an
invalid inference.

## Claim boundary

No MAX11 identity or unrestricted lower bound has been obtained.  The earned
claims are: an exact finite-panel member, an exact global refutation of that
particular seed, an explicit new CEGIS row, and adversarially tested machinery
for continuing the finite-family search.  A family member becomes a MAX11
candidate only after exact global normal-form zero and still requires an
audited compilation into the declared two-hidden-layer architecture before
Lean formalization.
