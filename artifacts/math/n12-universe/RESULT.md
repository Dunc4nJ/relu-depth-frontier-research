# relu-depth-frontier-research-max11-root-gmp.15 — RESULT

## Outcome

PASS. The complete n=12 loopless degree-five signed-W orbit universe contains
787,523/787,523 records in the G-0027 record schema. The n=12 stage-A order
contains 148,628/787,523 universe indices; `tools/colgen --include-five-l true`
adds the separate 5L carrier as one further column.

The producer is `enumerate_loopless_signed_w.py`, SHA-256
`b268941eda8a13f9e0eef05f7e8c1c8e2d67dee384731dd620daefc2cd4942f7`.
It parameterizes, without editing, G-0027's nauty absolute-incidence-graph
enumeration and pynauty signing-orbit engine. Every record has exactly the six
G-0027 mathematical fields: `active_vertices`, `signed_mass`,
`negative_edges`, `positive_edges`, `abs_components`, and `abs_beta`.

## Input custody

| input | SHA-256 |
|---|---|
| G-0027 n=11 universe | `8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8` |
| G-0027 producer | `92ce1d017a12ce9dc44c3f43103028dcfe635fa7ba9e8c1026c3d6ca8fe19f13` |
| Existing simple-pair Burnside probe | `0f6a0416ac8a421c39139b10773a3a92965058afcea92aa794cbeb63b99b8a0d` |
| `tools/colgen/src/lib.rs` | `81f6618d57c09fb1694f0b97a4e493853193f48249ddde5a7b612e795a850eb5` |
| `tools/colgen/src/main.rs` | `c7a40f0381e2085888470a101e74fdfabcf4cf0e113c811729214edb4a9cce6b` |
| Local release colgen executable | `276ddb8f18b2b77451dc57e2019f3d98e519b42db27bce873c0c8106e2c0a00b` |

The local executable is rebuildable and is not committed. No file under
`tools/colgen` was edited by this bead.

## n=11 same-code reproduction

The same parameterized code produced 754,017/754,017 records. The canonical
per-record stream SHA-256 is
`5fc1b608612ca4668e772a9234a8795f12f17a746392ffdf492e8888548cc541`,
identical to frozen G-0027. It reproduced:

- 41/41 signed-mass/active-support strata;
- 85/85 `(s,r,components,beta)` topology rows;
- signed-mass counts `1, 2, 28, 542, 17,712, 735,732` over the
  754,017-record denominator;
- maximum-multiplicity counts `1, 243,467, 436,335, 67,265, 6,457, 492`
  over the same 754,017 records.

The replay gzip SHA-256 is
`92ee9f255fc99557ea67c85edc80b9151c7c9d7bb7417d26d614b89f7881e562`;
its differing outer-file hash reflects added gmp.15 census/control metadata,
not a differing record stream.

## n=12 universe and strata

Universe: `loopless_signed_degree5_universe_n12_v1.json.gz`, 4,116,936 bytes,
SHA-256
`f98352ea4d1517f0b88aba0b38d34be0edb0b845aac3eaa724f3bd1f8f83f640`.
The canonical per-record stream SHA-256 is
`800e832d2a3c40d65a5b2351c889ec955a6c313b05f81b6b6a899d76da6dd10a`.

All counts below name the 787,523-record denominator.

| signed mass | records / 787,523 |
|---:|---:|
| 0 | 1 / 787,523 |
| 1 | 2 / 787,523 |
| 2 | 28 / 787,523 |
| 3 | 543 / 787,523 |
| 4 | 17,867 / 787,523 |
| 5 | 769,082 / 787,523 |

The direct record recount matched the producer counters in every mass stratum,
including all 18,441/787,523 records with `s<=4`.

| abs beta | records / 787,523 |
|---:|---:|
| 0 | 25,059 / 787,523 |
| 1 | 131,147 / 787,523 |
| 2 | 245,962 / 787,523 |
| 3 | 232,698 / 787,523 |
| 4 | 118,214 / 787,523 |
| 5 | 30,617 / 787,523 |
| 6 | 3,646 / 787,523 |
| 7 | 176 / 787,523 |
| 8 | 4 / 787,523 |

| abs components | records / 787,523 |
|---:|---:|
| 0 | 1 / 787,523 |
| 1 | 485,632 / 787,523 |
| 2 | 229,910 / 787,523 |
| 3 | 62,371 / 787,523 |
| 4 | 9,086 / 787,523 |
| 5 | 513 / 787,523 |
| 6 | 10 / 787,523 |

| maximum absolute edge multiplicity | records / 787,523 |
|---:|---:|
| 0 | 1 / 787,523 |
| 1 | 264,790 / 787,523 |
| 2 | 447,961 / 787,523 |
| 3 | 67,803 / 787,523 |
| 4 | 6,475 / 787,523 |
| 5 | 493 / 787,523 |

The full joint `(s,r,components,beta,max multiplicity)` table is in the
48,252-byte manifest, SHA-256
`cdd9dbdcad7aae6d63b4b49309e3aeeb6cd401fdb9a5a17fe13dbc4315ad544c`.

Relative to n=11, n=12 adds precisely 33,506/787,523 records supported on all
12 coordinates: 1 at signed mass 3, 155 at signed mass 4, and 33,350 at signed
mass 5. No lower-support record changes.

## Burnside and simple-W relation

The independently transcribed exact Burnside calculation passed 4/4 known
answers:

| subject | raw simple graph-pair orbits / expected |
|---|---:|
| n=5,k=2 | 19 / 19 |
| n=6,k=2 | 25 / 25 |
| n=11,k=5 | 462,627 / 462,627 |
| n=12,k=5 | 490,480 / 490,480 |

For n=12, the Burnside numerator is 469,881,409,536,000 over group-order
denominator 958,003,200. Its fixed-without-swap contribution is
467,431,795,353,600/469,881,409,536,000 and its swap-coset contribution is
2,449,614,182,400/469,881,409,536,000. Omitting the swap coset is rejected by
1/1 mutation control.

The 490,480 raw simple-pair orbits are **not** the number of simple-W orbits.
Common-edge cancellation gives a surjective, noninjective map to
264,791/787,523 reachable simple-W records: 264,790 exact-multiplicity-one
records plus the one `W=0` record. For every such W of mass `s`, the verifier
chooses `5-s` unused edges and constructs two simple five-edge branches whose
difference is W. This passed 264,791/264,791 records. The raw orbit-count
excess is 490,480 - 264,791 = 225,689; it is not a uniform fiber cardinality.

## Stage-A order and carriers

`stage_a_order_n12_v1.json` is a plain JSON list, 1,486,278 bytes, SHA-256
`691cb0368545f8834c98e891bbb771476e547ce9e140887c9791710a8786a7c1`.
It contains 148,628/787,523 unique in-range indices:

- index 0 first, the 5E/zero-W carrier;
- then exactly 148,627/787,522 nonzero records with `s=5` and `beta<=1`;
- no other indices.

5L is not a signed-W universe record. The exact current-binary gate invoked
`--order-file [0] --include-five-l true`: it emitted 2/2 carrier columns. The
5L source index is 787,523, its hinge count is 0, and all 12/12 linear
coordinates equal `5*11! = 199,584,000`. A planted duplicate stage index was
rejected 1/1.

Thus a stage-A colgen stream using this order plus 5L contains
148,629/148,629 columns.

## Colgen benchmark

The registered deterministic sample is 200/787,523 records, SplitMix64 seed
2,026,090,215, sample-index SHA-256
`f4482e123eab567680775e2813601bbf6c6c359df1df7690314a4451d8808d7d`.
At 4/4 threads on this host:

- 200/200 columns completed in 70.278820746 seconds wall;
- throughput was 2.8458075687245117 columns/second;
- measured cost was 1.40557641492 core-seconds/column;
- retained hinges over the 200-column denominator: minimum 1,458, median
  71,349, p90 164,264, p99 229,423, maximum 303,463;
- total retained hinges were 17,475,092/200 columns, mean 87,375.46 per column;
- peak RSS was 1,295,332/8,388,608 KiB under the bead's 8 GiB ceiling.

For context, the pinned n=11 v3 colgen benchmark measured
0.280766653782 core-seconds/column on a different 1,000-record sample at six
threads. The n=12/n=11 core-cost ratio is 5.0062085, not the anticipated 10x;
this is an indicative cross-sample comparison, not a paired benchmark.

Ideal-linear four-thread projections from the n=12 sample are
276,731.290 seconds = 76.870 hours for all 787,523 records plus 5L, and
52,227.354 seconds = 14.508 hours for the 148,628-index stage-A order plus 5L.
Neither projected pass was run.

## Verification and controls

`verify_outputs.py`, SHA-256
`c505b209c33332c781265e4b0ab628f33186f0ecc93d82f13de1ca82b6ffd9ba`,
performed a full independent pass over both serialized universes. Final result:

- n=11 record invariants/hash/uniqueness: 754,017/754,017;
- n=12 record invariants/hash/uniqueness: 787,523/787,523;
- simple-W reconstruction: 243,468/243,468 at n=11 and 264,791/264,791 at n=12;
- stage order: 148,628/148,628 selected indices;
- planted record and order duplicates: 2/2 rejected;
- `tools/colgen` release unit tests: 5/5;
- current release binary smoke: 4/4 n=12 columns;
- exact 5E/5L current-binary carrier check: 2/2.

The final verifier ran in 120.15 seconds at 1,927,968/8,388,608 KiB peak RSS.
Its report is `verification_v2.json`, SHA-256
`e1e63830285716a9f0ed44bdce13c6c5e53d64f2bc8c531c49a1c7e10d6ea4b0`.
The pre-carrier `verification_v1.json` is retained as a prior successful trial,
not treated as the final gate.

The final `./skill-runtime verify-quick` completed its walkers but exited 1 on
the campaign's pre-existing SE-10 finding for `ledger/gaps.toml` G-0015
(`changed obligation`, still attributed there to commit `7cf9d50deb61`). This
is the known finding named in `AGENTS.md`; this bead did not edit or attempt to
repair any ledger path.

## Exact commands

```bash
source .venv/bin/activate
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
/usr/bin/time -v python artifacts/math/n12-universe/enumerate_loopless_signed_w.py \
  --n 11 --branch-edges 5 \
  --reference-g0027 artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --output artifacts/math/n12-universe/loopless_signed_degree5_universe_n11_replay_v1.json.gz \
  --manifest artifacts/math/n12-universe/loopless_signed_degree5_universe_n11_replay_manifest_v1.json

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
/usr/bin/time -v python artifacts/math/n12-universe/enumerate_loopless_signed_w.py \
  --n 12 --branch-edges 5 \
  --output artifacts/math/n12-universe/loopless_signed_degree5_universe_n12_v1.json.gz \
  --manifest artifacts/math/n12-universe/loopless_signed_degree5_universe_n12_manifest_v1.json \
  --stage-order artifacts/math/n12-universe/stage_a_order_n12_v1.json

source scripts/activate-toolchain.sh
CARGO_BUILD_JOBS=4 cargo test --release --manifest-path tools/colgen/Cargo.toml
CARGO_BUILD_JOBS=4 cargo build --release --manifest-path tools/colgen/Cargo.toml
/usr/bin/time -v tools/colgen/target/release/max11-colgen benchmark \
  --universe artifacts/math/n12-universe/loopless_signed_degree5_universe_n12_v1.json.gz \
  --sample-size 200 --seed 2026090215 --threads 4 \
  --output artifacts/math/n12-universe/colgen_benchmark_n12_200_v1.json

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
/usr/bin/time -v python artifacts/math/n12-universe/verify_outputs.py \
  --write-report artifacts/math/n12-universe/verification_v2.json

# Subsequent fail-closed replay; validates the stored v2 report without overwrite
python artifacts/math/n12-universe/verify_outputs.py
```

## Trials and resource accounting

- The first n=11 mathematical enumeration completed all 754,017 intended
  records but then hit a relative-path reporting exception before emitting any
  artifact. It ran for 82.17 seconds and peaked at 2,251,196/8,388,608 KiB RSS.
  Path normalization was fixed and the entire enumeration—not merely the
  failed tail—was rerun.
- The successful n=11 replay took 134.40 seconds and peaked at
  2,251,424/8,388,608 KiB RSS. The successful n=12 enumeration took 130.67
  seconds and peaked at 1,821,940/8,388,608 KiB RSS.
- The first full verifier passed before the explicit 5L runtime gate was added;
  it is preserved as `verification_v1.json`. The complete v2 verifier reran all
  preceding checks and added the 2/2 carrier gate.
- Every launched command used at most 4/4 threads. No bead file exceeds 50 MB;
  both universe gzip files are committed with their SHA-256 values.

## What was not verified

- No n=12 rank, modular membership test, exact lift, separator, or full
  148,629-column stage-A generation was run.
- The 490,480 count is for raw simple graph-pair orbits; it is not a signed-W
  record count. The finite constructive image count is 264,791/264,791.
- Orbit completeness is for the loopless degree-five signed-W quotient only.
  It does not cover loops, non-pairwise first-layer neurons, higher degree, or
  arbitrary two-hidden-layer representations.

## No-claim line

This finite census and benchmark say nothing about whether MAX_12 belongs to
the n=12 stage-A span, the full loopless signed-W span, or the unrestricted
two-hidden-layer ReLU class.
