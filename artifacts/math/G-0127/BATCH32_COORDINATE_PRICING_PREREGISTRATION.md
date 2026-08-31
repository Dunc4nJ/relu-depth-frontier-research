# G-0127 preregistration — exact full-family prices for the G-0126 Batch32

## Frozen purpose and boundary

This protocol is committed before computing any G-0126 selected direction on
the full 163,740-record family.  It produces exact coordinate rows for the
next restricted-master experiment; it does not run that master.

No output is a membership decision, a family-completeness statement, a global
MAX11 identity, a lower bound, or a Lean theorem.

## Frozen scientific inputs

```text
G-0126 complete replay:
  artifacts/math/G-0126/global_replay_v1.json
  sha256 = bd0410d861978956502e9d4c4fc1cd159565f2e170d70509abd0f3eb21b771ea
  schema = max11-g0126-global-replay-v1
  result = GLOBAL_MODULAR_RESIDUAL
  selected_count = 32
  selected direction/residue digest =
    0cd2699dec0bc5ffd7cb81c1454aac79143ae4a37c571fcb707c85a55a5c459e
  exact selected residual decimal-LF digest =
    000ae45daea6c4debf91f47f3accd7877762b830c30945d31f1f1c97d3c7262b

candidate:
  artifacts/math/G-0121/full_family_master_result_v1.json
  sha256 = 53bc7d8894a3552c226ca64f51bf7b369ce1d7c71f532241b14271964abc1036
  nonzero terms = 131

panel/record input:
  artifacts/math/G-0113/panel_solver_input_v1.json
  sha256 = 093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8
  records = 163740 in sequence order

normal-form coordinate kernel:
  artifacts/math/G-0117/src/lib.rs
  sha256 = 2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6
```

The selected directions and modular residues are consumed in the exact
serialized G-0126 order.  The producer must recompute their signed-i8/u64-LE
digest and refuse any reordering, truncation, duplicate, zero residue,
direction invalidity, or receipt/schema/binding drift.  It also binds the
G-0126 preregistration, producer source, and release executable recorded in
that receipt wherever the immutable hashes are meaningful.

## Audited implementation ancestor

The implementation adapts the already used G-0118 coordinate pricer, not its
scientific payload:

```text
artifacts/math/G-0117/src/bin/g0118_batch_coordinate_pricer.rs
sha256 = 35cabc07a3e6a50366c584c737493b393b202092d64f0951a37dde4f515d3058

same-lineage clean-room audit:
  artifacts/reviews/G-0118-iteration4-batch/review_v1.json
  sha256 = e7905d258ed05e004c51b449494c9cd7094e967cdf3c29380646f55caaf2b569
  result = CONSISTENT_WITH_PROVENANCE_LIMITS
```

That audit is T1 evidence, not a proof.  G-0127 must retain the pricer's exact
coordinate semantics while adding receipt-specific dot-product bridges,
stronger source custody, must-fail controls, and atomic output publication.

## Frozen computation

For each input record, construct its increment table once and evaluate all 32
G-0126 directions with `hinge_coefficients`.  Also compute its complete exact
11-coordinate `linear_vector`.  Every integer must fit signed i64 as enforced
by the kernel.

Transpose the hinge data into direction-major order and emit exactly:

```text
32 * 163740 = 5,239,680 signed-i64 hinge entries;
163740 * 11 = 1,801,140 signed-i64 linear entries.
```

For each hinge row record its direction, G-0126 residues, record census,
nonzero count, signed minimum, signed maximum, maximum absolute value, row
signed-i64-LE SHA-256, and all 163,740 values.  Record the complete
direction-major signed-i64-LE digest.  Emit all 163,740 linear vectors and
their record-major/rank-minor signed-i64-LE digest.

Because the linear vector depends only on the frozen records and kernel, its
digest must reproduce the audited G-0118 value

```text
84cc206d635fa7f651578ab46cda56f6154d0ebd22ca2be26ceeffcf0594aa51.
```

## Exact arithmetic bridges

Before publication, parse the candidate's 131 canonical nonzero integer terms
and positive `target_scale` as arbitrary-precision integers.

For every direction row `r_i`, compute

```text
R_i = sum_(term s) coefficient_s * r_i[sequence_s].
```

Require `R_i` to be nonzero, equal byte-for-byte as a canonical decimal to the
corresponding G-0126 `exact_selected_prices[i].exact_residual`, and reduce to
the corresponding ordered residue pair modulo 1,000,000,007 and
1,000,000,009.  Require the decimal-LF stream of all 32 recomputed values to
have SHA-256

```text
000ae45daea6c4debf91f47f3accd7877762b830c30945d31f1f1c97d3c7262b.
```

For every linear coordinate `j`, compute the same 131-term dot product.
Require exact zero for `j < 10` and exactly

```text
target_scale * 11!
```

for `j = 10`.

These bridges show that the emitted rows reject the bound candidate exactly;
they do not solve the enlarged master.

## Frozen controls and custody

- Validate every selected direction with the kernel invariants and reproduce
  the selected digest before pricing.
- Run the G-0117 literal-enumeration versus subset-DP tests and a G-0127
  producer `--self-test` before the scientific invocation.
- The producer self-test includes record/direction transpose, signed-i64
  stream order/sign mutants, exact negative modular reduction, receipt order
  and residue mutants, row truncation, candidate coefficient parsing,
  independent hinge and linear dot mutants, and publication overwrite
  refusal.
- Add one to candidate sequence 0 in memory.  Recompute all 32 row dots and all
  11 linear dots; require the complete exact-dot receipt to differ.  Record
  whether hinge and linear portions changed separately.  A surviving `+1`
  mutant is fatal.
- Unknown receipt/candidate/panel fields, duplicate keys as reached by strict
  deserialization, noncanonical integers, term-projection drift, wrong
  dimensions, source drift, executable drift, an i64 overflow, or any digest
  or exact bridge mismatch is fatal.
- Bind the G-0126 receipt/source/executable, candidate, panel input, kernel,
  audited ancestor source/review, G-0127 source, Cargo manifest/lockfile,
  preregistration, and running executable.  Recheck all bindings after the
  expensive computation.
- Pre-serialize the complete JSON in memory.  Write it to an exclusively
  created same-directory temporary file, flush and sync it, then publish by
  atomic no-overwrite hard link and remove the temporary link.  On failure,
  remove the temporary file and retain no partial scientific output.

## Frozen output and stop rule

The sole scientific output is

```text
artifacts/math/G-0127/batch32_coordinate_prices_v1.json
```

It is created once and never overwritten.  Any disagreement returns an error
without a scientific output.  Success is named
`EXACT_FULL_FAMILY_BATCH32_COORDINATES` and triggers only the separately
preregistered exact-master step.
