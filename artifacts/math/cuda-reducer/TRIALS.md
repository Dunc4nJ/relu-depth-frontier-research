# CUDA reducer trial log

All counts below name their denominator. These are engineering trials over
finite modular sketches, not exact-Q MAX11 decisions.

- Two pre-control launches of the n=9 command failed before processing 0 / 739
  selected columns because the remote input did not yet exist. No report was
  written. A separate n=10 launch failed locally before SSH because the shell
  misparsed an unquoted `jq` filter; 0 / 12,248 columns were processed.
- Initial CUDA controls (`*-cuda.json`, executable later superseded) completed
  n=9 at 739 / 739 and n=10 at 12,248 / 12,248 for two sketches at each named
  prime. Their ordered pivot hashes matched CPU, but a later large-shape trial
  exposed a latent workspace-size defect. They are retained as history and are
  not the post-fix controls.
- The first production-shaped command below failed after 1,024 / 5,000 columns
  (rank 1,024) with an illegal CUDA access. A diagnostic rerun reproduced it at
  the same denominator. One immediate retry accidentally used the stale release
  CLI after rebuilding only test targets and reproduced the same failure.

```bash
tools/streamrank/target/release/max11-streamrank run-universe \
  --backend cuda \
  --input artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --order-file artifacts/math/stream-rank-engine/n11-random-order-5000-seed20260902.json \
  --n 11 --branch-edges 5 --modulus 1000003 --buckets 96000 \
  --seeds 2026090201 --batch-size 1024 --gemm-block 8192 \
  --rank-panel 64 --threads 24 \
  --output artifacts/math/cuda-reducer/n11-random5000-m96000-p1000003-cuda-b8192.json
```

- `compute-sanitizer --tool memcheck --error-exitcode=99` localized the write
  to `u32_to_f64` during `max11_cuda_apply_panel`: the old-basis target can have
  up to 8,191 columns while the FP64 workspace had capacity for only the 1,024
  streamed columns. The first printed invalid write was 445,185 bytes past a
  786,432,000-byte allocation; memcheck reported 105,796 errors in that failed
  run. No decision report was written.
- Fix: allocate the dense FP64 target as
  `rows * max(batch_size, gemm_block)` and test explicitly with
  `gemm_block > batch_size`. Fixed executable SHA-256:
  `cb138a7cd8e44aac07875416de171902b8bc95e5c5b3e10fd1a9dcfb3eec211f`.
- Corrected controls are `*-cuda-v2.json`; all 8 ordered-pivot comparisons
  (2 systems x 2 sketches x 2 primes) equal the CPU reference hashes. The
  production-shaped command then completed 5,000 / 5,000 source columns and
  produced `n11-random5000-m96000-p1000003-cuda-b8192.json`.
- The first corrected GPU Stage A attempt was attached directly to SSH. The
  transport exited 255 after checkpoint 54,272 / 120,947 order records, rank
  8,326, elapsed 894.960 s. A later process check found no streamrank process
  and no JSON report. This is an infrastructure abort, not a rank result. The
  identical command was relaunched under `nohup` as remote PID 6570 with a
  durable `.log`. That detached retry completed 120,948 / 120,948 columns
  (120,947 ordered universe records plus appended 5L), rank(A) =
  rank([A|b]) = 21,222, MEMBER and unsaturated at 64,000 buckets, modulus
  1,000,003, seed 2,026,090,201. Wall time was 1,728.299779711 s and host
  high-water RSS was 8,053,556 KiB; the reducer reported peak allocated GPU
  storage 15,026,213,376 bytes. The JSON SHA-256 is
  `115818ab415386b32543b2cbc94eab788df3565d012cc279eab003b99cd6c7c0`.
  This is one finite sketch; its ordered pivot-list SHA-256
  `2ac8d1227fb3a66e61f2292a861ec9bdb3fb132c970fcd9e1d7da4c2334b744b`
  remains gated on equality with the still-running CPU reference.
- The first launch guard for Stage A seed 2 used `pgrep -af` and matched the
  remote shell's own command line. It exited 23 before starting streamrank:
  0 / 120,948 columns, with no JSON or log written. The corrected exact-name
  guard (`pgrep -x max11-streamrank`) launched remote PID 7731 under `nohup`.
- That seed-2 retry completed 120,948 / 120,948 columns at modulus 1,000,003:
  rank(A) = rank([A|b]) = 21,222, MEMBER and unsaturated at 64,000 buckets.
  Wall time was 1,718.818657184 s, host high-water RSS 8,014,552 KiB, and
  reported peak allocated GPU storage 15,026,213,376 bytes. Its ordered pivot
  SHA-256 is the same as seed 1,
  `2ac8d1227fb3a66e61f2292a861ec9bdb3fb132c970fcd9e1d7da4c2334b744b`;
  JSON SHA-256 is
  `892b27e657f1344338c0aad66aa8e673e10d25ea2a2da0f2ed94e8ca7c18d1e0`.
  This is the second of two finite sketches at one of two named primes; the
  preregistered Stage A verdict still requires both sketches at modulus
  1,000,033 as well.

No-claim: failures and passes here concern only the named finite modular
sketches and CUDA implementation. They do not establish exact rational
consistency or unrestricted two-hidden-layer representability.
