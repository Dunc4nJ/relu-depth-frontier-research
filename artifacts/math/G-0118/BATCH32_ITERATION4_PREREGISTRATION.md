# G-0118 candidate-4 deterministic batch CEGIS preregistration

## Frozen purpose

Amortize the next counterexample-guided refinement step for the exact 316-row
prefix member by selecting and pricing up to 32 global residual directions in
one frozen pass. This protocol is fixed before running the candidate-4 global
replay or inspecting any candidate-4 residual map.

## Frozen inputs

```text
candidate:
  artifacts/math/G-0118/prefix_exact_cegis_iteration4_v1.json
  sha256 = 728c06bd02f03367fbfa9f50c0353dc74b708a6ef576520cc0eaa72e2e472e1b
  schema = max11-g0118-prefix-exact-cegis-accumulated-v1
  result = PREFIX_EXACT_Q_MEMBER_ALL_316_ROWS
  terms = 102

independent recheck:
  artifacts/math/G-0118/prefix_exact_cegis_iteration4_recheck_v1.json
  sha256 = f29c7095a60ab945293bb1b182afde372405e3cb45c3509080f766aebf46911f

panel input:
  artifacts/math/G-0113/panel_solver_input_v1.json
  sha256 = 093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8

normal-form kernel:
  artifacts/math/G-0117/src/lib.rs
  preregistration-time sha256 = 84b37ea50f012bfe8310de84b1ca27a7c1b77de90978635dd483798759d4c6aa
```

The implementation commit will record the final kernel and producer hashes
after adding the shared-increments batch entry point. Running executables must
verify that their compiled-in sources equal the files on disk.

## Frozen modular replay and selection rule

Use the ordered primes 1,000,000,007 and 1,000,000,009. Replay all 102 integer
certificate terms through the complete normal form. Subtract the scaled MAX11
target in each field before making any decision. Require the full census of
102 × 11! labelled permutations and record all linear residuals.

The four accumulated hinge directions, in this exact order, are

```text
(0,0,0,0,0,0,0,0,1,-5,4)
(0,0,0,0,0,0,0,0,1,-4,3)
(0,0,0,0,0,0,0,0,1,-3,2)
(0,0,0,0,0,0,0,0,1,-2,1)
```

The candidate must list exactly these four accumulated directions, and every
one must have residue zero in both fields. Any failure stops the run as an
accumulated-row replay defect; no residual batch may be emitted.

After that check:

1. Retain every hinge direction whose residue is nonzero in either field.
2. Sort retained directions by the signed integer 11-tuple in ascending
   lexicographic order.
3. Freeze `K = 32`.
4. Select the first `min(32, retained_count)` directions.
5. Emit each selected direction and its ordered pair of field residues.

The receipt must bind the candidate, panel input, normal-form kernel,
normal-form uniqueness lemma, producer source, executable, primes, `K`, full
replay censuses, all four accumulated-row checks, total nonzero direction
count, selected count, and the exact ordered selected prefix.

If every hinge and linear residual is zero in both fields, emit a two-prime-zero
screen with an empty prefix. This is not an exact-Q identity and must trigger
exact replay or a deterministic coefficient bound.

## Frozen exact batch-pricing rule

Only after the replay receipt is sealed, price its selected prefix exactly over
all 163,740 frozen records. For each record, compute its increment table once
and reuse it for every selected direction. Emit a direction-major matrix of
signed-i64 hinge coefficients, one row per selected direction and one column
per frozen record. Compute the linear vector once per record and emit the
complete 163,740 × 11 signed-i64 linear matrix.

The price receipt must bind the replay receipt, panel input, kernel, producer,
executable, dimensions, ordered directions and modular residues, per-row
nonzero/max statistics and signed-i64 stream hashes, the complete
direction-major hinge stream hash, and the complete linear stream hash. It must
refuse to overwrite an existing output.

No batch-price result may be inspected before this preregistration, both Rust
producers, and their tests are committed.

## Frozen controls

- Positive: the 102-term candidate completes the full replay, passes all four
  accumulated-row zero checks, and emits the deterministic selected prefix.
- Provenance negative: a one-unit mutation of any bound candidate coefficient
  changes the candidate SHA-256 and is rejected before replay.
- Arithmetic negative: the implementation also adds one to the first
  coefficient in memory and requires this planted mutant to fail at least one
  accumulated-row zero check or otherwise change the selected global receipt.
- Structural negatives: duplicate/out-of-range term sequences, malformed
  integers, record-order drift, wrong candidate identity, wrong `K`, reordered
  selected directions, inconsistent selected count, and source drift are fatal.

## Frozen continuation

Append selected rows with exact target zero in canonical order, discarding only
rows that are exactly rank-dependent on the already accumulated row system.
Then solve the reopened 163,740-column rational restricted master. The exact
rank filter and solve are a later artifact and are not implied by the modular
receipt.

## Claim boundary

Selected modular rows are deterministic CEGIS inputs. A nonzero two-prime
residual exactly refutes candidate 4, but does not refute the frozen family.
Two-prime zero is only a screen. Exact batch prices are finite-family rows, not
an existence result, a family-completeness theorem, or a MAX11 theorem.
