# n=12 loopless signed-W degree-five universe

This directory contains the complete finite orbit denominator for loopless
degree-five signed graphs `W=B-A` on at most 12 active coordinates, modulo
coordinate relabeling and global sign/branch reversal. It parameterizes the
frozen G-0027 incidence-graph method without changing G-0027.

## Files

| file | role | SHA-256 |
|---|---|---|
| `loopless_signed_degree5_universe_n12_v1.json.gz` | 787,523-record colgen-compatible universe | `f98352ea4d1517f0b88aba0b38d34be0edb0b845aac3eaa724f3bd1f8f83f640` |
| `loopless_signed_degree5_universe_n12_manifest_v1.json` | marginal and joint strata, controls, custody | `cdd9dbdcad7aae6d63b4b49309e3aeeb6cd401fdb9a5a17fe13dbc4315ad544c` |
| `stage_a_order_n12_v1.json` | plain index list: record 0, then `s=5, beta<=1` | `691cb0368545f8834c98e891bbb771476e547ce9e140887c9791710a8786a7c1` |
| `loopless_signed_degree5_universe_n11_replay_v1.json.gz` | same-code n=11 replay | `92ee9f255fc99557ea67c85edc80b9151c7c9d7bb7417d26d614b89f7881e562` |
| `loopless_signed_degree5_universe_n11_replay_manifest_v1.json` | exact G-0027 comparison | `158b9a87bb140b3112b9216fa9446fba33d5bcc0fbe6fc14ca4a39876c1560e7` |
| `colgen_benchmark_n12_200_v1.json` | deterministic four-thread benchmark | `5a866707e2105852f4d1ef96f06b6bdd0d47a0fbbab19fe3a5f171870c6d97eb` |
| `verification_v2.json` | final full-record and current-binary verification | `e1e63830285716a9f0ed44bdce13c6c5e53d64f2bc8c531c49a1c7e10d6ea4b0` |

The universe gzip is 4,116,936 bytes; every file in this bead is below the
50 MB commit ceiling.

## Counts

| signed mass | records / 787,523 |
|---:|---:|
| 0 | 1 / 787,523 |
| 1 | 2 / 787,523 |
| 2 | 28 / 787,523 |
| 3 | 543 / 787,523 |
| 4 | 17,867 / 787,523 |
| 5 | 769,082 / 787,523 |

The full beta, component, multiplicity, and joint topology tables are in the
manifest. The only new active-support strata relative to n=11 are 1 record at
`s=3,r=12`, 155 at `s=4,r=12`, and 33,350 at `s=5,r=12`, totalling
33,506/787,523 records.

The stage-A order has 148,628/787,523 indices: record 0 first, then
148,627/787,522 nonzero records satisfying `s=5, beta<=1`. Record 0 generates
the 5E carrier. 5L is not a universe index; pass `--include-five-l true` to
`tools/colgen`, which appends it at source index 787,523.

## Simple pairs versus simple W

Exact Burnside counting gives 490,480/490,480 raw unordered pairs of simple
five-edge graphs modulo `S_12` and branch swap. Signed-W cancellation maps
these surjectively, not injectively, to 264,791 reachable simple-W orbits:
264,790 records of exact maximum multiplicity one plus the `W=0` record.

Surjectivity is constructive. For a simple W of signed mass `s`, choose
`5-s` loopless edges outside its `2s`-edge support and add them to both sides;
for `W=0`, choose any simple five-edge graph for both sides. The verifier
replays this construction on 264,791/264,791 records. The difference
490,480 - 264,791 = 225,689 counts raw orbit classes beyond the number of W
orbit classes; it is not a uniform fiber size.

## Commands

Run from the repository root:

```bash
source .venv/bin/activate

python artifacts/math/n12-universe/enumerate_loopless_signed_w.py \
  --n 11 --branch-edges 5 \
  --reference-g0027 artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --output artifacts/math/n12-universe/loopless_signed_degree5_universe_n11_replay_v1.json.gz \
  --manifest artifacts/math/n12-universe/loopless_signed_degree5_universe_n11_replay_manifest_v1.json

python artifacts/math/n12-universe/enumerate_loopless_signed_w.py \
  --n 12 --branch-edges 5 \
  --output artifacts/math/n12-universe/loopless_signed_degree5_universe_n12_v1.json.gz \
  --manifest artifacts/math/n12-universe/loopless_signed_degree5_universe_n12_manifest_v1.json \
  --stage-order artifacts/math/n12-universe/stage_a_order_n12_v1.json

source scripts/activate-toolchain.sh
CARGO_BUILD_JOBS=4 cargo build --release --manifest-path tools/colgen/Cargo.toml
tools/colgen/target/release/max11-colgen benchmark \
  --universe artifacts/math/n12-universe/loopless_signed_degree5_universe_n12_v1.json.gz \
  --sample-size 200 --seed 2026090215 --threads 4 \
  --output artifacts/math/n12-universe/colgen_benchmark_n12_200_v1.json

python artifacts/math/n12-universe/verify_outputs.py
```

The verifier recomputes every serialized record invariant and record-stream
hash, all marginal counts, all simple-W lifts, the stage order, four Burnside
known answers, two planted duplicate rejections, five colgen unit tests, a
four-column current-binary smoke, and the exact 5E/5L carrier convention.

## No claim

This is a finite universe census and producer benchmark. It does not establish
MAX_12 membership or non-membership, a span rank, an exact network identity,
or completeness for arbitrary two-hidden-layer ReLU representations.
