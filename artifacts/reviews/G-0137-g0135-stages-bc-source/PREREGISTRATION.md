# G-0137 preregistration — outcome-blind source audit of G-0135 Stages B/C

## Subject and blindness

Audit the future committed Stage B exact Batch32 coordinate pricer and Stage C
exact 412-row full-family master, including their Cargo/Python dependencies and
release artifacts, before any G-0135 scientific manifest, selected Batch32,
coordinate receipt, or master result exists.  Do not run Stage A's complete
replay or create any scientific output.

## Stage B obligations

Return `PASS` for Stage B only if source inspection and independent probes show:

1. It accepts exactly the Stage-A schema and requires exact G-0132
   reconciliation, 32 unique valid directions in strict signed-`i8` tuple
   lexicographic order, canonical nonzero BigInt residuals, correct direction
   byte digest, correct decimal-LF digest, and the independently audited first
   direction/coefficient.
2. It prices every selected direction on all 163,740 frozen records in canonical
   order using the pinned hinge-coordinate specification.  Atomic coordinates
   are checked `i64`; every dot product and residual comparison is signed
   arbitrary precision.
3. It emits exactly 5,239,680 direction-major coordinates, with per-row and
   aggregate digests, extrema, nonzero counts, and exact candidate dots equal to
   Stage A.  No modulus, dependency screen, or magnitude filter changes a row.
4. Truncation, reordering, coefficient, residual, direction, digest, and
   coefficient-plus-one mutants fail, while a planted positive fixture passes.
5. All inputs, sources, executable, manifest, and prior receipts are bound at
   entry and exit; publication is atomic and no-overwrite.

## Stage C obligations

Return `PASS` for Stage C only if source inspection and independent matrix
fixtures show:

1. The validated G-0128 380-row system is an immutable prefix and the 32 Stage-B
   rows are appended in receipt order.  The target is the original unscaled
   380-vector followed by 32 exact zeros; no previous denominator is carried.
2. All 176 prior selected columns are replayed exactly, their old rank/identity
   are checked, and the new rows must reject the prior member before solving.
3. Every one of the 163,740 columns remains eligible.  The exact-Q loop derives
   a left separator when needed, scans all columns in canonical order, appends
   the first exact nonzero-priced column, and requires a unit rank increase.
4. The only scientific terminals are exact 412-row membership or an exact
   separator annihilating all frozen columns with nonzero target pairing.
   Modular ranks may be diagnostics only.  No support freeze, zero-price-column
   deletion, row deletion, approximate terminal, or sparsity preference exists.
5. A member is replayed before and after primitive denominator clearing.  A
   separator is replayed against every column.  Both branches have must-fail
   coefficient/row/target/separator/census mutants and atomic publication.

## Independent probe and artifacts

The reviewer must write fresh, non-importing probes that:

- independently recompute the signed-byte and decimal-LF stream semantics;
- compare Stage B's kernel to an independent exact route on planted records and
  reject a deliberately corrupted coordinate/census;
- exercise Stage C on small exact rational member and nonmember matrices,
  requiring the correct member and separator terminals and rejecting target
  scale, omitted-column, and separator mutants;
- verify all committed path/SHA/ancestry and executable bindings; and
- run only self-tests/preflights that cannot emit scientific outputs.

Publish a report, independent probe source/receipt, self-test receipt, and one
combined source-audit receipt under this directory.  The final receipt must
identify both exact subjects, bind their source/executable hashes, record
`scientific_manifest_observed=false` and `scientific_output_observed=false`,
and use verdict `PASS` only when both stages pass.

This is T1 source clearance only.  It cannot promote a residual, coordinate
pack, member, separator, global identity, unrestricted MAX11 statement, or Lean
theorem.  Any unresolved arithmetic, all-column, target-scale, selection,
census, or custody defect is `FAIL`.
