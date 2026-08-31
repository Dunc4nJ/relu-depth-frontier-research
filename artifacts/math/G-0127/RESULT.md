# G-0127 exact Batch32 coordinate result

## Decision

The single preregistered invocation returned
`EXACT_FULL_FAMILY_BATCH32_COORDINATES`.  All 32 deterministic G-0126
directions now have exact signed-i64 coordinate rows over all 163,740 frozen
records, and all records have their complete 11-coordinate exact linear
vectors.

This is input for a later exact restricted-master solve.  It is not a
membership decision, family-completeness theorem, global MAX11 identity,
lower bound, or Lean theorem.

## Frozen provenance

```text
preregistration:
  artifacts/math/G-0127/BATCH32_COORDINATE_PRICING_PREREGISTRATION.md
  sha256 ddd823a8c63e42c74e07fd1cbee6a7c5fca573f10ab3deb8138674092bde0070
  commit e348dd0

producer:
  artifacts/math/G-0127/src/main.rs
  sha256 68a9062fa28a5ad5da614634066685cc7e66f709fe6309f553317b483ba23cd8
  commit 36ec270

release executable:
  artifacts/math/G-0127/target/release/g0127-batch-coordinate-pricer
  sha256 ab521e503eab3ec014465fffd8da602b1721bf76a00c7c9ef3adadd266379b64

scientific output:
  artifacts/math/G-0127/batch32_coordinate_prices_v1.json
  bytes 26575822
  sha256 c4c5d59b13820027c81bd4e0b74c67027da851f0a6f90bd941484eb9c4533946
```

The captured producer verdict was

```text
schema = max11-g0127-batch32-coordinate-prices-v1
result = EXACT_FULL_FAMILY_BATCH32_COORDINATES
records = 163740
selected_count = 32
wall_seconds = 135.084009026
```

## Complete arithmetic checks

The output contains exactly 5,239,680 direction-major hinge entries and
1,801,140 record-major linear entries.

```text
complete direction-major hinge signed-i64-LE sha256:
  6435f44216f7545f466a793f31eb81c625a44ad94e21675dfab382e2d97550e5

complete linear signed-i64-LE sha256:
  84cc206d635fa7f651578ab46cda56f6154d0ebd22ca2be26ceeffcf0594aa51

candidate exact-dot decimal-LF sha256:
  000ae45daea6c4debf91f47f3accd7877762b830c30945d31f1f1c97d3c7262b
```

The linear digest exactly reproduces the independently audited G-0118 value.
For every one of the 32 rows, the 131-term arbitrary-precision candidate dot
product is nonzero, equals the corresponding exact G-0126 residual, and
reduces to both frozen modular residues.  The 32-value decimal-LF digest is
therefore identical to the sealed G-0126 digest above.

The 131-term dot product with the linear vectors is exactly zero in
coordinates 0 through 9 and exactly `target_scale * 11!` in coordinate 10.
The in-memory `+1` mutation at candidate sequence 0 changed both the hinge-dot
and linear-dot receipts and was rejected.

An independent Python BigInt/stream check re-read the complete 26 MB artifact,
recomputed every row digest, the full hinge and linear digests, all 32 exact
candidate dots and prime reductions, all 11 linear dots, every row statistic,
every bound file hash, and the mutation flags.  It returned `PASS` and
confirmed that no partial temporary output remained.

The producer tests passed 2/2, strict Clippy passed with warnings denied, the
underlying literal/kernel tests passed 5/5, and the release `--self-test`
passed before the scientific invocation.
