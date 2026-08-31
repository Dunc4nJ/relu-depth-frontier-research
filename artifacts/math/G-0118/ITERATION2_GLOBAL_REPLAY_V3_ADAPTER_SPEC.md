# G-0118 iteration-2 global-replay adapter v3

This provenance specification was written after the iteration-2 exact member
and its discovery modular replay were observed.  It is therefore **not** a
preregistration of the global outcome.  Its narrower purpose is to replace the
temporary v2 wire-shape adapter with a fail-closed certificate whose terms and
scale are mechanically tied to the actual G-0118 exact result.  The complete
global replay algorithm, primes, normal-form kernel, and zero/nonzero decision
rule were already frozen before the candidate existed.

## Certificate contract

Schema: `max11-g0118-global-replay-certificate-v3`.

The certificate contains the original nonzero integer `(sequence,
coefficient)` terms and freshly computed `target_scale`, plus a required
`source_prefix_cegis` object with:

```text
sha256, result_path, schema, result
recheck_sha256, recheck_path
preregistration_sha256, preregistration_path
runner_sha256, runner_path
solver_executable_sha256, solver_executable_path
cache_prefix_path, cache_prefix_bytes, cache_prefix_sha256
adapter_spec_sha256, adapter_spec_path
bindings
receipt.rows, receipt.family_sequences, receipt.support_rank
receipt.selected_basis_sha256
receipt.all_rows_replayed
receipt.coefficient_mutant_rejected
```

Every path is repository-relative, canonical, exists at replay time, and is
hashed from its actual bytes.  The cache digest covers exactly the first
192,640,000 bytes used by the prefix solver.  `bindings` must exactly equal the
map in the source result and every named file in that map is independently
rehashed.

The consumer parses both the primary result and deterministic recheck, removes
only `wall_seconds` and `maximum_rss_kib`, and requires the remaining JSON
values to be identical.  It requires the fixed iteration-2 result identity,
314-row replay flag, mutation rejection, 40,003-family census, 123 selected
basis sequences, selected-basis digest, runner/preregistration/prefix hashes,
and exact equality of certificate scale and terms to the primary result.

Missing files, path traversal, hash drift, source/recheck disagreement, term or
scale mutation, false replay flags, prefix mutation/truncation, or unknown
certificate fields fail before global normal-form aggregation.

## Global decision boundary

The two-prime replay still has its original meaning.  A nonzero residue modulo
either prime exactly refutes this denominator-cleared rational candidate.  Zero
at both primes is only a screen and must be followed by the BigInt exact global
replay.  Neither outcome proves completeness of the 40,003-column subset, the
163,740-column family, or the unrestricted architecture.

The coefficient-plus-one hostile certificate must be rejected by provenance
before aggregation because its terms no longer equal the bound exact result.
