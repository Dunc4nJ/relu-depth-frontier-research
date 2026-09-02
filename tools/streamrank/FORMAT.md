# Stream-rank interchange format v1

The decision artifact is UTF-8 JSON with schema `max11-streamrank-pivots-v1`.
It names the source path and SHA-256, `n`, branch size, subject/filter, prime,
bucket count, batch size, GEMM block, source-column denominator, and target.
Each entry in `sketches` freezes the hash algorithm and seed, ranks of `A` and
`[A|b]`, saturation/verdict, and parallel arrays `pivot_columns` (source
record indices, discovery order) and `pivot_buckets` (`u32`, same length).
The target is appended only for the augmented-rank test and never appears in
`pivot_columns`. Separate primes are separate artifacts; a manifest may hash
and list both.

Exact selected-column batches reuse colgen's `MCOLGEN1` binary format. Its
little-endian header is magic `[u8;8]`, `n:u16`, branch size `u16`, modulus
`u64=0`, record count `u64`. Each record is source index `u64`, `n` linear
`i64` coefficients, hinge count `u64`, then that many direction `[i16;n]`
plus coefficient `i64` entries. Selected batches may contain arbitrary source
indices in pivot-discovery order: readers must not infer contiguity. A batch
contains at most 1024 columns and its SHA-256 belongs in the exact-leg manifest.

For modular-only batches the same format permits a nonzero header modulus and
canonical `[0,p)` residues stored as `i64`. Directions never change. See
`../colgen/HANDOFF.md` for the complete encoding and convention map.

