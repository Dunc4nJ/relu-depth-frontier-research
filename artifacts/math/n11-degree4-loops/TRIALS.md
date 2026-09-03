# Trial log

All exploratory, failed, control, and target attempts for bead
`relu-depth-frontier-research-sou` are listed here. Temporary smoke-test files
are explicitly identified; they are not decision evidence.

## Pre-target trials

| ID | Attempt | Outcome | Retained evidence |
|---|---|---|---|
| T0 | First certificate command named nonexistent `literature/repos/max-relu-certificates/certificates/certificate_5_3.json`. | Failed before reading any certificate (`ENOENT`), elapsed 0.02 s, maximum RSS 2,704 KiB; no report. The legacy required input is `certificate_5_2.json`. | This log only. |
| T1 | Retried n=5/n=7/n=8 certificate replay after `cargo test --release`, but before rebuilding the standalone release binary. | The stale binary ignored `--certificate-n8` and emitted only its old 2/2 n=5/n=7 control. Detected by inspecting the row denominator; excluded from evidence. | `upstream-degree3-certificate-replay.prebuild-invalid.json` and `.stderr`. |
| T2 | Local `cargo test --release` and clippy for the loop-aware tool changes. | Colgen-loops 5/5 tests PASS. Streamrank 9/9 tests PASS. Default-feature clippy PASS. `clippy --all-features` could not start because this CPU host has no `nvcc`; this is an environment failure, not a CUDA test result. The isolated H100 CUDA build and smoke test subsequently passed. | Commands and outcome in `RESULT.md`; no separate generated report. |
| T3 | Local CPU n=11 prefix timing, first 1,000/137,504 records, p=1,000,003, m=128, seed 2,026,090,201, four threads, no 4L. | Rank 87, augmented rank 88, prefix-only NON_MEMBER; wall 19.354 s, streamrank high-water RSS 264,168 KiB. Used only to estimate generation time. | Temporary directory intentionally not retained; exact denominator and outcome are recorded here. |
| T4 | Isolated-H100 CUDA smoke test on record zero plus 4L, p=1,000,003, m=64, seed 2,026,090,201. | Rank 2, augmented rank 3, two-column prefix-only NON_MEMBER. Confirmed CUDA linkage, loop-inclusive dispatch, carrier, and report field. | Temporary directory intentionally not retained; binary SHA is frozen in `PREREGISTRATION.md`. |
| T5 | First remote n=10 launch wrapped the command in `/usr/bin/time -v`. | Failed before streamrank because this H100 image has no `/usr/bin/time`; no JSON was created. Its stderr was accidentally reused by the immediate corrected retry, so this narrative is the only retained record. | This log only. |
| T6 | Complete n=10 loop-inclusive degree-4 universe plus 4L, CUDA, p=1,000,003, m=32,768, seed 2,026,090,201. | `CONTROL_PASS`: 136,037/136,037 columns, rank 7,867, augmented rank 7,867, MEMBER; wall 619.079 s, high-water RSS 1,621,052 KiB. | `n10-loop-degree4-m32768-p1000003-s1-cuda.{json,stderr,stdout}`. |

The complete n=11 target attempts are appended after they terminate. A
resource-gated abort remains an outcome and will not be hidden or retuned
without first recording the failed gate.
