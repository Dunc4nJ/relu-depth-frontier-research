# max11-colgen-loops

Exact sparse-column generation for the loop-inclusive, signed degree-five
pairwise-comparison universe in G-0038. This is a separate crate that imports
the public `max11-colgen` record, sparse-column, output, and loopless generator
API. It does not modify `tools/colgen`.

## Convention

A diagonal pair `(v,v)` contributes the bare coordinate `x_v` once. For a
vertex placed at the next rank of a permutation cone, the loop-aware DP adds

```text
W[v,v] + sum(W[v,u] for already placed u).
```

Thus loop-bearing directions may have a nonzero minimum-coordinate coefficient
`d_0`. Nonloops contribute only when their second endpoint is placed. G-0038
uses zero common-loop padding: after signed cancellation, all remaining common
padding is a nonloop. The separate carrier `5L` represents five common loops;
`5E` represents five common nonloops.

Loopless records with zero common loops delegate directly to
`max11_colgen::generate_column`. The native loop DP is also exposed for the
independent loopless parity control.

## Build and test

```bash
cd tools/colgen-loops
source ../../scripts/activate-toolchain.sh
cargo build --release
cargo test --release
cargo clippy --all-targets --all-features -- -D warnings
```

The crate refuses more than four Rayon threads in this campaign build.

## Emit G-0038

`emit-universe` reads the gzip stream in batches of `2 * threads`; it does not
retain the 7,015,841 input records or output columns. The header is checked for
the exact G-0038 schema, `n=11`, `k=5`, loop allowance, record count, and padding
convention. Record sequence numbers must be contiguous.

```bash
target/release/max11-colgen-loops emit-universe \
  --input ../../artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz \
  --threads 4 --format binary --modulus 1000003 \
  --start 0 --limit 1000 --output /path/to/chunk.bin
```

Omit `--start` to start at zero. Omit `--limit` to emit every remaining record.
The command refuses to overwrite an existing output. Add the two carriers in a
separate file:

```bash
target/release/max11-colgen-loops emit-base-atoms \
  --n 11 --branch-edges 5 --format binary --modulus 1000003 \
  --output /path/to/base-atoms.bin
```

`emit-records` accepts smaller headerless JSONL samples and requires explicit
`--n` and `--branch-edges`. Both emitters support exact integer output (omit
`--modulus`) or residues modulo the named modulus.

## Output formats

JSONL uses `max11_colgen::ColumnOutput`: record index, optional modulus, `n`
linear coefficients, and sorted sparse hinge entries with an `n`-coordinate
primitive direction and coefficient.

Binary output preserves the existing `MCOLGEN1` contract, little-endian:

```text
magic[8] = MCOLGEN1
n:u16, k:u16, modulus:u64 (zero means exact), column_count:u64
for each column:
  record_index:u64
  linear[n]:i64
  hinge_count:u64
  for each hinge: direction[n]:i16, coefficient:i64
```

## Validation surface

The bead artifacts in `artifacts/math/colgen-loops/` cover:

- exact reconstruction of upstream MAX identities at n=5 and n=7;
- literal S_n versus loop-DP equality on all 60 certificate templates;
- 2,000/2,000 exact columns versus the prior Python DP at n=9 and n=10;
- 1,000/1,000 loopless columns versus `tools/colgen` at n=11;
- exact/modular `MCOLGEN1`, 5E/5L, minimum-coordinate, and planted-mutant gates;
- byte custody and a complete 7,015,841/7,015,841 G-0038 record audit;
- a deterministic 1,000-record n=11 throughput benchmark.

These controls do not generate or rank the complete universe and do not decide
MAX11 membership.
