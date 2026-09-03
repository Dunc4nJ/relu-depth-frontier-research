# Stream-rank interchange format v1

The decision artifact is UTF-8 JSON with schema `max11-streamrank-pivots-v1`.
It names the source path and SHA-256, `n`, branch size, subject/filter, prime,
bucket count, batch size, GEMM block, rank-panel width, source-column
denominator, reducer `backend` (`cpu` or `cuda`),
generation/allocation/sketch/reducer timings, and target.
Each progress entry also carries per-batch active durations `generate_s`,
`sketch_s`, `gemm_s`, `host_reduce_s`, `basis_update_s`, and `io_s`.
`sketch_s` includes dense-matrix allocation. `host_reduce_s` is reducer wall
time after subtracting measured GEMM and scalar pivot/basis-update time. The
durations can overlap in pipelined runs and therefore need not sum to elapsed
wall time.
Each entry in `sketches` freezes the hash algorithm and seed, ranks of `A` and
`[A|b]`, saturation/verdict, and parallel arrays `pivot_columns` (source
record indices, discovery order) and `pivot_buckets` (`u32`, same length).
`pivot_columns_u64_le_sha256` hashes the ordered source-index array.
The target is appended only for the augmented-rank test and never appears in
`pivot_columns`. `target_sketch_nonzero` is a sparse bucket/residue vector.
For a NON_MEMBER result, `left_separator` has explicit bucket length, sparse
canonical residues, its nonzero target dot product, and the denominator of
basis columns it was checked against. Separate primes are separate artifacts;
a manifest may hash and list both.

CUDA reducer metrics keep the same GEMM product denominator and additionally
record host-to-device and device-to-host byte numerators, transfer seconds, and
peak allocated device bytes. These are zero on the CPU backend.

`run-universe --order-file INDICES.json` accepts an arbitrary duplicate-free
JSON array of zero-based universe record indices and preserves that order.
The result records the order-file path and SHA-256; pivot indices always refer
to the original universe, not positions within this list.

Exact selected-column batches reuse colgen's `MCOLGEN1` binary format. Its
little-endian header is magic `[u8;8]`, `n:u16`, branch size `u16`, modulus
`u64=0`, record count `u64`. Each record is source index `u64`, `n` linear
`i64` coefficients, hinge count `u64`, then that many direction `[i16;n]`
plus coefficient `i64` entries. Selected batches may contain arbitrary source
indices in pivot-discovery order: readers must not infer contiguity. A batch
contains at most 1024 columns and its SHA-256 belongs in the exact-leg manifest.

If `five_l_carrier` is non-null, that column is appended after the order file.
Its source index is exactly `universe.records.len()` (one past the largest
universe record index), and the descriptor freezes the exact common coefficient
on all `n` linear coordinates and its zero hinge count. For G-0027 this sentinel
is 754,017 and the exact coefficient is `5*10! = 18,144,000`. Exact gatherers
must synthesize this declared column; it is not a serialized universe record.

If `linear_loop_carrier` is non-null, it is the generic `kL` analogue. Its
source index is likewise one past the largest universe record index, its exact
coefficient on each of the `n` linear coordinates is `k*(n-1)!`, and its hinge
count is zero. Exactly one of `five_l_carrier` and `linear_loop_carrier` may be
non-null.

A resource-gated partial run uses schema `max11-streamrank-abort-v1` and result
`ABORTED_GATE`. It records requested and processed column counts, exact real-nnz
numerator over the processed denominator, progress, current/high-water RSS,
pivot arrays and hashes, and all timing counters. It deliberately has no target
rank, verdict, or separator and is not a `max11-streamrank-pivots-v1` decision
artifact.

For modular-only batches the same format permits a nonzero header modulus and
canonical `[0,p)` residues stored as `i64`. Directions never change. See
`../colgen/HANDOFF.md` for the complete encoding and convention map.
