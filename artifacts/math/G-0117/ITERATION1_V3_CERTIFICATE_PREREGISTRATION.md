# G-0117e preregistration — binding-clean CEGIS replay certificate v3

Registered after the first panel-seed residual direction and its 163,740
coordinate prices were observed, but before the full cache completed and before
the iteration-1 modular or exact-Q membership decision.  The purpose is to
close an observed provenance defect: v2 names only the original G-0113
postprocessor and therefore cannot truthfully certify coefficients changed by
later CEGIS rows.

## Fixed iteration-1 row order and target

The accumulated system has exactly 313 rows, in this order:

1. the 301 frozen G-0113 panel rows, descriptors `panel:0` through
   `panel:300`, with the original 301-entry integer target;
2. the eleven ordered-cone linear rows, descriptors `linear:0` through
   `linear:10`, with target `(0,...,0,11!)`; and
3. the hinge row descriptor
   `hinge:0,0,0,0,0,0,0,0,1,-5,4`, with target zero.

Descriptors must be unique.  Their order, their target values, the complete
163,740-value digest of each appended row, and the hash of the document that
contains them are certificate inputs.  Reordering any two descriptors, dropping
a row, changing a target, or substituting a coordinate-price stream invalidates
the certificate.

## Certificate schema

The new certificate schema is
`max11-g0117-global-replay-certificate-v3`.  It retains the v2 top-level
`target_scale` and nonzero integer `(sequence, coefficient)` terms, but replaces
`source_exact_postprocess` by `source_cegis` with these required fields:

```text
source_cegis.sha256                         exact fresh-Q result bytes
source_cegis.schema                         max11-g0117-fresh-q-cegis-result-v1
source_cegis.result                         FRESH_Q_MEMBER_ALL_ROWS_REPLAYED
source_cegis.paths.panel_input              workspace-relative path
source_cegis.paths.panel_rows               workspace-relative path
source_cegis.paths.cache_manifest           workspace-relative path
source_cegis.paths.cache_payload            workspace-relative path
source_cegis.paths.accumulated_rows         workspace-relative path
source_cegis.paths.modular_scan             workspace-relative path
source_cegis.paths.solver_source            workspace-relative path
source_cegis.paths.solver_executable        workspace-relative path
source_cegis.bindings.<same eight names>     SHA-256 of each actual path
source_cegis.receipt.rows                    313
source_cegis.receipt.columns                 163740
source_cegis.receipt.descriptors_sha256      ordered descriptor stream
source_cegis.receipt.targets_sha256          ordered signed-i128 target stream
source_cegis.receipt.selected_sequences_sha256
source_cegis.receipt.selected_basis_sha256   row-major signed-i128 basis
source_cegis.receipt.exact_replay_sha256     canonical rational all-row replay
source_cegis.receipt.all_rows_replayed       true
source_cegis.receipt.coefficient_mutant_rejected true
```

All paths must be relative, contain no `..`, remain under the repository root,
and exist at replay time.  The exact and modular replayers independently hash
all eight actual files, require equality with `bindings`, parse the fresh-Q
result, and require every duplicated receipt field to match it.  Missing or
stale files fail before normal-form aggregation.

The fresh-Q result must in turn bind the cache manifest and payload, the
ordered row document, both full-family modular scans, its own source and
interpreter executable, the selected sequence list and selected basis, and the
canonical exact replay receipt.  A hash string without the corresponding
actual file is not evidence.

## Fresh normalization

The solver obtains rational coefficients on the 313-row system and recomputes

```text
L = lcm(denominator(c_j) for every selected coefficient c_j)
a_j = L c_j.
```

The v3 `target_scale` is this newly computed positive integer `L`.  It is not
copied from the panel seed or any earlier iteration.  Zero integer terms are
removed only after all 313 rational rows replay exactly.  Adding one to the
first nonzero integer coefficient must break at least one exact accumulated
row.

## Replay and hostile controls

Both normal-form replayers accept either the frozen v2 form or v3; neither may
silently coerce one provenance shape into the other.  For v3 they must reject:

1. missing cache, row, scan, solver-source, or solver-executable files;
2. a stale digest for any bound file;
3. reordered row descriptors or targets;
4. a selected-basis digest or sequence digest mismatch;
5. `all_rows_replayed=false` or a changed exact replay receipt;
6. a reused previous target scale; and
7. an integer coefficient-plus-one mutation.

Passing provenance checks only admits the candidate to global replay.  Exact
BigInt zero is required for a global identity.  Modular zeros remain a gate;
any nonzero modular residue exactly refutes that rational candidate only.

## No-claim boundary and retirement

A v3 certificate is a denominator-cleared exact-Q member of the accumulated
313-row system with binding-clean provenance.  It is not, by itself, a global
identity, a completeness theorem for the 163,740-column family, an unrestricted
two-hidden-layer lower bound, or a MAX11 construction.

This schema is retired only when a reviewed successor preserves every binding
above and the replayers stop admitting v3.  Completion of iteration 1 does not
retire it.
