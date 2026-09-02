# EXP-0037 trial log

All denominators are explicit. No n=12 subject arm was launched before the
final known-answer suite passed.

## Bootstrap and pre-control trials

- The orchestrator bootstrap initially exposed the H100 NVL (95,830 MiB), but
  `cargo` was absent and the required repo paths were empty. Once Rust, CUDA
  12.4, OpenBLAS, and Python were present, a narrow rsync supplied only the
  frozen streamrank/colgen trees, two saved systems, n=12 inputs, and committed
  harnesses. All input and source SHA checks passed before build.
- Control attempt 1 began at 2026-09-02T21:05:50Z. The CUDA-feature binary
  built and its 7/7 Rust tests passed, but the first CPU command used 60/64
  threads and was rejected by the binary's CPU limit of 6/64. It certified
  0/12,248 columns and wrote no JSON. The complete log is preserved under
  `controls/attempt-01-aborted/`.
- Control attempt 2 began at 2026-09-02T21:10:02Z with CPU threads corrected
  to 6/64. Its first n=10 batch hit `nonzero at an existing pivot after
  reduction`; it completed 0 checkpoints/12,248 and wrote no JSON. It used
  batch size 1,024.
- Control attempt 3 began at 2026-09-02T21:11:24Z after an exploratory change
  to CPU batch size 256. It failed with the identical reduction invariant,
  again at 0 completed checkpoints/12,248 with no JSON. This falsified batch
  size as the cause. Both attempts are retained under their named aborted
  directories.
- A separate one-thread n=10 diagnostic with the box's default OpenBLAS 0.3.20
  failed with the same reduction invariant and wrote no JSON. The same
  one-thread command with `OPENBLAS_CORETYPE=HASWELL` completed
  12,248/12,248 columns in 38.084 seconds with rank pair 2,166/2,166 and
  `MEMBER`; its pivot SHA was the registered CPU value. Both directions are
  retained under `controls/diagnostics/`.
- A byte copy of the campaign host's OpenBLAS 0.3.30 shared object, SHA-256
  `b4dee79f670f590fc062cefdcd9392ff470d39f5a2af9bf577af8ae05430387a`,
  was tested as a possible runtime replacement. `ldd` rejected it because it
  requires GLIBC 2.38 while the box has GLIBC 2.35. It was never loaded by a
  control or subject process. The smaller `OPENBLAS_CORETYPE=HASWELL`
  intervention was used instead.
- Control attempt 4 began at 2026-09-02T21:18:20Z with the stable HASWELL
  kernel. All 4/4 CPU system-prime reports passed, but the first CUDA command
  used 60/64 threads and the binary rejected its CUDA limit of 24/64 before
  0/12,248 columns. The successful CPU reports and CUDA refusal remain under
  `controls/attempt-04-aborted/`; they are historical and not substituted into
  the final suite.

## Version 1 known-answer suite (superseded)

Attempt 5 began at 2026-09-02T21:21:06Z using CPU 6/64 threads, CUDA 24/64
threads, `OPENBLAS_CORETYPE=HASWELL`, and one CUDA-feature binary with SHA-256
`11d08a17eb706f6b4bfcc3f75d18e0e3e02167127e19c1db0b74a1ee810fe676`.
All 8/8 backend-system-prime reports passed, with both registered seeds per
report:

- n=10: CPU and CUDA each processed 12,248/12,248 columns at each of 2/2
  primes; all 8/8 seed-backend-prime observations were rank
  2,166/2,166, `MEMBER`, with pivot SHA
  `13ef82302f2e50e9f9555cd77eab1881bd3ef87f33677badd2b9fe079e39a87d`.
- n=9 union-trees: CPU and CUDA each processed 739/739 selected columns at
  each of 2/2 primes; all 8/8 seed-backend-prime observations were rank
  360/361, `NON_MEMBER`, with pivot SHA
  `3885bf4223184e19c9d6cfdc1632d24d33c47c7cbc4a859f4208257af0933cdd`.
- The CPU/CUDA ordered-pivot comparison passed 8/8 system-seed-prime pairs.
- The deliberate n=9 expected-rank mutation (359 instead of 360) returned
  nonzero and wrote `CONTROL_FAIL`; it was rejected 1/1.
- The independent local verifier result was
  `EXP0037_CONTROLS_PASS reports=8/8 pivots=8/8 planted_mutant=1/1`.

AmberBluff subsequently authorized increasing the CUDA-only thread limit from
24/64 to 60/64. Because that changes the subject binary, this suite is retained
under `controls-v1-threads24/` but is not used to gate the restarted arms.

The first replacement-suite launch was aborted after an rsync layout error:
the five updated files landed at `/workspace/relu/` instead of their repository
relative paths, so the invoked harness still saw the version 1 source and
binary. Its 7/7 Rust tests passed, but the first CPU control was terminated at
the 5,120/12,248 checkpoint and wrote no JSON. The logs and misplaced-file
bytes are preserved under `attempt-control-v2-aborted-sync-layout/`. A
corrected relative-path sync and exact source-hash preflight preceded the one
replacement suite used below.

## Version 2 final known-answer suite

The replacement suite ran from 2026-09-02T21:56:42Z through 22:00:10Z with
source SHA-256
`67e2b19731bebc6ec506d3830eb2e85d2d9268b1a14688d99a9c9d075b6b1448`
and rebuilt binary SHA-256
`cdf835b269d25a37f110d72f16865e6f511d5154b5caf7808dd2eb1d82bc85c3`.
CPU controls used 6/64 threads and CUDA controls used 60/64 threads; all other
reducer settings remained those of version 1.

- n=10: 8/8 seed-backend-prime observations processed 12,248/12,248
  columns, obtained rank 2,166/2,166 and `MEMBER`, and reproduced pivot SHA
  `13ef82302f2e50e9f9555cd77eab1881bd3ef87f33677badd2b9fe079e39a87d`.
- n=9 union-trees: 8/8 seed-backend-prime observations processed 739/739
  selected columns, obtained rank 360/361 and `NON_MEMBER`, and reproduced
  pivot SHA
  `3885bf4223184e19c9d6cfdc1632d24d33c47c7cbc4a859f4208257af0933cdd`.
- CPU/CUDA ordered pivots agreed for 8/8 system-seed-prime pairs. The planted
  expected-rank-359 mutation was rejected 1/1. The independent verifier passed
  8/8 reports, 8/8 pivot comparisons, and 1/1 mutation rejection.

## Subject attempt 1 (aborted at orchestrator steer)

Two p=1,000,003 arms were live concurrently when the thread-limit steer
arrived. Both used the version 1 binary above and 24/64 column-generation
threads. They were terminated with SIGTERM, exited 143, wrote no observation
JSON, and therefore produced no complete rank or membership verdict.

- Seed 2,026,090,201 reached the 10,240/148,628 order-file checkpoint, rank
  5,418/128,000 sketch rows, after 1,350.443 seconds. Telemetry contains 97/97
  samples, with maxima 42,379/95,830 MiB aggregate GPU memory and
  9,360,416/230,686,720 KiB process RSS.
- Seed 2,026,090,202 reached the 8,192/148,628 order-file checkpoint, rank
  4,828/128,000 sketch rows, after 1,053.101 seconds. Telemetry contains 78/78
  samples, with maxima 42,379/95,830 MiB aggregate GPU memory and
  8,210,732/230,686,720 KiB process RSS.

The complete logs and telemetry are preserved under
`attempt-01-aborted-threads24/`. These checkpoint ranks are intermediate
diagnostics, not results on the full 148,629/148,629 source-column denominator
(148,628 ordered universe records plus 1/1 five-linear carrier).

## Scheduling amendment: two concurrent slots

At 2026-09-02T23:06Z AmberBluff amended only the execution schedule after
observing substantial idle CPU, GPU, and RAM capacity. The sequential
coordinator PID 10,906 was terminated without signaling arm 1: its wrapper PID
10,909 and reducer PID 10,917 remained live and were reparented. At the last
pre-amendment checkpoint, arm 1 had reached 36,864/148,628 ordered records at
rank 8,176/128,000 after 3,770.274 seconds; this was not a verdict.

Arm 2 (p=1,000,003, seed 2,026,090,202) then launched under a separate
`nohup` supervisor with wrapper/reducer PIDs 16,346/16,355 and its own output,
logs, and telemetry. The two active arms retain 60 configured column-generation
threads each, all frozen reducer settings, and distinct output prefixes. Their
initial aggregate GPU use was 42,381/95,830 MiB, below the
90,000/95,830 MiB gate. The replacement watcher maintains at most two active
arms (the 120-thread scheduling cap), and launches arms 3 and 4 only as a slot
becomes free. The four primes/seeds, finite subjects, and verdict rule are
unchanged; scheduling changes none of their epistemic meaning.

## Scheduling amendment: split across two H100 boxes

At 2026-09-02T23:30Z AmberBluff reassigned arms 3 and 4 to the H100 PCIe box
at `ssh1.vast.ai:29562` after WildWillow's pass-1 PID 9,055 had exited. The
NVL auto-launch watcher was stopped before it could create either p=1,000,033
arm; NVL arms 1 and 2 were not signaled or otherwise changed.

The registered n=12 universe and order file were copied to the PCIe checkout
and rechecked as
`f98352ea4d1517f0b88aba0b38d34be0edb0b845aac3eaa724f3bd1f8f83f640`
and `691cb0368545f8834c98e891bbb771476e547ce9e140887c9791710a8786a7c1`.
The exact already-gated binary was copied from the NVL box and rechecked as
`cdf835b269d25a37f110d72f16865e6f511d5154b5caf7808dd2eb1d82bc85c3`
(2,361,344 bytes). No WildWillow pass-1 output path was read or written.

Arms 3 and 4 then launched under isolated `nohup` supervisors with 12
column-generation threads each: wrapper/reducer PIDs 13,692/13,704 for seed
2,026,090,201 and 13,798/13,810 for seed 2,026,090,202. All mathematical and
reducer parameters remain frozen. Initial aggregate GPU use was
34,243/81,559 MiB; the PCIe wrapper terminates its own arm at
75,000/81,559 MiB. WildWillow pass-2 PID 13,920 auto-launched just after these
starts and was reported to AmberBluff and WildWillow; NavyTiger did not signal
it or touch its output paths. It was no longer present at the next process
check. A read-only multibox watcher now verifies, copies, and mails each arm
from its assigned box. This scheduling amendment changes neither the four-arm
verdict rule nor the finite modular-sketch no-claim.

## No claim

These trials validate the named machinery on two finite known-answer systems.
They do not decide the n=12 subject, establish exact rational consistency, or
verify an identity on every real row.
