# EXP-0037 arm 3 restart amendment

Bead: `relu-depth-frontier-research-max11-root-gmp.16`

This changes scheduling only. The preregistered arm parameters and the
four-arm verdict rule are unchanged.

## Preserved aborted attempt

H100 PCIe arm 3 (`p=1,000,033`, seed `2026090201`) started at
`2026-09-02T23:30:01Z`. Its last completed progress receipt was
37,888/148,628 columns at rank 8,199. At `2026-09-03T00:46:17Z`, its wrapper
observed 77,956/81,559 MiB aggregate GPU use, above its 75,000 MiB gate, sent
SIGTERM, and recorded `STREAMRANK_EXIT=143 EXTERNAL_ABORT=1`. The arm wrote no
result JSON and therefore has no verdict.

That external gate is the actual cause recorded by the arm. A separate
degree-4 CUDA run reportedly hit `cudaMalloc` OOM at approximately the same
time, making cross-run GPU-memory contention the likely reason the aggregate
gate was crossed. Arm 3's own stderr contains no CUDA allocation failure.

The complete small-file record is preserved under
`attempt-02-h100-arm3-gpu-gate-abort/`; `TRIAL.json` records it as an aborted
trial excluded from all verdict counts.

## Restart

Arm 3 restarted from column zero on the H100 NVL box at
`2026-09-03T00:56:48Z` using the unchanged mathematical parameters and the
NVL wrapper's 60-thread setting:

```text
nohup bash artifacts/math/n12-stageA/run_remote_arm.sh \
  1000033 2026090201 \
  n12-stageA-m128000-p1000033-s2026090201-cuda \
  > artifacts/math/n12-stageA/n12-stageA-m128000-p1000033-s2026090201-cuda.supervisor.log \
  2>&1 < /dev/null &
```

- NVL wrapper PID: 35070.
- NVL streamrank PID: 35079.
- replacement multibox watcher PID: 727714, held by tmux session
  `navy-n12-arm-watch`.
- streamrank binary SHA-256:
  `cdf835b269d25a37f110d72f16865e6f511d5154b5caf7808dd2eb1d82bc85c3`.
- universe SHA-256:
  `f98352ea4d1517f0b88aba0b38d34be0edb0b845aac3eaa724f3bd1f8f83f640`.
- order SHA-256:
  `691cb0368545f8834c98e891bbb771476e547ce9e140887c9791710a8786a7c1`.

Immediately before launch, NVL aggregate GPU use was 65,306/95,830 MiB.
The wrapper retains its 90,000/95,830 MiB external abort gate. H100 arm 4 and
the ksi run were not touched, and no new H100 process was launched.

## No claim

The aborted attempt supplies no verdict. Restarting on another box changes
only scheduling; it does not change any prime, seed, order, sketch size,
column family, or preregistered decision rule.
