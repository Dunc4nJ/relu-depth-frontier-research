# Exact column-generation throughput

- Bead: `relu-depth-frontier-research-3ke`
- Worker: `CobaltHare`
- Status: gates passed; awaiting AmberBluff review. Only AmberBluff closes the
  bead.

## No-claim boundary

**No claim:** this work profiles and optimizes exact generation for a named,
finite atom family. A speedup changes no MAX11 verdict, proves no identity,
and supplies no unrestricted two-hidden-layer depth lower bound. Byte-identical
MCOLGEN1 and pivot outputs are execution-semantic gates, not new mathematics.

## Preregistered scenario and gates

- Primary scenario: emit exact binary MCOLGEN1 columns for the first
  4,096/120,947 indices in the frozen n=11 Stage-A order, with 16 threads.
- Frozen prefix: `stageA-first4096-order.json`, 4,096 indices, SHA-256
  `0023b80943d454cf502403b045a6d5ea5bc6bf638ec314e81f21382957d4a984`.
- Universe: `artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz`,
  SHA-256
  `8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8`.
- Primary metric: same-host wall seconds for one complete 4,096-column run;
  acceptance requires baseline/candidate ratio at least 2.0 with identical
  thread count, argv, input bytes, and MCOLGEN1 SHA-256.
- Additional golden gates: byte-identical MCOLGEN1 output for all
  10,976/10,976 n=9 saved templates and all 12,248/12,248 n=10 saved templates; identical
  streamrank pivot list on the n=10 known answer.
- Profile taxonomy: record/matrix preparation, subset-increment table,
  dynamic-program child enumeration, DP state hashing/deduplication and map
  allocation, terminal-word canonicalization, hinge hashing/deduplication,
  output sorting/serialization, and I/O.

## Trial register

Every attempted profile and optimization variant will be appended here,
including aborts and nulls. No optimization is admitted before an
instrumentation-only ranked hotspot table and an isomorphism note.

| Trial | Subject / denominator | Outcome | Gating? |
|---|---:|---|---|
| T0 | current binary, n=11 Stage-A prefix 4,096/4,096 | Baseline completed; 6,611,102,772-byte exact MCOLGEN1 output. | baseline |
| T1 | instrumentation-only binary, same 4,096/4,096; every 16th column profiled (256/4,096) | Profile completed; output SHA-256 byte-identical to T0. | profile |
| T2 | compact-i8 DP state, same 4,096/4,096 | 314.374 s complete wall, 1.023887x; output byte-identical to T0. This is a bounded performance null, not the gate result. | no |
| T3 | compact-i8 plus parallel output preparation, same 4,096/4,096 | 143.368 s complete wall, 2.245x; output byte-identical. | intermediate pass |
| T4 | saved-system gate harness build | Requested nonexistent bin name `emit-saved`; Cargo rejected the selection before execution. Corrected to declared `emit_saved`; no result was silently discarded. | aborted |
| T5 | T3 binary, saved n=9 10,976/10,976, saved n=10 12,248/12,248, n=10 streamrank 12,248/12,248 | All exact-column comparisons, MCOLGEN hashes, expected ranks/verdicts, and pivots passed. Superseded by final binary gates below. | intermediate controls |
| T6 | packed-u128 DP state, n=11 4,096/4,096 | MCOLGEN wall 114.604 s and byte-identical; isolated generation 41.404302715 s versus 78.561831852 s baseline (1.897432x), just below the bottleneck-specific target. | bounded null for 2x generation |
| T7 | local 1-thread harness smoke, n=11 512/512 requested | Harness compiled, but the deliberately slow serial run was manually aborted before a result because the remote same-host 16-thread comparison was already running. | aborted |
| T8 | packed DP plus packed hinge dedup, n=11 4,096/4,096 | Isolated generation 35.966299478 s (2.184318x); complete MCOLGEN wall 108.108 s (2.977421x); output byte-identical. | final pass |
| T9 | final binary, saved n=9 10,976/10,976 and n=10 12,248/12,248 | Every generated column equalled its saved exact column; MCOLGEN outputs byte-identical to baseline. | final pass |
| T10 | final colgen linked into frozen fhw streamrank, n=10 12,248/12,248, two seeds | Both ranks 2,166/2,166, verdict MEMBER, and both 2,166-entry pivot arrays byte-identical to reference. | final pass |
| T11 | final instrumentation, n=11 512/512 | Reprofile completed; 768,886,046-byte MCOLGEN output byte-identical to the compact-profile control. | final profile |
| T12 | campaign verifier | First invocation used root-relative paths from `tools/colgen/` and returned command-not-found; rerun from repository root completed and reported 22 SE-10 findings in concurrently modified protected ledger files. No protected file was edited here. | external/shared-state finding |

## Baseline custody

T0 ran on the NVL box from isolated directory
`/workspace/cobalthare-3ke/baseline`, with 16 threads. `nvidia-smi` reported
11,748 MiB free of 95,830 MiB and 0% instantaneous GPU utilization before the
CPU-only run. The three existing n=12 processes were not signalled or changed.

```bash
TIMEFORMAT='wall_seconds=%R'
time target/release/max11-colgen emit-universe \
  --universe /workspace/relu/artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --threads 16 --order-file stageA-first4096-order.json \
  --format binary --output results/n11-first4096-exact.mcolgen1
```

- Baseline source: `src/lib.rs` SHA-256
  `9b7a3af7328d543c6791d9d983aaf97af7a2be232f459beccaf443e3668081e1`;
  `src/main.rs`
  `1cb685be4e8a6b96c1ce056453b3671c53eabcd3a87dc7fd6a5f34456742ebc0`.
- Baseline binary SHA-256:
  `77c3488d6e4f23cbd089cbb026cacd97c0901ab0d6b4a5b284dc0676e980cb3d`.
- Complete wall: 321.883 s / 4,096 columns; internal emit window:
  318.583 s / 4,096 columns.
- Output: 6,611,102,772 bytes / 4,096 columns, SHA-256
  `5c900f18a8e84220beb2df51ae32555774f82460769bb3166f96897d14bdbfa1`.
- Acceptance threshold: at most 160.9415 complete wall seconds for one
  same-host, same-16-thread 4,096-column run.

## Instrumentation profile and ranked hotspots

Instrumentation-only commit `3dd9058` adds a generic no-op observer for the
normal path and a timing observer selected only by
`MAX11_COLGEN_PROFILE_OUTPUT`. T1 ran the complete 4,096-column subject and
profiled positions `0 mod 16`, exactly 256/4,096 columns. Per-child clock reads
perturb sampled columns, so T1 is attribution evidence, not the throughput
baseline. Nevertheless its 6,611,102,772-byte output has the same SHA-256 as
T0, establishing output preservation for the instrumentation path.

Active CPU values below sum over 256 profiled columns; percentages divide by
124.373795651 active CPU seconds. Wall-stage values divide by the
330.316024245-second internal emit window.

| Rank | Location | Metric / denominator | Value | Share | Evidence |
|---:|---|---|---:|---:|---|
| 1 | subset DP total | active CPU / 256 columns | 99.042378398 s | 79.633% active | `profile/n11-first4096-profile.json` |
| 2 | DP state hash + dedup | active CPU / 278,303,075 probes | 65.379644804 s | 52.567% active | same |
| 3 | output conversion + lexicographic sort | wall / 4,096 columns | 135.508743656 s | 41.024% emit | same |
| 4 | terminal hinge enumeration | active CPU / 26,176,046 terminal words | 24.907522481 s | 20.026% active | same |
| 5 | word canonicalization | active CPU / 26,176,046 terminal words | 15.237613442 s | 12.251% active | same |
| 6 | hinge hash + dedup | active CPU / 16,380,502 retained words | 5.369793752 s | 4.317% active | same |
| 7 | serialization + buffered write | wall / 4,096 columns | 29.349659527 s | 8.885% emit | same |
| 8 | DP map allocation | active CPU / 2,816 layer allocations | 0.566306665 s | 0.455% active | same |

Counts provide the discriminator: 120,852,557/278,303,075 DP probes (43.425%)
hit an existing state, whereas only 2,807,199/16,380,502 retained hinge words
(17.137%) deduplicated. Matrix construction plus subset-increment construction
used only 0.067845971 active CPU seconds / 256 columns.

### Hypothesis ledger and opportunity matrix

| Candidate | Evidence verdict | Impact | Confidence | Effort | Score |
|---|---|---:|---:|---:|---:|
| compact fixed-width DP state key | supports: top hotspot hashes the current 34-byte state key on 278,303,075 probes | 5 | 5 | 2 | 12.5 |
| parallelize output conversion/sort and sparse-column destruction in the existing batch pool | supports for end-to-end emission: conversion/sort is 41.024% of emit wall and currently serial | 5 | 5 | 2 | 12.5 |
| compact temporary hinge-direction key | supports: canonicalization + hinge hash is 16.569% active and allocates a `Vec<i16>` per terminal word | 4 | 4 | 3 | 5.3 |
| reuse DP maps/buffers | rejects as first lever: explicit map allocation is 0.455% active | 1 | 3 | 2 | 1.5 |
| cache matrix/increment derivation | rejects: both stages total 0.055% active | 1 | 5 | 2 | 2.5, but negligible absolute ceiling |

The first optimization lever is therefore a compact DP state representation;
output parallelism remains a separate commit and is attempted only if the
complete-wall gate requires it.

T2 commit `126e92c` represented the 16 stored word coordinates as checked
`i8` values rather than `i16`. It passed the signed-mass-127 endpoint against
literal enumeration and reproduced T0's 6,611,102,772-byte SHA-256 exactly,
but improved complete wall only from 321.883 s / 4,096 columns to 314.374 s /
4,096 columns (1.023887x). This finite null rejects compact DP words alone as
the solution to the end-to-end gate; it says nothing about other workloads.

### Isomorphism obligation for lever 1

- Ordering preserved: yes; caller order, DP depth order, and vertex loop order
  remain unchanged.
- Tie-breaking unchanged: N/A; exact integer hash-map merging has no tie.
- Floating point: N/A.
- RNG: N/A.
- Representation proof required: every stored back-degree entry must round-trip
  exactly between signed `i16` and its compact key; the n<=16 and signed-mass
  bounds must be checked rather than assumed.
- Golden outputs required: exact T0 MCOLGEN1 SHA plus existing literal-
  permutation, branch-swap, and corruption controls.

### Isomorphism obligation for final representation and scheduling

- The input contract checks `branch_edges <= 127`; every incremental
  back-degree is converted to `i8` with `try_from`, so an out-of-range value
  fails closed rather than truncating.
- At `n <= 14`, the low 16 bits of `PackedState(u128)` contain the visited
  mask and the remaining 112 bits contain 14 disjoint signed-byte slots.
  Encoding through `i8 as u8` and decoding through `u8 as i8` is a lossless
  two's-complement round trip. `n=15,16` retain the fixed-width fallback.
- A primitive coordinate is the original signed-byte coordinate divided by a
  positive gcd and optionally sign-flipped, so it remains representable in a
  signed byte; conversion is nevertheless checked. A column has one fixed
  `n`, so its packed direction key needs no length tag. Each unique key is
  expanded back to the public `Vec<i16>` representation before return.
- Hash-table encounter order can change, but all merges are checked exact
  integer additions. Serialized hinges are lexicographically sorted. The
  indexed Rayon collection preserves source-record order, and only the final
  batch writer is serial.
- There is no floating point, RNG, approximate reduction, changed filter, or
  changed tie-break in column generation.

## Final throughput result

The final code is commits `cfd80b0` (parallel output preparation), `420d0cf`
(packed DP key), and `1ca9c00` (packed hinge key), with documentation in
`6ae138e`. Final source and release-binary custody on the NVL box:

- `src/lib.rs` SHA-256
  `cd4d16fda3b5e673ed43063e22db1ec66637413636f1ab1da24cae8ac5b412f8`.
- `src/main.rs` SHA-256
  `7bf1ec0064b8eeb11ff7184decef6098427aa596fb15577a007ffd96309e206c`.
- `target/release/max11-colgen` SHA-256
  `de2fc1cd6b8fde07686a69126a25a882fef859868cbaed30c0c42e548baf776f`.

### Exact-generation-only measurement

`bench_generate.rs` SHA-256
`82eb70d5a162b41bfbf701949bccdf436346cc40bc31f96884de98177809d308`
loads the universe and order before its internal clock, then generates and
destroys every exact sparse column in the same 16-thread indexed Rayon pool.
It reports aggregate support counts to make the work observable. Baseline and
final were run sequentially on the same NVL host with the same harness,
inputs, order, and 16 threads:

```bash
TIMEFORMAT='wall_seconds=%R'
time target/release/bench_generate \
  /workspace/relu/artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  stageA-first4096-order.json 16 > generation-benchmark/n11-first4096.json
```

| Metric / denominator | Baseline | Final | Ratio / equality |
|---|---:|---:|---:|
| harness generation wall / 4,096 columns | 78.561831852 s | 35.966299478 s | **2.184318x** |
| complete shell wall / 4,096 columns | 84.462 s | 40.330 s | **2.094272x** |
| throughput / 4,096 columns | 52.137277 columns/s | 113.884388 columns/s | 2.184318x |
| total linear entries / 4,096 columns | 45,056 | 45,056 | identical |
| total hinge entries / 4,096 columns | 220,355,892 | 220,355,892 | identical |

Evidence is in `generation-baseline/` and `generation-final/`. The clocks are
wall clocks, not sums of per-thread CPU time.

### Complete MCOLGEN1 measurement

The preregistered command in **Baseline custody** was repeated unchanged from
isolated directory `/workspace/cobalthare-3ke/packed-hinge`. Before the run,
GPU headroom was checked; existing n=12 processes were neither signalled nor
changed. No measurement used more than 16 worker threads.

| Metric / denominator | Baseline | Final | Ratio / equality |
|---|---:|---:|---:|
| complete shell wall / 4,096 columns | 321.883 s | 108.108 s | **2.977421x** |
| internal emit wall / 4,096 columns | 318.583 s | 105.117 s | 3.030747x |
| output bytes / 4,096 columns | 6,611,102,772 | 6,611,102,772 | identical |
| output SHA-256 / 4,096 columns | `5c900f18...bdbfa1` | `5c900f18...bdbfa1` | byte-identical |

The unabbreviated SHA-256 on both sides is
`5c900f18a8e84220beb2df51ae32555774f82460769bb3166f96897d14bdbfa1`.
Final logs are in `packed-hinge/`; the 6.6 GB output remains on the NVL box and
is not committed.

## Golden-output gates

### Saved n=9 and n=10 exact systems

The gate harness `emit_saved.rs` (SHA-256
`2acdff0e9e5d2baa552d8af27c6e6aa9f8d1caa036f1e8fe7bf046b105994db3`)
derives each record from its two saved branches, generates the exact column,
requires equality with the saved exact column, then writes MCOLGEN1 in source
order. It was linked separately to the baseline and final libraries.

```bash
target/release/emit_saved \
  /workspace/relu/handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  9 4 16 10976 saved-results/n9-all-exact.mcolgen1
target/release/emit_saved \
  /workspace/relu/handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  10 4 16 12248 saved-results/n10-all-exact.mcolgen1
```

| Subject | Input SHA-256 | Exact matches / denominator | Output bytes | Baseline and final output SHA-256 |
|---|---|---:|---:|---|
| saved n=9 | `729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991` | 10,976/10,976 | 273,862,332 | `6dfdda67a78330860a1ae90e03f4d00195faf70e791a1aa867ba7589700c1487` |
| saved n=10 | `bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18` | 12,248/12,248 | 930,256,772 | `edc289626d2060f881563002fbf752eb3f1e15f50add9fa3d67115808164d721` |

Final complete walls were 17.418 s / 10,976 n=9 columns and 47.772 s /
12,248 n=10 columns. Baseline and final evidence is in `saved-baseline/` and
`saved-final-packed/`; the binary outputs remain remote.

### Streamrank n=10 pivot gate

The final colgen library was linked into the frozen fhw streamrank sources
(`src/main.rs` SHA-256
`666f7396a4fe529c809536b4ed5f0465a72f3e70172c2479120458ab1d95a335`,
`src/lib.rs` SHA-256
`7f47f49379a2bca1c0b5fa3cc4e6d486731dd41577bda3b6083fba611762c161`).
CUDA release tests passed 9/9. The resulting streamrank
binary SHA-256 was
`874d83973eabe4737c6885ac6cdef5db7312b7db38a695b51d082fc2409cb0f3`.
The exact command was:

```bash
target/release/max11-streamrank run-saved --backend cuda \
  --input /workspace/relu/handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --n 10 --branch-edges 4 --filter all --modulus 1000003 \
  --buckets 6498 --seeds 2026090201,2026090202 --batch-size 1024 \
  --gemm-block 1024 --rank-panel 64 --threads 16 \
  --expected-columns 12248 --expected-rank 2166 \
  --expected-aug-rank 2166 --expected-verdict MEMBER \
  --output ../../results-final/n10-cuda.json
```

Both seeds returned rank(A)=rank([A|b])=2,166 and MEMBER over exactly
12,248/12,248 source columns. Each final pivot array has 2,166 entries and is
element-for-element equal to the reference; each little-endian pivot hash is
`13ef82302f2e50e9f9555cd77eab1881bd3ef87f33677badd2b9fe079e39a87d`.
The final report SHA-256 is
`9c9a0dc503f2d6a484e681a85d2df50fa3abbdfd3fe35d8c0f3dd2d6a4b23903`;
evidence is in `streamrank-final-packed/`.

## Reprofile after optimization

T11 profiled every one of 512/512 frozen prefix columns. Its exact
768,886,046-byte output SHA-256
`146b1cbb157fb33b1b3607f6596d97a4c92f29fd9da3ba340e2d39071dc49100`
matches the pre-packed 512-column control. Active times sum across threads and
are deliberately perturbed by per-operation clocks:

| Location | Active time / denominator | Share of 148.334912733 active s |
|---|---:|---:|
| subset DP | 118.377382217 s / 512 columns | 79.804% |
| DP hash + dedup | 69.168331782 s / 560,769,198 probes | 46.630% |
| terminal hinge enumeration | 29.507324469 s / 48,061,203 terminal words | 19.892% |
| canonicalization | 15.000291613 s / 48,061,203 terminal words | 10.112% |
| hinge hash + dedup | 2.655595079 s / 30,131,265 retained words | 1.790% |
| DP map allocation | 0.645819271 s / 5,632 layer maps | 0.435% |
| matrix + increment preparation | 0.073752411 s / 512 columns | 0.050% |

Normalized DP-hash time fell from 234.922 ns/probe in T1 to 123.345
ns/probe in T11 (1.905x); hinge-hash time fell from 327.816 ns/retained word
to 88.134 ns/retained word (3.720x). The remaining dominant cost is therefore
the exact subset DP itself, not setup, allocation, or hinge-table hashing.

## Verification summary

- Local `cargo test --release --all-targets`: 8/8 passed.
- Local `cargo clippy --release --all-targets -- -D warnings`: passed.
- NVL CUDA-linked streamrank release tests: 9/9 passed.
- All recorded gate exit codes are zero.
- `./skill-runtime verify-quick` was run from the repository root. It exited 1
  on 22 SE-10 findings in protected, concurrently changed ledger files
  (including the documented G-0015 finding); this bead did not edit those
  files. The Rust and exact-output gates above are independently green.
- No output over 50 MB is committed; remote output byte counts and hashes are
  recorded above.

**No claim:** these are engineering measurements and exact execution-semantic
controls on named finite inputs. They do not change a MAX11 verdict, certify a
new rational identity, prove ansatz completeness, or establish an
unrestricted depth lower bound.
