# relu-depth-frontier-research-max11-root-gmp.13 — RESULT

## Outcome

PASS for the requested producer and validation scope. `tools/colgen-loops` is a
separate Rust crate depending on `tools/colgen` as `max11-colgen`; no file under
`tools/colgen` was edited. It emits exact-integer or modular sparse columns as
JSONL or `MCOLGEN1`, including a bounded-memory `emit-universe` path that reads
G-0038 directly in batches of `2 * threads`. The crate caps threads at 4/4.

The defining loop increment is exact:

```text
d_rank = W[v,v] + sum(W[v,u] for u already placed).
```

Consequently `(v,v)` contributes the bare coordinate `x_v` and can produce a
retained direction with `d_0 != 0`. Canonical G-0038 rows use zero common-loop
padding; remaining cancelled mass is padded by common nonloops. The separate
5E and 5L emitters cover the two carrier atoms requested by the bead.

## Frozen inputs and custody

- G-0038 gzip: SHA-256
  `e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd`,
  78,769,863 compressed bytes, 7,015,841/7,015,841 orbit records.
- G-0038 manifest: SHA-256
  `1d6d7ce58c4302b899e922939030706428c54870d32cc5b0e60f43e2c25ee640`.
- Prior loop-aware Python DP: SHA-256
  `4b8afc3db48aa65976ff5123b7e817150ca7edc66563938068a99f15331eab6a`.
- Upstream n=5 certificate: SHA-256
  `698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694`.
- Upstream n=7 certificate: SHA-256
  `b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be`.
- Final Rust library source: SHA-256
  `c85934720ec50f30b2b5f672167005f93e6cc76e5c594e61020839f60c93fbfd`.
- Final Rust CLI source: SHA-256
  `86d83761cdaebe44efd12cf166e3d2f4b52b1b32fb09c658b4822ccffd90ce0b`.
- Final local release executable used by the fast current-binary control:
  SHA-256
  `1e27b6216a97e5e460c743a4715fa0bbb925250384ca9eee3c1959861c310fb3`.
  The executable is a rebuildable local file and is not committed.

The complete audit reproduced 46/46 manifest strata, the framed uncompressed
SHA-256
`89ffe6d0f8aec9fb0ef8d91c5f15b75c89a6bd0d5bdd5b554c155f5c18e177cd`,
and orbit-only SHA-256
`e49035b2700272f6edc1d1792bbceb0d5811a870820dd982d67a243b79423ef5`.

Counts by signed mass, each over the 7,015,841-record denominator:

| signed mass | records / 7,015,841 |
|---:|---:|
| 0 | 1 / 7,015,841 |
| 1 | 5 / 7,015,841 |
| 2 | 107 / 7,015,841 |
| 3 | 3,198 / 7,015,841 |
| 4 | 134,193 / 7,015,841 |
| 5 | 6,878,337 / 7,015,841 |

Counts by total uncancelled signed-loop occurrences, again over 7,015,841:

| loops | records / 7,015,841 |
|---:|---:|
| 0 | 754,017 / 7,015,841 |
| 1 | 1,805,136 / 7,015,841 |
| 2 | 2,026,736 / 7,015,841 |
| 3 | 1,413,037 / 7,015,841 |
| 4 | 686,507 / 7,015,841 |
| 5 | 246,170 / 7,015,841 |
| 6 | 67,098 / 7,015,841 |
| 7 | 14,376 / 7,015,841 |
| 8 | 2,428 / 7,015,841 |
| 9 | 308 / 7,015,841 |
| 10 | 28 / 7,015,841 |

Thus 6,261,824/7,015,841 records are loop-bearing and
754,017/7,015,841 are loopless.

## Known-answer controls

All identities and column equalities below are exact integer/rational checks;
none uses floating-point equality.

| gate | result / denominator | detail |
|---|---:|---|
| Upstream MAX identities | 2 / 2 | Exact rational identity on every sparse row for n=5 and n=7. |
| DP versus literal S_n | 60 / 60 templates | n=5: 3/3 templates with 120/120 permutations per template; n=7: 57/57 with 5,040/5,040 permutations per template. |
| Loop-bearing certificate templates | 59 / 60 | The finite upstream-certificate template set, not every template at n<=7. |
| Certificate diagonal-sign mutants | 2 / 2 rejected | One complete-identity mutant gate per certificate. |
| Explicit minimum-coordinate control | 1 / 1 | Synthetic loop/nonloop pair matches literal S_5 and retains 7 d_0 hinges; 46/60 certificate templates also retain at least one d_0 hinge. |
| Python DP random samples | 2,000 / 2,000 columns | 1,000/1,000 loop-bearing records at n=9 and 1,000/1,000 at n=10. Full sparse linear and hinge maps agree. |
| Loopless native/dependency parity | 1,000 / 1,000 columns | Uniform sample from the 754,017-record loopless stratum at n=11. |
| Loopless production/dependency parity | 1,000 / 1,000 columns | Production additionally delegates every accepted zero-common-loop loopless row directly to `max11-colgen`; the 1,000/1,000 count is the empirical native-DP control. |
| Exact/modular MCOLGEN1 replay | 16 / 16 columns | Residues at denominator prime 1,000,003; header, indices, linear rows, directions, and hinge coefficients checked. |
| Carrier atoms | 2 / 2 exact and 2 / 2 modular | 5E minimum-coordinate linear coefficient 0; 5L coefficient 18,144,000. Denominator prime 1,000,003 for modular replay. |
| Final executable prefix control | 8 / 8 columns | Frozen G-0038 prefix: Python DP equality 8/8, streaming/direct byte equality 8/8, modular equality 8/8 at denominator prime 1,000,003. |
| Planted final coefficient mutant | 1 / 1 rejected | Modular sparse-column coefficient mutation. |
| Audit validator self-test | 1 / 1 positive; 2 / 2 mutants | Wrong loop count and opposite-sign overlap are rejected; reservoir denominator 3/3. |
| Verifier denominator mutant | 1 / 1 rejected | A 7,015,840/7,015,841 record-count report cannot pass. |
| Rust unit tests | 5 / 5 | Includes native/literal, loopless dependency, carrier, modular, and diagonal-sign mutant gates. |

The deterministic sample hashes are:

| sample | records / eligible denominator | SHA-256 |
|---|---:|---|
| n=11 benchmark | 1,000 / 7,015,841 | `5b1e373e911673460598ed46d053e36f8b0f06bf250c73f7a639304ae512dfe3` |
| n=11 loopless | 1,000 / 754,017 | `39601c0e2322c793ed885ba35d721621f35adeb19727d144490b5dc9dd992c0d` |
| n=9 Python DP | 1,000 / 5,213,489 eligible loop-bearing rows | `c37d70e8d8938a13b9cca069dbc83961056c7afc857bde8e4703f98344ebc390` |
| n=10 Python DP | 1,000 / 5,958,788 eligible loop-bearing rows | `e3c95e261dfa47c827d6b492987fe0f1c205df83fda03b9bf68924b60b7ee51d` |

## Benchmark

The final four-thread run generated 1,000/1,000 deterministic n=11 records in
127.483699132 seconds, or 7.844140127786639 columns/second on this host. It
measured 0.509934796528 core-seconds/column. The sample contained
890/1,000 loop-bearing rows.

For the explicitly requested 7,015,841 records plus 2/2 carrier columns, the
projected denominator is 7,015,843 columns. Ideal-linear projections from this
single sample are:

| concurrency | projected wall time / 7,015,843 columns |
|---:|---:|
| 4 threads | 894,405.618 seconds = 248.446 hours = 10.352 days |
| 24 vCPU | 149,067.603 seconds = 41.408 hours |
| 64 vCPU | 55,900.351 seconds = 15.528 hours |

The 24-vCPU and 64-vCPU values are arithmetic ideal-scaling projections, not
measured passes. Retained hinge counts on the 1,000-column denominator were:
minimum 486/column, median 36,150/column, p90 85,087/column, p99
133,937/column, maximum 185,776/column, and 43,115,692/1,000 total hinges.
Minimum-coordinate hinges occurred in 886/1,000 columns and accounted for
14,874,910/43,115,692 retained hinges.

The first reporting-version benchmark on the same 1,000/1,000 sample peaked at
689,568 KiB RSS. The final reporting-only rerun did not preserve its `/usr/bin/time`
stderr, so no final-run peak is claimed. Both used 4/4 threads.

## Exact commands

All commands were run from the repository root after
`source scripts/activate-toolchain.sh`, except Rust commands whose shown working
directory is `tools/colgen-loops`.

```bash
# Complete G-0038 audit, census replay, and deterministic reservoirs
/usr/bin/time -v python artifacts/math/colgen-loops/audit_universe.py \
  --universe artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz \
  --manifest artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_manifest_v1.json \
  --output-dir artifacts/math/colgen-loops --sample-size 1000 --seed 2026090213

# Upstream certificates: exact rational identity plus literal S_n and mutant
cd tools/colgen-loops
target/release/max11-colgen-loops validate-certificates \
  --certificate-n5 ../../literature/repos/max-relu-certificates/certificates/certificate_5_2.json \
  --certificate-n7 ../../literature/repos/max-relu-certificates/certificates/certificate_7_3.json \
  --output ../../artifacts/math/colgen-loops/certificate_controls.json

# 2,000-column prior-Python-DP cross-check
cd ../..
/usr/bin/time -v python artifacts/math/colgen-loops/cross_validate.py \
  --rust-binary tools/colgen-loops/target/release/max11-colgen-loops \
  --python-dp artifacts/math/span-structure-n5-n10/span_structure.py \
  --sample-n9 artifacts/math/colgen-loops/sample_python_n9.jsonl \
  --sample-n10 artifacts/math/colgen-loops/sample_python_n10.jsonl \
  --output artifacts/math/colgen-loops/cross_validation.json --threads 4

# Loopless dependency parity
cd tools/colgen-loops
/usr/bin/time -v target/release/max11-colgen-loops validate-loopless \
  --input ../../artifacts/math/colgen-loops/sample_loopless_n11.jsonl \
  --n 11 --branch-edges 5 --threads 4 \
  --output ../../artifacts/math/colgen-loops/loopless_parity.json

# Final n=11 host benchmark
/usr/bin/time -v target/release/max11-colgen-loops benchmark \
  --input ../../artifacts/math/colgen-loops/sample_benchmark_n11.jsonl \
  --n 11 --branch-edges 5 --universe-records 7015841 \
  --expected-sample-size 1000 --seed 2026090213 --threads 4 \
  --output ../../artifacts/math/colgen-loops/benchmark_n11.json

# Current-binary streaming/Python/modular smoke
cd ../..
/usr/bin/time -v python artifacts/math/colgen-loops/final_binary_smoke.py \
  --rust-binary tools/colgen-loops/target/release/max11-colgen-loops \
  --rust-lib tools/colgen-loops/src/lib.rs \
  --rust-main tools/colgen-loops/src/main.rs \
  --universe artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz \
  --python-dp artifacts/math/span-structure-n5-n10/span_structure.py \
  --cross-module artifacts/math/colgen-loops/cross_validate.py \
  --output artifacts/math/colgen-loops/final_binary_smoke.json \
  --records 8 --prime 1000003 --threads 4

# Final verifier (10.405 seconds wall; 75,980 KiB peak RSS in this run)
/usr/bin/time -v python artifacts/math/colgen-loops/verify_outputs.py

# Rust gates
cd tools/colgen-loops
cargo fmt --all -- --check
cargo build --release
cargo test --release
cargo clippy --all-targets --all-features -- -D warnings
```

For a chunked production pass, the new streaming command is:

```bash
target/release/max11-colgen-loops emit-universe \
  --input ../../artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz \
  --threads 4 --format binary --modulus 1000003 \
  --start START --limit COUNT --output OUTPUT.bin
```

Omitting `--limit` emits every row after `--start` without retaining the input
universe in memory. `emit-base-atoms` writes the explicit 5E/5L columns.

## Trials, failures, and resource accounting

- The first cross-validator retained all exact Rust columns. It was manually
  stopped before a verdict after reaching 9,382,924 KiB peak RSS against an
  intended 2,000-column denominator. AmberBluff was notified immediately. The
  implementation was replaced by a streaming comparator; its completed
  2,000/2,000 run took 3,933.026 seconds and peaked at 278,116 KiB.
- The first diagonal-sign mutant was too symmetric and survived 1/1 fixture.
  The control was not weakened: it was changed to flip one diagonal occurrence,
  after which the exact invariant or column comparison rejects it. The final
  certificate gates reject 2/2 such mutants.
- An initial assertion that every loop-using upstream certificate must retain
  a `d_0 != 0` hinge failed: the n=5 certificate has 0/3 such templates. That
  false assertion was removed, not relabelled as a pass. The reported fact is
  46/60 certificate templates, plus a purpose-built literal control passing
  1/1 with 7 retained `d_0` hinges.
- One initial compile needed an explicit `HashMap` value type; one initial
  clippy run rejected inconsistent digit grouping; both were fixed. A first
  certificate command was invoked before the named release binary existed and
  produced no result artifact; it was rerun after `cargo build --release`.
- Full audit: 7,015,841/7,015,841 rows in 307.321 seconds, peak 30,784 KiB RSS.
  Loopless parity: 1,000/1,000 rows in 207.59 seconds, peak 407,936 KiB RSS.
  Final current-binary smoke: 8/8 rows in 1.769 seconds, peak 40,180 KiB RSS.
- No generated or committed bead file exceeds 50 MB. The 78,769,863-byte
  G-0038 input predates this bead and is referenced by hash, not added here.

## What was not verified

- No complete 7,015,841-record column pass was run. Only its input stream was
  completely audited; generated columns were checked on the named finite
  denominators above.
- The native loop DP was not compared against `tools/colgen` on all
  754,017/754,017 loopless rows; empirical parity is 1,000/1,000, while the
  production loopless branch is code-level delegation.
- Literal S_n comparison covers the 60/60 upstream-certificate templates, not
  the complete loop-inclusive template universes for every n<=7.
- No rank, exact lift, rational separator, full pricing pass, or MAX11
  membership test was performed.

## No-claim line

This work supplies and controls a finite loop-inclusive degree-five column
generator. It does **not** show that MAX_11 is or is not in the G-0038 span, it
does **not** establish completeness of G-0038 for arbitrary two-hidden-layer
ReLU networks, and it is not an unrestricted depth theorem.
