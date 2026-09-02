# `max11-price-universe`

Exact all-column pricing for the finite MAX11 campaign. The binary accepts the
frozen exact `MCOLGEN1` stream, saved n=9/n=10 JSONL systems, or the G-0027
universe directly. Direct universe pricing calls `max11-colgen` as a library in
bounded chunks; it does not duplicate the column generator or materialize the
roughly terabyte-scale full exact stream.

Every rational separator is scaled once to its positive common denominator.
Each price is then an integer dot product. The fast path uses checked `i128`;
any weight, product, or sum that does not fit is promoted to `num_bigint::BigInt`.
Independently accumulated residues at 1,000,003 and 1,000,033 must equal the
exact scaled integer reduced modulo each prime on every column.

The full price-vector SHA-256 hashes this canonical byte sequence:

1. ASCII `MPRICEV1`, `n:u16-le`, denominator magnitude length `u64-le`, then
   the positive denominator magnitude in big-endian order;
2. for each column in evaluation order: source index `u64-le`, sign byte
   (`0` zero, `1` positive, `2` negative), magnitude length `u64-le`, and
   magnitude bytes in big-endian order;
3. ASCII `ENDPV001` followed by the evaluated-column count `u64-le`.

The violator JSONL stores each nonzero `source_index` and `scaled_price`; the
single common rational denominator is hash-bound in the report. Outputs use
create-new semantics.

```bash
cargo build --release --manifest-path tools/priceuniverse/Cargo.toml

# Production: bounded in-process reuse of colgen, with the 5L source carrier
# and target evaluated after all 754,017 G-0027 records.
tools/priceuniverse/target/release/max11-price-universe price-universe \
  --universe artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --separator separator.json --threads 16 --include-five-l true \
  --include-target true --violators violations.jsonl --output report.json

# Frozen exact interchange stream.
tools/priceuniverse/target/release/max11-price-universe price-mcolgen \
  --input columns.bin --separator separator.json \
  --violators violations.jsonl --output report.json

# Saved-system known answers; filter is `all` or `union-trees`.
tools/priceuniverse/target/release/max11-price-universe price-saved \
  --input handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --separator separator.json --filter all \
  --violators violations.jsonl --output report.json
```

`price-universe` also accepts `--order-file INDICES.json` instead of a
contiguous `--start`/`--limit` range. The array must be nonempty,
duplicate-free, and in range; its order is the price-vector order and its
SHA-256 is recorded. The 5L and target flags are accepted only when the order
contains all universe records.

For G-0027, record 0 is validated as the zero signed core and therefore is the
5E/common-edge carrier already inside the 754,017-record denominator. With
`--include-five-l true`, 5L is source index 754,017; with `--include-target
true` as well, the target evaluation is index 754,018. Thus a complete report
names 754,018 source columns and 754,019 evaluated columns including target.

The tool prices only the named finite columns. A zero vector is a finite-family
null, never a MAX11 or unrestricted depth lower bound.
