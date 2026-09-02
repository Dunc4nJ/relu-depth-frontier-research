# `max11-streamrank`

Streaming CountSketch-style modular rank experiments for the finite MAX11
loopless signed-`W` campaign. Real rows map independently to one bucket with a
deterministic random sign. Dense column-echelon bases use `u32` residues and
block-local reduced pivot sets. Old-basis reduction and 64-column rank-panel
updates pack residues into exact `f64` integers, call OpenBLAS `dgemm`, and
reduce modulo `p` once per product block. Only factorization inside a rank
panel remains scalar.

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
`universe.records.len()` (754,017 for G-0027). Resource gates use
`--abort-rank-above R` and `--abort-rss-kib-above KIB`. A triggered gate writes
a create-new `max11-streamrank-abort-v1` partial report, including the processed
denominator and pivots, without attempting a target test or separator.
