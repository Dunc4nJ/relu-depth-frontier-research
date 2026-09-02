# `max11-streamrank`

Streaming CountSketch-style modular rank experiments for the finite MAX11
loopless signed-`W` campaign. Real rows map independently to one bucket with a
deterministic random sign. Dense column-echelon bases use `u32` residues and
block-local reduced pivot sets; old-basis reduction packs one block into exact
`f64` integers and calls OpenBLAS `dgemm`, then reduces back modulo `p`.

The safety check requires `block_size*(p-1)^2+p < 2^53`, so every integer
product and partial sum passed through binary64 is exact. Primes must be below
`2^20`. This is modular/sketched evidence, not exact rational verification.

```bash
source ../../scripts/activate-toolchain.sh
cargo test --release
cargo run --release -- run-saved \
  --input ../../handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --n 10 --branch-edges 4 --filter all --modulus 1000003 --buckets 8192 \
  --seeds 2026090201,2026090202 --batch-size 256 --gemm-block 2048 --threads 6 \
  --expected-columns 12248 --expected-rank 2166 --expected-aug-rank 2166 \
  --expected-verdict MEMBER --output n10-p1000003.json
```

`run-universe` accepts a colgen universe plus optional `--start`/`--limit` and
generates its exact columns in process. Alternatively, `--order-file` accepts
a duplicate-free JSON array of caller-ordered source indices; `sample-order`
can make a deterministic sorted SplitMix64 sample. It has the same sketch/rank
arguments. Outputs are create-new JSON artifacts and include pivot source
indices, ordered-pivot hashes, target sketches, and modular bucket separators
for NON_MEMBER outcomes.
