# Recorded execution environments for the n=11 rung

The code and data manifests were regenerated exclusively from committed blobs at
Git tree anchor `392aeb609118b8218ee0fb8c9b9a0b739fba2f3a`; every listed digest was
computed from `git show <anchor>:<path>`, never from the working tree.

This file is a custody snapshot, not provider authentication. It records only
environment facts present in the source artifacts and AmberBluff's dated bead
records.

- Stage-A modular arms: rented H100 CUDA environment; `m=64,000`; primes
  `1,000,003` and `1,000,033`; seeds `2,026,090,201` and `2,026,090,202`;
  the four JSON reports record CUDA backend and 24 requested threads. The CPU
  cross-check report's backend field is absent and therefore reads as null; its
  CPU attribution comes from the command/path, and its report records six threads.
- Exact lift run7: rented A100 environment; binary attribution
  `max11-lift-large-a50338c3`; prime `65,521`; 16 OpenBLAS threads. The solver
  report records 1,319 seconds and 15,406,352 KiB peak RSS, equal to 14.7 GiB.
  The source record says the report bytes were identical after transfer to the
  campaign host.
- T1: campaign shared host; `max11-verify11` release build; four Rayon threads.
  The verifier used exact integer/rational arithmetic and no modular primes.
- T2 independent verifier: fresh scratch build attributed to a Claude Opus
  referee subagent; four threads. The report records 2,832.516966189 seconds.
- T2 lattice falsifier: campaign shared AMD EPYC host, 16 cores, Linux
  6.17.0-14-generic; `.venv/bin/python`, CPython 3.13.7, NumPy 2.5.2; four
  processes. The first PASS used lattice tool SHA-256
  `4e812678c137ecdab34fbe0d75c02fa8aac52d9ca54980b72f460c71bf779b01`;
  the tool changed during review and the rerun PASS used SHA-256
  `e8175f87cc131ce032a185afa7a387ab532608cee606dd21afec15a5ee3ae89b`.
- Degree-4 modular runs: rented H100 CUDA environment, eight threads, prime
  `1,000,003`, `m=64,000`, with seeds `2,026,090,201` and `2,026,090,202`
  run sequentially after the combined process hit the recorded CUDA allocation
  abort.
- Class-sum runs: campaign `.venv`; exact integer/rational verification plus
  primes `1,000,003` and `1,000,033`; `OMP_NUM_THREADS=2`,
  `OPENBLAS_NUM_THREADS=2`, and `MKL_NUM_THREADS=2` in the retained commands.

No line here establishes provider identity, pristine-host isolation, or a
complete transitive shared-library inventory.
