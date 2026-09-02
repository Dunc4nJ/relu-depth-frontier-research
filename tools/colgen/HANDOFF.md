# `max11-colgen` handoff

Build from this directory with `cargo build --release`; the binary is
`target/release/max11-colgen`. Every output path is create-new: remove or rename an
old disposable output before rerunning. `--threads` is required by compute commands
and is currently hard-limited to `1..=6` for the shared host.

## CLI surface

- `validate-templates --input FILE.jsonl[.gz] --n N --branch-edges K --threads T --output REPORT.json [--bruteforce] [--mutate-one-sign]`
- `validate-prices --universe UNIVERSE.json.gz --dual DUAL.json --expected-report EXPECTED.json --threads T --output REPORT.json`
- `benchmark --universe UNIVERSE.json.gz --sample-size S --seed U64 --threads T --output REPORT.json`
- `scan-universe --universe UNIVERSE.json.gz --threads T --output REPORT.json [--start I --limit L]`
- `emit-universe --universe UNIVERSE.json.gz --threads T --output FILE --format jsonl|binary [--modulus P] [--start I --limit L]`

## Column formats

JSONL is one UTF-8 JSON object plus newline per column, in increasing record order:
`{"record_index":usize,"modulus":null|u64,"linear":[i64;n],"hinges":[...]}`.
Each hinge is `{"direction":[i16;n],"coefficient":i64}`; hinges are sorted
lexicographically by direction. With no modulus, coefficients are exact signed
integers. With `--modulus P`, every linear/hinge coefficient is the canonical
residue in `[0,P)` represented as `i64`; directions are unchanged.

Binary begins with `magic[8] = "MCOLGEN1"`, then little-endian `n:u16`,
`branch_edges:u16`, `modulus:u64` (zero means exact), `record_count:u64`.
Each column is little-endian `record_index:u64`, `linear[n]:i64`,
`hinge_count:u64`, then `hinge_count` entries of `direction[n]:i16` followed by
`coefficient:i64`. Columns and hinge directions have the same ordering as JSONL.
There is no padding, checksum, compression, target column, or per-record byte length.

## Convention map

For signed `W=B-A`, ordering `pi` gives back-degree word `w_r=sum_{t<r}
W[pi_r,pi_t]`. Divide a nonzero word by its coordinate gcd and orient its first
nonzero entry positive; retain that primitive hinge exactly when a proper prefix sum
is negative, with coefficient `gcd(w)` times multiplicity. If the raw word's first
nonzero entry is negative, also add the raw word to the linear part using
`ReLU(-z)=ReLU(z)-z`. The fixed linear base is `2*k*r*(n-2)!` at rank coordinate
`r`, where `k=branch_edge_occurrences`. This equals the saved Python convention in
which the lexicographically smaller branch word supplies the linear summand.

## Range streaming

`--start I --limit L` selects the half-open universe-record range `[I,I+L)` and
preserves the original zero-based record indices. Example (run from `tools/colgen`):

```bash
target/release/max11-colgen emit-universe \
  --universe ../../artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --threads 6 --start 4096 --limit 1024 --format binary --modulus 1000003 \
  --output /tmp/columns-4096-5120-p1000003.bin
```

The command generates a small ordered batch in parallel and writes it before making
the next; peak generator memory is therefore bounded by the largest few columns.
For direct in-process use, depend on this crate and call `generate_column(record,n,k)`;
`SparseColumn` contains exact `linear: Vec<i64>` and `hinges: FxHashMap<Vec<i16>,i64>`.
The generator supports only the finite serialized loopless signed-record family; it
does not itself establish MAX11 span membership or an unrestricted depth result.
