# `max11-streamrank`

Streaming CountSketch-style modular rank experiments for the finite MAX11
loopless signed-`W` campaign. Real rows map independently to one bucket with a
deterministic random sign. Dense column-echelon bases use `u32` residues and
block-local reduced pivot sets. Old-basis reduction and 64-column rank-panel
updates pack residues into exact `f64` integers, call OpenBLAS `dgemm`, and
reduce modulo `p` once per product block. Only factorization inside a rank
panel remains scalar.

An opt-in `cuda` feature adds `--backend cuda`. It leaves column generation and
panel pivot discovery on the host, keeps the canonical `u32` basis in resident
8,192-column GPU segments, and sends the same exact-binary64 products through
cuBLAS `dgemm`. The CUDA report adds transfer byte numerators, transfer time,
and peak allocated VRAM to `reducer_metrics`. Use one sketch per CUDA process
when the two resident bases would exceed device memory.

Every `STREAMRANK_PROGRESS` line and serialized progress point reports the
just-finished batch's `generate_s`, `sketch_s`, `gemm_s`, `host_reduce_s`,
`basis_update_s`, and `io_s`. Sketch time includes dense-matrix allocation;
host-reduce time is reducer wall time excluding measured GEMM and scalar
pivot/basis-update work. Pipelined phase durations are active work clocks and
can overlap, so their sum is not a wall-time identity.

`run-universe` prepares generated-and-sketched batches on a scoped producer
and sends them through a capacity-one channel to the reducer. This bounded
pipeline overlaps batch `k+1` preparation with batch `k` reduction and limits
the prepared-batch queue to one entry. Sketching is parallel only across
columns; each column retains the original sequential bucket-accumulation order,
and indexed collection plus FIFO receipt preserve source order exactly.

The safety check requires `max(block_size,panel_size)*(p-1)^2+p < 2^53`, so every integer
product and partial sum passed through binary64 is exact. Primes must be below
`2^20`. This is modular/sketched evidence, not exact rational verification.

```bash
source ../../scripts/activate-toolchain.sh
cargo test --release
cargo run --release -- run-saved \
  --input ../../handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --n 10 --branch-edges 4 --filter all --modulus 1000003 --buckets 8192 \
  --seeds 2026090201,2026090202 --batch-size 256 --gemm-block 2048 \
  --rank-panel 64 --threads 6 \
  --expected-columns 12248 --expected-rank 2166 --expected-aug-rank 2166 \
  --expected-verdict MEMBER --output n10-p1000003.json
```

On a CUDA host, build with `cargo build --release --features cuda` and add
`--backend cuda`. The CPU backend remains the default and reference path.

`run-universe` accepts a colgen universe plus optional `--start`/`--limit` and
generates its exact columns in process. Alternatively, `--order-file` accepts
a duplicate-free JSON array of caller-ordered source indices; `sample-order`
can make a deterministic sorted SplitMix64 sample. It has the same sketch/rank
arguments. Outputs are create-new JSON artifacts and include pivot source
indices, ordered-pivot hashes, target sketches, and modular bucket separators
for NON_MEMBER outcomes.

One or two distinct values are accepted by `--seeds`. Stage runs may append
the exact `5L` carrier with `--include-five-l true`; for `n=11` it has eleven
linear coefficients equal to `5*10! = 18,144,000`, no hinges, and source index
`universe.records.len()` (754,017 for G-0027). The generic
`--include-linear-carrier true` form appends `kL` for the universe's branch
size with coefficient `k*(n-1)!` on every coordinate (14,515,200 for 4L at
n=11). The two carrier flags are mutually exclusive. Resource gates use
`--abort-rank-above R` and `--abort-rss-kib-above KIB`; the memory gate uses
high-water RSS so transient GEMM storage is counted. A triggered gate writes
a create-new `max11-streamrank-abort-v1` partial report, including the processed
denominator and pivots, without attempting a target test or separator.
