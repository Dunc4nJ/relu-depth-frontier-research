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

## Target and stopped trials

| ID | Attempt | Outcome | Retained evidence |
|---|---|---|---|
| T7 | Complete n=11 loop-inclusive degree-4 universe plus 4L, CUDA, p=1,000,003, m=32,768, seed 2,026,090,201. | Completed 137,505/137,505 columns: rank 8,667, augmented rank 8,668, NON_MEMBER; separator dot target 176,191; wall 2,675.836 s; high-water RSS 1,791,228 KiB. This is a bounded one-prime modular null. | `n11-loop-degree4-m32768-p1000003-s1-cuda.{json,stderr,stdout}`. |
| T8 | Same complete n=11 run at primary seed 2,026,090,202. | **CANCELLED by orchestrator** after the novelty gate failed: Rueß et al. v1 Corollary 4.3 already proves the degree floor. `SIGTERM` was sent only to the isolated sou process (remote PID 41,829) after 117,760/137,504 universe records; the latest partial rank was 4,209. No 4L was reached, no result JSON was written, and no verdict is assigned. The last observed aggregate H100 allocation was 59,826 MiB, below the 60,000 MiB gate. | Partial `n11-loop-degree4-m32768-p1000003-s2-cuda.stderr`, SHA-256 `96cd9d9d80c16e6e516bc75508780dc831f9d23ebd27a5c2a148202522d1b159`, and empty `.stdout`. |
| T9 | Preregistered n=11 second-prime repeats, p=1,000,033, seeds 2,026,090,201 and 2,026,090,202. | **CANCELLED before launch by orchestrator.** No processes were started and no reports or logs exist. | This log and `RESULT.md`. |
| T10 | Campaign `./skill-runtime verify-quick` at handoff. | Exited 1 with 24 findings in concurrently modified canonical ledger files, including pre-existing SE-10 history findings and E-0057 subject-binding drift. This bead did not edit those forbidden files. The bead-local hash/result assertions and `git diff --check` passed immediately before it. | Terminal result summarized here; canonical files were not changed. |

The stopped suite therefore has one completed target sketch, one partial
sketch with no verdict, and zero second-prime sketches. It does not satisfy
the preregistered two-seed/two-prime decision gate.
