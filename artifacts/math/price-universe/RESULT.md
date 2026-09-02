# RESULT — exact all-column pricing of rational separators

Bead: `relu-depth-frontier-research-max11-root-gmp.11`
Agent: `AzureAspen`
Date: 2026-09-02

## Outcome

`tools/priceuniverse` implements exact all-column separator pricing through
three ingress modes:

- exact `MCOLGEN1` batches with header modulus 0;
- saved n=9/n=10 JSONL systems; and
- the G-0027 universe generated in bounded chunks by the existing
  `max11-colgen` library.

Every rational separator is scaled to one positive common integer denominator.
Every column price uses checked `i128`; a weight, product, or sum that does not
fit is promoted to `BigInt`. Two independent modular accumulators at primes
1,000,003 and 1,000,033 must equal the final exact integer reduced modulo the
same prime on every evaluated column. The output is a JSONL list of nonzero
scaled prices, exact zero/nonzero counts with the evaluated-column denominator,
and a SHA-256 of the full ordered price vector, including zeros.

The frozen binary SHA-256 is
`e8eac3787edf91565ea27502712a4328433e1b82ff3dab19b71aced6c1fd9214`.
The implementation commits before this custody report are `8cfca48`,
`2dedb9e`, and `1b29f28`.

## G-0027 source/target counting convention

G-0027 has 754,017/754,017 serialized universe records. Record index 0 is
validated as the zero signed core and is the 5E/common-edge carrier already
inside that denominator. The synthetic 5L carrier is source index 754,017 and
has 11/11 linear coefficients equal to 18,144,000 with 0 hinge entries. Thus a
complete source family has 754,018/754,018 columns. The separately evaluated
target is index 754,018, so a source-plus-target pricing report has
754,019/754,019 evaluations.

For a final NON_MEMBER certificate, the required condition is zero price on
754,018/754,018 source columns and nonzero price on the 1/1 target. It is not
zero price on the target.

## Inputs and implementation hashes

- G-0027 universe SHA-256:
  `8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8`.
- n=9 saved system SHA-256:
  `729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991`.
- n=10 saved system SHA-256:
  `bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18`.
- n=9 `.8` separator SHA-256:
  `92fb25b388743d38e54c5d2b1c9c96d3184e7debe61ea93b46ebc1c1ea6cc9f5`.
- n=9 `+1/1` separator SHA-256:
  `06931186ae944263d28b9b0c42e1539b925ddd1d0ca53359679164889b5df6d1`.
- n=10 pivot report SHA-256:
  `fdba23baaa66ac08c84a96a2a7026b8ad5be30f8654e842d395940b1ad5a99de`.
- n=10 selected-row artifact SHA-256:
  `e13c4eeebdf54d862a6c25367c8d95755ddd773fff551da165975b03da25847f`.
- `src/lib.rs` / `src/main.rs` SHA-256:
  `47562fc5044b588182234e6d980dec05a44e395c9b44e2af1982df2b9f2fa41a` /
  `cd3cec940156704d9fc60cc0c7e779790b71430af8aabda29d892b744992a387`.
- `Cargo.toml` / `Cargo.lock` SHA-256:
  `db6e514e7f4ad216e69ecba10a3169cfdad6952776e8ee2e83a01db445073853` /
  `8f9f2f3af793e3513a92293c1f42a16243db2d709383a1f783941b87f2c06eba`.
- Exact control verifier SHA-256:
  `62f72eb3d39692e60d92c4baeb8def6d0c75e3011975c42bf1b9e12b46089801`.

Toolchain: rustc 1.95.0-nightly (`5c49c4f7c`, dated 2026-01-20), cargo
1.95.0-nightly (`85eff7c80`, dated 2026-01-15), Python 3.13.7, and
python-flint 0.9.0. All compute commands used at most 6 threads.

## Exact commands

Build and static/unit validation:

```bash
cargo fmt --manifest-path tools/priceuniverse/Cargo.toml
cargo clippy --release --manifest-path tools/priceuniverse/Cargo.toml -- -D warnings
cargo test --release --manifest-path tools/priceuniverse/Cargo.toml
cargo build --release --manifest-path tools/priceuniverse/Cargo.toml
source .venv/bin/activate
python -m py_compile tools/priceuniverse/*.py
```

n=9 positive, full-system pricing, and perturbed negative:

```bash
tools/priceuniverse/target/release/max11-price-universe price-saved \
  --input handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --separator artifacts/math/exact-leg-at-scale/n9_tree_exact_separator.json \
  --filter all \
  --violators artifacts/math/price-universe/n9_all_final_v2_violators.jsonl \
  --output artifacts/math/price-universe/n9_all_final_v2_report.json

tools/priceuniverse/target/release/max11-price-universe price-saved \
  --input handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --separator artifacts/math/exact-leg-at-scale/n9_tree_exact_separator.json \
  --filter union-trees \
  --violators artifacts/math/price-universe/n9_tree_final_v2_violators.jsonl \
  --output artifacts/math/price-universe/n9_tree_final_v2_report.json

tools/priceuniverse/target/release/max11-price-universe price-saved \
  --input handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --separator artifacts/math/exact-leg-at-scale/n9_tree_exact_separator_mutated_plus1.json \
  --filter union-trees \
  --violators artifacts/math/price-universe/n9_tree_mutant_final_v2_violators.jsonl \
  --output artifacts/math/price-universe/n9_tree_mutant_final_v2_report.json
```

n=10 codimension-one control and all-system pricing:

```bash
source .venv/bin/activate
python tools/priceuniverse/build_n10_codim1_control.py \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --pivot-report artifacts/math/exact-leg-at-scale/n10-sketch-m6498-p1000003.json \
  --selected-rows artifacts/math/exact-lift-35k/n10_selected_rows.json \
  --sketch-index 0 --drop-position -1 --primes 1000003,1000033 \
  --output artifacts/math/price-universe/n10_codim1_separator.json \
  --report artifacts/math/price-universe/n10_codim1_build_report.json

tools/priceuniverse/target/release/max11-price-universe price-saved \
  --input handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --separator artifacts/math/price-universe/n10_codim1_separator.json \
  --filter all \
  --violators artifacts/math/price-universe/n10_codim1_final_v2_violators.jsonl \
  --output artifacts/math/price-universe/n10_codim1_final_v2_price_report.json

python tools/priceuniverse/verify_known_controls.py \
  --n9-system handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --n9-all-report artifacts/math/price-universe/n9_all_final_v2_report.json \
  --n9-all-violators artifacts/math/price-universe/n9_all_final_v2_violators.jsonl \
  --n9-tree-report artifacts/math/price-universe/n9_tree_final_v2_report.json \
  --n9-mutant-report artifacts/math/price-universe/n9_tree_mutant_final_v2_report.json \
  --n10-build-report artifacts/math/price-universe/n10_codim1_build_report.json \
  --n10-separator artifacts/math/price-universe/n10_codim1_separator.json \
  --n10-price-report artifacts/math/price-universe/n10_codim1_final_v2_price_report.json \
  --n10-violators artifacts/math/price-universe/n10_codim1_final_v2_violators.jsonl \
  --output artifacts/math/price-universe/known_controls_final_v3_verification.json
```

MCOLGEN1/direct-ingress parity and n=11 throughput:

```bash
source .venv/bin/activate
python tools/priceuniverse/make_n11_benchmark_separator.py \
  --source artifacts/math/exact-leg-at-scale/n9_tree_exact_separator.json \
  --output artifacts/math/price-universe/n11_benchmark_separator.json

tools/colgen/target/release/max11-colgen emit-universe \
  --universe artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --threads 6 --format binary --output /tmp/azureaspen-gmp11-first8.mcolgen \
  --start 0 --limit 8

tools/priceuniverse/target/release/max11-price-universe price-mcolgen \
  --input /tmp/azureaspen-gmp11-first8.mcolgen \
  --separator artifacts/math/price-universe/n11_benchmark_separator.json \
  --violators artifacts/math/price-universe/n11_first8_mcolgen_final_v2_violators.jsonl \
  --output artifacts/math/price-universe/n11_first8_mcolgen_final_v2_report.json

tools/priceuniverse/target/release/max11-price-universe price-universe \
  --universe artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --separator artifacts/math/price-universe/n11_benchmark_separator.json \
  --threads 6 --start 0 --limit 8 \
  --violators artifacts/math/price-universe/n11_first8_direct_final_v2_violators.jsonl \
  --output artifacts/math/price-universe/n11_first8_direct_final_v2_report.json

python tools/priceuniverse/verify_ingress_parity.py \
  --mcolgen-input /tmp/azureaspen-gmp11-first8.mcolgen \
  --mcolgen-report artifacts/math/price-universe/n11_first8_mcolgen_final_v2_report.json \
  --direct-report artifacts/math/price-universe/n11_first8_direct_final_v2_report.json \
  --mcolgen-violators artifacts/math/price-universe/n11_first8_mcolgen_final_v2_violators.jsonl \
  --direct-violators artifacts/math/price-universe/n11_first8_direct_final_v2_violators.jsonl \
  --output artifacts/math/price-universe/n11_first8_final_v2_ingress_parity.json

tools/priceuniverse/target/release/max11-price-universe price-universe \
  --universe artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --separator artifacts/math/price-universe/n11_benchmark_separator.json \
  --threads 6 --start 0 --limit 5000 \
  --violators artifacts/math/price-universe/n11_first5000_final_v2_violators.jsonl \
  --output artifacts/math/price-universe/n11_first5000_final_v2_report.json

python tools/priceuniverse/project_benchmark.py \
  --report artifacts/math/price-universe/n11_first5000_final_v2_report.json \
  --universe-records 754017 \
  --output artifacts/math/price-universe/n11_full_final_v2_projection.json
```

The arbitrary order control used the exact order `[7,3,0]` from
`n11_order_7_3_0.json`; the violator list preserved 3/3 indices in that order.
The carrier control used the 2-record `n11_tiny_universe.json`, then appended
5L and target; it evaluated source indices `[0,1,2]` and target index `[3]`,
4/4 in total.

## Known-answer controls

### n=9 tree separator, positive and mutation

The exact `.8` separator has common denominator
97364603919803580258999820726850424198374075481730015590022192032000190525263857818256419814883341618118281361505947077011539873831487543592990587085504321910697890637689380372169009647347232743227946520019600.
It annihilated 739/739 union-tree columns. The `+1/1` mutation gave nonzero
prices on 739/739 of the same columns. Exact/modular agreement was 739/739 at
prime 1,000,003 and 739/739 at prime 1,000,033 in both directions.

Over the full 10,976-column saved system, 10,236/10,976 prices were nonzero and
740/10,976 were zero. The extra zero was source index 495. The exact integer
rank over Q was 360 for the 739-column tree matrix and remained 360 after
adjoining source 495 as column 740/740. The same ranks were 360/739 and
360/740 at each named prime. Thus all 10,236/10,976 nonzero-priced columns are
outside the exact tree span, while the one non-tree zero is inside it.

The full ordered exact price-vector SHA-256 is
`9e0cfa35528b9bd77f06d9d2926943d9ab210568a5ace7988e5161304011d1b8`.
The combined exact-control report SHA-256 is
`86dcf597efecb5ed98951b23878e20e300f0b137bb93e9062fda30ad1621f420`.

### n=10 proper-subfamily rank deficit

The verified full pivot minor has rank 2,166/2,166. Removing pivot position
2,165/2,166, source index 12,153/12,248, gives a proper subfamily of
2,165/2,166 pivot columns and rank 2,165/2,165 at both named primes. The exact
solve `M^T y=e_drop` took 12.181017275899649 seconds for the 2,166-row minor,
peaked at 1,289,780 KiB, and produced 508/16,709 nonzero hinge weights plus
0/10 nonzero linear weights, with common denominator 276,480.

Pricing all 12,248/12,248 saved columns gave 12,247/12,248 exact zeros and
exactly 1/12,248 violator: dropped source 12,153, with scaled price
276,480/276,480 = 1. All 2,165/2,165 retained pivot columns priced zero.
Because their exact span has codimension 1/2,166 inside the rank-2,166 span,
zero price is exactly membership in that proper-subfamily span. Modular/exact
agreement was 12,248/12,248 at each named prime. The ordered price-vector
SHA-256 is
`c1f07f94b36511f71dbab7c7db66f49250359095ab7ab0ef34d876812726f182`.

## MCOLGEN1 parity, overflow, and output controls

The transient exact MCOLGEN1 input had 8/8 records, 11,660 bytes, and SHA-256
`ca5a0e5bc291372e416fb7e017ce90c8f760ec27422e134dcf37bdc031b723b2`.
It is not committed because it is deterministically regenerated by the command
above. MCOLGEN1 pricing and direct `max11-colgen` reuse produced byte-identical
violator JSONL and the same 8/8 exact price-vector SHA-256
`bd98fd57443b96f90957272b45700fa7d49a974c78812bf91ec9ddab958538ea`.
Exact/modular agreement was 8/8 at both named primes.

The unit overflow plant multiplies `(i128::MAX-1)` by 3/1. Checked `i128`
refuses the product, promotes it to `BigInt`, and returns the exact integer.
In the real n=11 timing control, all 5,000/5,000 columns exercised the BigInt
path. No overflow is truncated or wrapped.

The canonical `MPRICEV1` hash commits, in order, to `n`, common denominator,
every source index, every signed arbitrary-precision scaled price including
zero, and the evaluated-column count. The violator JSONL separately lists
each nonzero source index and scaled integer price; the report hash-binds that
file and supplies the one common denominator.

## n=11 5,000-column timing and full-pass projection

The throughput separator is explicitly synthetic: 722/722 padded n=9 hinge
weights plus 11/11 n=11 linear slots, chosen to exercise large rational
arithmetic. It is not a stage-A separator and has no mathematical standing for
MAX11.

On the first 5,000/754,017 G-0027 records with 6 threads:

- total time: 112.102711509 seconds / 5,000 columns;
- colgen time: 98.72524070799993 seconds / 5,000 columns;
- exact pricing plus JSONL/hash time: 13.377470801000072 seconds / 5,000 columns;
- throughput: 5,000 columns / 112.102711509 seconds =
  44.60195416056981 columns/second;
- peak RSS: 660,496 KiB = 0.6298980712890625 GiB / 6 GiB cap;
- BigInt promotion: 5,000/5,000 columns;
- exact/modular agreement: 5,000/5,000 at each named prime;
- exact price-vector SHA-256:
  `4c30b5bb18cb25e60291165dfe8f273c28ea255a426bc0c2326f961c5539e259`.

Linear projection from that 5,000-column denominator, not a measured full
pass:

| evaluated denominator | projected total | projected colgen |
|---:|---:|---:|
| 754,017 records | 16,905.47004477633 s = 4.695963901326759 h | 14,888.101964584797 s = 4.135583879051333 h |
| 754,018 sources including 5L | 16,905.49246531863 s = 4.695970129255175 h | 14,888.121709632938 s = 4.135589363786927 h |
| 754,019 evaluations including target | 16,905.514885860935 s = 4.695976357183593 h | 14,888.141454681081 s = 4.135594848522523 h |

The benchmark report SHA-256 is
`ddf268f68f51bc9ea55ec662f8a41963a867c9d00ce202750ffef8c9b7e862e2`;
the projection artifact SHA-256 is
`30677e7b97cd045779dd117aec72d63733fe2ae5d452ad02283d1232b1d6f4d1`.

## Validation

- Rust unit tests: 4/4 PASS, including checked overflow promotion and exact
  5L/target conventions.
- `cargo clippy --release -- -D warnings`: 0 warnings / 1 crate.
- Python control scripts: 5/5 compile with Python 3.13.7.
- Known-answer controls: PASS in
  `known_controls_final_v3_verification.json`, SHA-256
  `86dcf597efecb5ed98951b23878e20e300f0b137bb93e9062fda30ad1621f420`.
- MCOLGEN1/direct ingress parity: PASS in
  `n11_first8_final_v2_ingress_parity.json`, SHA-256
  `d8a857af1b17051eecd92cb47f8c7180b88037addd031f07acb2911d73c6d4b9`.
- No committed file exceeds the 50,000,000-byte policy cap; the largest
  committed bead artifact is 2,615,577/50,000,000 bytes.

`./skill-runtime verify-quick` reported only the campaign's known
pre-existing SE-10 finding on G-0015; this bead does not edit the ledger or
G-0015.

## No claim

No stage-A n=11 NON_MEMBER separator was available or priced in this bead. The
5,000-column run uses a synthetic separator-shaped timing input and covers only
5,000/754,017 G-0027 records. The three full-pass times are projections, not
runs. The n=9 and n=10 results are known-answer controls on finite saved
systems. Nothing here establishes MAX11 membership, MAX11 nonmembership, or an
unrestricted depth lower bound. A real family null still requires the actual
lifted n=11 separator to price zero on every one of 754,018/754,018 source
columns, nonzero on the 1/1 target, with the resulting full vector and
violator list exact-verified and hash-bound.
