# streamrank generation/sketch/reduce overlap

Bead: `relu-depth-frontier-research-fhw`  
Worker: `CobaltHare`  
Status: in progress; the orchestrator alone decides closure.

## No-claim boundary

**No claim:** this work measures and changes the throughput of a modular,
finite-row rank engine. An engine speedup changes no MAX11 verdict, proves no
identity, and supplies no unrestricted two-hidden-layer depth lower bound.
Pivot equality checks only execution-semantic preservation on the named
finite inputs; they are not exact-rational verification.

## Frozen inputs and denominators

- n=11 universe: `artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz`,
  SHA-256 `8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8`.
- Complete Stage-A order: 120,947 source indices, SHA-256
  `42cbef6ff5ef2652995b5d3b434c4672f71e622738649613808726b0ccf36c5f`.
- Benchmark order: the first 20,000/120,947 indices, stored as
  `stageA-first20000-order.json`, SHA-256
  `29bf756acd53f7fed328d5a5f4b03f40c462e59d0e625fbd94395d696e4470ef`.
- Committed Stage-A s1 reference report: 120,948 columns including 5L,
  SHA-256 `115818ab415386b32543b2cbc94eab788df3565d012cc279eab003b99cd6c7c0`.
- Expected pivot prefix: 7,330 pivots discovered among the first
  20,000/120,947 ordered source columns, `stageA-first20000-s1-expected-pivots.json`,
  SHA-256 `71aca8c25e6b4ebfe500947078e7dfa4b70c1f6c52bd5f37a686bc460ce7767c`.
- Benchmark field/sketch: p=1,000,003; m=64,000 buckets; seed
  2,026,090,201; batch denominator 1,024 except the final 544-column batch;
  GEMM block 8,192; rank panel 64; one sketch; 16 CLI threads.

The 20,000-prefix and expected-pivot files were deterministically derived with:

```bash
jq -c '.[0:20000]' \
  artifacts/math/stream-rank-engine/stageA-order-s5-beta-le1.json \
  > artifacts/math/streamrank-overlap/stageA-first20000-order.json
jq -c --slurpfile ord \
  artifacts/math/streamrank-overlap/stageA-first20000-order.json \
  '($ord[0] | map({key:(.|tostring), value:true}) | from_entries) as $selected |
   .sketches[0].pivot_columns | map(select($selected[(.|tostring)]))' \
  artifacts/math/n11-stageA/stageA-s5-beta-le1-plus5L-m64000-p1000003-s1-cuda.json \
  > artifacts/math/streamrank-overlap/stageA-first20000-s1-expected-pivots.json
```

## Timer semantics

Commit `ceb1ef0` added per-batch `generate_s`, `sketch_s`, `gemm_s`,
`host_reduce_s`, `basis_update_s`, and `io_s` fields to both
`STREAMRANK_PROGRESS` and serialized progress entries. `sketch_s` includes
dense matrix allocation. `host_reduce_s` is reducer wall time after subtracting
measured GEMM and scalar pivot/basis-update time. Phase clocks measure active
work; after pipelining their sum may exceed wall time because phases overlap.

## Trial register

All attempted variants are retained here; only rows explicitly marked gating
are used for the final comparison.

| Trial | Subject / denominator | Outcome | Gating? |
|---|---:|---|---|
| T0 | remote baseline wrapper, 0/20,000 | Aborted before streamrank start: NVL image has no `/usr/bin/time`; no JSON created. | no |
| T1 | local stale executable, n=10 12,248/12,248 and n=9 trees 739/739 | Known answers passed, but missing timer fields exposed that `cargo test` had not refreshed the release executable. Retained as a non-gating build-selection error. | no |
| T2 | instrumented local CPU, n=9 trees 739/739, one seed | `rank(A)=360`, `rank([A|b])=361`, NON_MEMBER; expected check passed. | diagnostic |
| T3 | instrumented local CPU, n=10 saved system 12,248/12,248, one seed | `rank(A)=rank([A|b])=2,166`, MEMBER; expected check passed. | diagnostic |
| T4 | instrumented sequential CUDA baseline, n=11 prefix 20,000/20,000 | Completed in 1,278.341672130 s; `rank(A)=7,330`, `rank([A|b])=7,331`. Binary SHA-256 `23d1bac794f695375ea849efd469423d76e0da5ba6f79043b7a94aad9486a86a`. | baseline |
| T5 | first bounded-pipeline variant, n=11 prefix 3,072/20,000 | Stopped only this worker's process after 149.703 s at rank 2,446. The named phase totals exposed unmeasured serial `SparseColumn`/`HashMap` destruction after sketch as the remaining preparation bottleneck. No result JSON was created; stderr is retained. Binary SHA-256 `ca5a24cc65162b1b79bd7e2ef1f06ec71bab155f6414cbaef1c45e0bc46de6e0`. | no |
| T6 | final bounded pipeline CUDA, n=11 prefix 20,000/20,000 | Completed in 615.351879507 s; `rank(A)=7,330`, `rank([A|b])=7,331`; 2.077415727x over T4. Binary SHA-256 `36c0e3ce8918164bd1d0a30e63399d1f446fef7b61df3bdeb16a2a6ed3a3fe5e`. | final |
| T7 | final binary, CPU n=10 saved system, 12,248/12,248, two seeds | 2/2 sketches reproduced MEMBER 2,166/2,166 and the committed pivot hash. | control |
| T8 | final binary, CUDA n=10 saved system, 12,248/12,248, two seeds | 2/2 sketches reproduced MEMBER 2,166/2,166 and were byte-identical to CPU. | control |
| T9 | final binary, CPU n=9 tree filter, 739/739, two seeds | 2/2 sketches reproduced NON_MEMBER 360/361 and the committed pivot hash. | control |
| T10 | final binary, CUDA n=9 tree filter, 739/739, two seeds | 2/2 sketches reproduced NON_MEMBER 360/361 and were byte-identical to CPU. | control |
| T11 | final CUDA binary, n=9 hostile expected `rank(A)=359`, 739/739, one seed | Correctly emitted `CONTROL_FAIL` and exited 1 after observing the unmodified 360/361 result. | adverse control |
| T12 | final local CPU binary, n=11 prefix, abort threshold 0 | Processed exactly one 64/20,000-column batch, emitted `ABORTED_GATE` at rank 64, and joined the scoped producer without deadlock. | resource-gate control |

T4 command (run only after `nvidia-smi` reported 40,938 MiB free and 0%
instantaneous GPU utilization; resident n=12 PIDs 10917 and 16355 were not
signalled or changed):

```bash
tools/streamrank/target/release/max11-streamrank run-universe \
  --backend cuda \
  --input /workspace/relu/artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --order-file stageA-first20000-order.json \
  --n 11 --branch-edges 5 --modulus 1000003 --buckets 64000 \
  --seeds 2026090201 --batch-size 1024 --gemm-block 8192 \
  --rank-panel 64 --threads 16 --output baseline-n11-first20000.json
```

T6 used the identical argv except for `--output final-n11-first20000.json`.
It began only after `nvidia-smi` reported 19,750 MiB free of 95,830 MiB and
0% instantaneous utilization. The three resident n=12 arms (PIDs 10917,
16355, and 35079) were not signalled or reconfigured. The final reducer's
recorded peak device allocation was 10,831,909,376 bytes. T4 ran alongside two
resident arms, so these are same-host, same-input, same-thread measurements,
not an isolated-machine benchmark; the final run did not receive the lighter
background load.

## Implementation and build custody

The producer generates each batch in the same indexed order, sketches columns
in parallel while preserving each column's sequential bucket-accumulation
order, and sends prepared batches through a capacity-one FIFO channel. The
consumer alone performs pivot discovery and basis updates. While batch `k` is
reduced, the producer prepares batch `k+1`; transient sparse-column destruction
is parallelized and separately timed as `sparse_drop_s`. The CPU and CUDA
reducers share this ordered ingress.

- Timer commit: `ceb1ef0`.
- Pipeline commit: `883fcd4`.
- Final source hashes: `src/main.rs`
  `666f7396a4fe529c809536b4ed5f0465a72f3e70172c2479120458ab1d95a335`,
  `src/lib.rs`
  `7f47f49379a2bca1c0b5fa3cc4e6d486731dd41577bda3b6083fba611762c161`,
  `src/cuda.rs`
  `e81e768aa60f9372d262914b2255bd32f1d6a27ff9a7efa6ad333b8d7797f417`,
  `src/cuda_backend.cu`
  `22a311c57bc6fb59acce18011fcb104e4a793c05f490b7967c199fa43ce80341`,
  `Cargo.toml`
  `e6065d00916457a90b8549a2e7afda8b5364af80e4e9f52213263cbac9a46c80`,
  and the consumed colgen `src/lib.rs`
  `9b7a3af7328d543c6791d9d983aaf97af7a2be232f459beccaf443e3668081e1`.
- Both remote binaries were built with `cargo build --release --features cuda`
  in isolated source copies under `/workspace/cobalthare-fhw/`.

## Measured phase breakdown

Each cell below is active seconds summed over exactly 20 batches and 20,000
source columns, except wall time, which is one complete 20,000-column run.
Active clocks overlap in T6 and therefore do not add to wall time.

| Measure / denominator | T4 sequential | T6 pipeline |
|---|---:|---:|
| wall s / 20,000 columns | 1,278.341672130 | 615.351879507 |
| generate s / 20 batches | 729.471864828 | 557.112136951 |
| sketch incl. allocation s / 20 batches | 222.467753696 | 24.281616720 |
| GEMM s / 20 batches | 0.974747040 | 1.142710531 |
| other host-reduce s / 20 batches | 65.223865131 | 59.986861361 |
| scalar pivot/basis-update s / 20 batches | 32.564739561 | 167.143735111 |
| I/O s / 20 batches | 0.000000000 | 0.000000000 |
| sparse destruction s / 20 batches | not separately timed | 28.225022149 |
| wall speedup ratio / one paired comparison | 1.000000000 | **2.077415727** |

On T4, generation consumed 57.064% and serial sketching 17.403% of the
1,278.341672130-second wall denominator; GEMM consumed only 0.076%. The six
active clocks leave 227.638701874 wall seconds unassigned in that pre-drop-
timer binary, so that residual is not attributed to any single phase. In T6,
parallel sketch active time fell to 24.281616720 s/20 batches, and generation
remained the critical producer cost at 557.112136951 s/20 batches. T6's active
clock sum exceeds wall time by design because production and reduction overlap.

## Exact control invocations

The exact argv arrays are also embedded in each JSON report. These commands
were run from the isolated final build directory with the same final binary:

```bash
BIN=tools/streamrank/target/release/max11-streamrank
N9=/workspace/relu/handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz
N10=/workspace/relu/handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz

$BIN run-saved --backend cpu --input "$N10" --n 10 --branch-edges 4 \
  --filter all --modulus 1000003 --buckets 6498 \
  --seeds 2026090201,2026090202 --batch-size 1024 --gemm-block 1024 \
  --rank-panel 64 --threads 6 --expected-columns 12248 \
  --expected-rank 2166 --expected-aug-rank 2166 \
  --expected-verdict MEMBER --output controls-final/cpu-n10.json
$BIN run-saved --backend cuda --input "$N10" --n 10 --branch-edges 4 \
  --filter all --modulus 1000003 --buckets 6498 \
  --seeds 2026090201,2026090202 --batch-size 1024 --gemm-block 1024 \
  --rank-panel 64 --threads 16 --expected-columns 12248 \
  --expected-rank 2166 --expected-aug-rank 2166 \
  --expected-verdict MEMBER --output controls-final/cuda-n10.json
$BIN run-saved --backend cpu --input "$N9" --n 9 --branch-edges 4 \
  --filter union-trees --modulus 1000003 --buckets 1080 \
  --seeds 2026090201,2026090202 --batch-size 256 --gemm-block 1024 \
  --rank-panel 64 --threads 6 --expected-columns 739 \
  --expected-rank 360 --expected-aug-rank 361 \
  --expected-verdict NON_MEMBER --output controls-final/cpu-n9.json
$BIN run-saved --backend cuda --input "$N9" --n 9 --branch-edges 4 \
  --filter union-trees --modulus 1000003 --buckets 1080 \
  --seeds 2026090201,2026090202 --batch-size 256 --gemm-block 1024 \
  --rank-panel 64 --threads 16 --expected-columns 739 \
  --expected-rank 360 --expected-aug-rank 361 \
  --expected-verdict NON_MEMBER --output controls-final/cuda-n9.json
$BIN run-saved --backend cuda --input "$N9" --n 9 --branch-edges 4 \
  --filter union-trees --modulus 1000003 --buckets 1080 \
  --seeds 2026090201 --batch-size 256 --gemm-block 1024 \
  --rank-panel 64 --threads 16 --expected-columns 739 \
  --expected-rank 359 --expected-aug-rank 361 \
  --expected-verdict NON_MEMBER \
  --output controls-final/cuda-n9-mutant-rank359.json
```

The local producer-shutdown control used:

```bash
timeout 120 tools/streamrank/target/release/max11-streamrank run-universe \
  --backend cpu \
  --input artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --order-file artifacts/math/streamrank-overlap/stageA-first20000-order.json \
  --n 11 --branch-edges 5 --modulus 1000003 --buckets 128 \
  --seeds 2026090201 --batch-size 64 --gemm-block 64 --rank-panel 16 \
  --threads 4 --abort-rank-above 0 \
  --output artifacts/math/streamrank-overlap/local-abort-control.json
```

The saved n=9 input SHA-256 is
`729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991`;
the saved n=10 input SHA-256 is
`bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18`.
The control field is p=1,000,003. Across 4/4 backend/input cases and 8/8
sketches, n=9 reproduced pivot hash
`3885bf4223184e19c9d6cfdc1632d24d33c47c7cbc4a859f4208257af0933cdd`
and n=10 reproduced
`13ef82302f2e50e9f9555cd77eab1881bd3ef87f33677badd2b9fe079e39a87d`.

## Semantic gates and verification

- T4 and T6 extracted pivot JSON files are byte-identical to each other and to
  the 7,330/20,000-pivot frozen reference; all three file SHA-256 values are
  `71aca8c25e6b4ebfe500947078e7dfa4b70c1f6c52bd5f37a686bc460ce7767c`.
- Their embedded little-endian-u64 pivot hash is identically
  `a9920a36aea1d328214a5208c3b0e132531cdb4839c52670d96bfe0a7043a978`.
- All 20/20 `(source_columns_processed, ranks)` progress pairs are identical,
  ending at `(20,000, [7,330])`; final augmented rank is 7,331 in both.
- The n=9 and n=10 CPU/CUDA pivot arrays are byte-identical for both seeds.
- The hostile rank-359 expected block failed closed with exit 1.
- Local release tests passed 8/8, remote `--features cuda` tests passed 9/9,
  and release clippy passed with warnings denied. The 64/20,000 abort test
  exercised early receiver drop and scoped-producer join without a deadlock.
- Final `./skill-runtime verify-quick` reached the single documented campaign
  finding, SE-10 on G-0015; project swarm instructions explicitly classify it
  as pre-existing and ignorable for this bead. No new verifier finding was
  emitted for this work.
- `verify_results.py` recomputes raw hashes and u64 pivot hashes, checks every
  timer field, compares all pivot arrays and per-batch traces, enforces the
  2.0x wall gate, checks both known answers on both backends, and checks the
  adverse control. It emitted `verification.json` with `result: PASS`.

Key raw artifact hashes are:

| Artifact | SHA-256 |
|---|---|
| `baseline-nvl-n11-first20000.json` | `81bcc5c0989cef8fce5013f52705c3891b30c66ca597906cd511e028fed1606c` |
| `baseline-nvl-n11-first20000.log` | `799cc157118a00d502226724f951d173cdc1a4213f2ae96fdc78539480825513` |
| `final-nvl-n11-first20000.json` | `2e6d3d57b2417944eb4d1deff5f279169546cc5adabab2311b445b85cfc5b5ca` |
| `final-nvl-n11-first20000.log` | `ef3fd35080bf7dd0c5459243fb6bc5381d0466a0078eaee14f3facf511ac7249` |
| `overlap-v1-aborted-3072.log` | `cbe6c5823d43038e393e3e2f4cf4f1d121ed642b1b7fd6179b11795e0ac25ddb` |
| `controls-final/cpu-n10.json` | `39167f220ce43a986fea58f45ac37cb4d36278930787984aee03c62309d2a9c3` |
| `controls-final/cpu-n9.json` | `f73c68f09c1a49571fd07f5670053ae13c16fdf8cbfb9228c05ed1e16fd07e7b` |
| `controls-final/cuda-n10.json` | `15a138437c267830faa0a289ea2c16cb6c2f2d5044e9cdaa8bc0de00730780b3` |
| `controls-final/cuda-n9.json` | `ccaeb49d55d636bc12659dfe6bd49248a4f42742f7f506744b87afddd68b8e17` |
| `controls-final/cuda-n9-mutant-rank359.json` | `b5fc5665371b1842f358add3e8ee3fcd1b80892217f4427bac62aabb5c95a843` |

## Interpretation

This is a measured throughput improvement for one finite modular benchmark.
It establishes ordered execution parity on the stated fixtures and closes the
bead's performance gate. It does **not** establish exact rational equality,
transfer the speedup to every n=12 workload, alter any existing verdict, or
prove an unrestricted depth lower bound. Restarting live arms remains an
orchestrator decision.
