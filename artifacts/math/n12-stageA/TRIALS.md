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

## Final known-answer suite

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

## No claim

These trials validate the named machinery on two finite known-answer systems.
They do not decide the n=12 subject, establish exact rational consistency, or
verify an identity on every real row.
