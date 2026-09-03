# relu-depth-frontier-research-kwa — loopless degree-4 signed-W span at n=11

## Result

`NON_MEMBER` in both preregistered 64,000-row sketches over the single prime
`p = 1,000,003` for the finite loopless degree-4 signed-W family described
below, with the degree-4 linear carrier `4L` added explicitly.

The serialized universe contains 18,285 signed-graph orbit representatives,
including record 0 (`4E`). Adding the external `4L` carrier gives a source
matrix with **18,286 columns**. Both CUDA sketches returned

| seed | rank(A) / rows | rank([A|MAX_11]) / rows | verdict | separator dot MAX_11 mod p |
|---:|---:|---:|---|---:|
| 2026090201 | 3,514 / 64,000 | 3,515 / 64,000 | NON_MEMBER | 176,191 |
| 2026090202 | 3,514 / 64,000 | 3,515 / 64,000 | NON_MEMBER | 844,447 |

Neither rank saturated the 64,000-row sketch. Both reports have the same
pivot-column hash,
`f1c3705626e995648c8ac5427ab15858408ce9ca516d8648145fd7e7ed52687d`.
The report checker replayed the stored separator/target dot products, checked
all 3,514 named basis columns per sketch, checked report and input hashes, and
rejected a planted rank-gain mutant.

Per the work order, no second prime was run because the result was
`NON_MEMBER`, not `MEMBER`.

## Claim boundary / no-claim

This is a **bounded one-prime modular null** for exactly 18,286 named columns:
the exhaustive loopless degree-4 signed-W quotient at n=11 (18,285 serialized
representatives, record 0 included) plus the external `4L` carrier. It is not a
characteristic-zero or rational nonmembership proof, not a claim that the
18,285 orbit representatives define distinct functions, not a lower bound for
an unrestricted two-hidden-layer network, and not a result about degree 5 or
arbitrary ansatzes. Byte hashes and enumeration checks are custody evidence,
not mathematical verification of those stronger statements.

## Universe and carrier definitions

The enumerator is a degree-4 adaptation of
`artifacts/math/G-0027/enumerate_signed_loopless.py`. It preserves the six-field
record schema:

`abs_beta`, `abs_components`, `active_vertices`, `negative_edges`,
`positive_edges`, `signed_mass`.

It quotients loopless signed multigraphs by coordinate relabeling and global
branch/sign reversal. Its graphwise nauty traversal count is checked against
an independent Burnside count in every `(signed_mass, active_vertices)`
stratum.

- Record 0 is `4E`, the degree-4 analogue of G-0027's `5E`: four common
  loopless edges. At n=11 colgen emits the exact linear vector
  `[0, 2903040, 5806080, ..., 29030400]` and no hinges.
- `4L` is the degree-4 analogue of `5L`: four common loops. It is not a
  loopless signed-W record, so streamrank appends it as source column 18,285.
  At n=11 it is the all-ones linear vector with coefficient
  `4*(11-1)! = 14,515,200` in each of 11 coordinates and no hinges.

The generic `kL` implementation and tests were committed separately as
`c958975` (`relu-depth-frontier-research-kwa: add generic kL carrier support`).
The legacy `--include-five-l` behavior is preserved and rejects k=4; the new
`--include-linear-carrier true` selects the `kL` carrier for the named branch
degree.

### Enumeration census and custody

| n | uncoloured absolute multigraphs | signed orbit records | universe SHA-256 | record-stream SHA-256 | verification SHA-256 |
|---:|---:|---:|---|---|---|
| 9 | 2,354 | 16,311 | `cbc54f11b4a080738b93c3228a2dc014908a09f073411fe8cf2574e252932fb5` | `61861ef72ab8c87b571dae1a42747bf173c8d839f4fb606bd6c3f41ebb6de98c` | `c4e9597c0f669ab61f056bc1d15ad62e7938d6aa1314a292eeb42d6631abca6b` |
| 10 | 2,520 | 17,775 | `8c84fa2104be9ac329290f901dfa544b42b8914b623f4e51c411c28f3c43c6a0` | `a94760212b6a29734a4b5348bfc1f0228b643a205ebd3da722cb196c335cd722` | `3fdbb36e1ef89469ea607082399e78be75728cf4c870215b80c256fdb80e27b8` |
| 11 | 2,585 | 18,285 | `72d0f4b53b8bd7584987eb9a4f11816db25e046e5a84b0fdb800e3beea3a400c` | `721ba7c97465985f9daea4f39c3617a837b7419e6ff073c870c11be566f9c7f2` | `05af7978601fd2b779baeb2d9cc95e2fbf00e55e75be4d736cc890d26e4ccb53` |

Producer SHA-256:
`4270f39dd2f9a99f847c3b93afa9a2d67444f54748c12eeebe80e6d3112a1f57`.
Independent verifier SHA-256:
`005f6250a25e0e443c929a73e63f711a3d80d7bd2a620015e0cb91ce23649e52`.
The G-0027 source hash is embedded in every universe report as
`92ce1d017a12ce9dc44c3f43103028dcfe635fa7ba9e8c1026c3d6ca8fe19f13`.

All three universe verifications passed record invariants, topology replay,
record-stream hashing, per-stratum traversal/Burnside equality, literal
canonicalization on all mass-at-most-two records, deterministic IR
relabel/global-sign tests, and rejection of a planted loop mutation.

## Known-answer controls

The expected answers were kept fixed throughout: n=9 rank 1,506 and MEMBER;
n=10 rank 2,166 and MEMBER. No expected rank or verdict was changed after a
run.

### Existing saved-system controls

`max11-colgen validate-templates` exactly reproduced all 10,976 / 10,976 n=9
templates and 12,248 / 12,248 n=10 templates from the AmberBluff handoff:

| n | input SHA-256 | exact matches / templates | validation report SHA-256 |
|---:|---|---:|---|
| 9 | `729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991` | 10,976 / 10,976 | `8115fafd7985643cf6e575ed9f4e097212872e8149b9964313a1e9468ea0d501` |
| 10 | `bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18` | 12,248 / 12,248 | `834232317eab0a3b4d5bd87aeb496b2974cb3bde8c79a9b9beb8838f43758d34` |

CPU streamrank results over those saved systems:

| n | rows | source columns | seeds | rank(A) / rank(augmented) | result | report SHA-256 |
|---:|---:|---:|---|---|---|---|
| 9 | 8,192 | 10,976 | 2026090201 / 2026090202 | 1,506/1,506 and 1,505/1,505 | CONTROL_FAIL (sketch collision) | `1405948b8ebe2a42b94113bbf1edafe5e2bf42ecbc4d33cb159254f4c21beb1b` |
| 9 | 16,384 | 10,976 | 2026090201 / 2026090202 | 1,506/1,506 and 1,506/1,506 | CONTROL_PASS | `2eadbf124212b9d0c06a44f9113a7884b03a5196cc445c37450a85f6e4cb9fde` |
| 10 | 8,192 | 12,248 | 2026090201 / 2026090202 | 2,166/2,166 and 2,166/2,166 | CONTROL_PASS | `858267b967f72cb20eeb647eede91da924fc5eb4ff45de2a1a70be59459ba433` |

The first n=9 two-sketch attempt is deliberately retained as a failed
control. Its second 8,192-row sketch had a deterministic rank collision. The
retry increased only the sketch row count to 16,384; the expected 1,506 rank,
MEMBER verdict, prime, input, and seeds were unchanged.

### Controls through the newly enumerated universes

To exercise the new serializer and `run-universe` path directly against the
same known degree-4 answers, `make_simple_orders.py` selected the simple-edge
subfamily (maximum edge multiplicity at most one) while retaining record 0.

| n | selected / full universe | order SHA-256 | rows | two-sketch ranks | result | report SHA-256 |
|---:|---:|---|---:|---|---|---|
| 9 | 6,197 / 16,311 | `5a0bef2caebad03f09dcc10c440e3036c77e8f569b0d4bd4d2883823058d6c44` | 16,384 | 1,506 / 1,506 in both | CONTROL_PASS, MEMBER | `f696874f087b4a06472ff3133cd50785bb1c59ffb5abd0f4ff736501d17cc50e` |
| 10 | 7,203 / 17,775 | `4b83228cc5e72d5848598e6ccdcc176a7ad453a3c2024db80c542b87aa71aec9` | 8,192 | 2,166 / 2,166 in both | CONTROL_PASS, MEMBER | `4b338d29dd44d7c172feda9b5cb820ca3900f1221907edad167fa0442bdcb6d5` |

These are positive controls. Negative-direction controls also passed: the
universe verifier rejected a planted self-loop, the result verifier rejected a
planted rank-gain mutation, and the CLI rejected the incompatible legacy `5L`
flag at branch degree 4.

## n=11 CUDA observations and verification

The H100 preflight used `nvidia-smi` and identified the protected n=12 arms and
lift-test processes before launch. Free-memory observations during scheduling
were 23,979 MiB, then 17,979 MiB, and 13,979 MiB at the combined-sketch attempt.
No protected process was signalled, stopped, reniced, overwritten, or otherwise
modified. At most eight streamrank threads were used. A later external job
release left 39,101 MiB free before seed 2026090202.

The isolated CUDA build was made under
`/workspace/relu/artifacts/math/n11-degree4/build-c958975/` from the separately
committed carrier patch and the then-certified streamrank CUDA sources. Binary
SHA-256:
`73d1964bfca6f34c220c3ed6c4e8a228f8d855c63653bdf22780a9a264a5851b`.
The relevant source hashes were:

- colgen lib:
  `9b7a3af7328d543c6791d9d983aaf97af7a2be232f459beccaf443e3668081e1`
- colgen main:
  `1cb685be4e8a6b96c1ce056453b3671c53eabcd3a87dc7fd6a5f34456742ebc0`
- streamrank main:
  `73a4371335ef85b3ffc19bf574e99c2a9e6a7922064368cc80026ce27bda14a9`
- streamrank lib:
  `7d0139fa7c1b6c26c65884b27f3687e0242a08f39ce3d154767b266e47c3d387`
- streamrank CUDA:
  `3bcea1727b56d0ca4ad502bf9f40af90204044f42a48dbd0f5c3d42651b3a6b6`

These hashes are reproducible directly from Git commit `c958975`; the
downloaded JSON reports plus binary and universe hashes are the result custody
anchors.

The first two-sketch process attempted `--seeds 2026090201,2026090202` and
failed before producing a rank because `cudaMalloc` exhausted the 13,979 MiB
then free. Its stderr is retained with SHA-256
`10cd856c5fa0fcf45152cb82a76b399fa66e2514d56dcc61d3b33ecf08c958c1`.
Following the documented low-headroom path, the exact same two seeds were then
run one process at a time. Each used `m=64000`, p=1,000,003, batch size 1,024,
GEMM block 8,192, rank panel 64, eight threads, CUDA, and the explicit `4L`
carrier.

| seed | wall seconds | max RSS KiB | JSON SHA-256 | stderr SHA-256 |
|---:|---:|---:|---|---|
| 2026090201 | 165.150 | 1,694,412 | `5181da9acf2105ca825fe3534b827faa675a611740caee0443039dcda6b1b563` | `d19a495ddacffb66df1926c28392bc5d2e206985ec7feb2a5cd97bc82ce7d942` |
| 2026090202 | 159.227 | 1,727,648 | `90764bbf7fa56a8ff2c926395b34b852d926232ccf5ee2dc96c0a58d4b222309` | `b008c3683746138874b0724754753137f6fa173beb89f4cd172ef8db78a57e0d` |

`verify_streamrank_results.py` was frozen with the first seed's observed rank
before the second seed completed. The second seed independently matched the
frozen expected ranks and verdict. Verification report SHA-256:
`2ebba241eaf9962feca5d22cf814ac3e6f0e6130e0759d6e3f905233f22281e3`;
verifier SHA-256:
`c5ed687efa34f5d91c55ebb2c92921a73a4bfc3574b1f90cef3ebeabe38f7162`.

## Commands

The JSON result files preserve their generating command arrays verbatim. The
principal local commands were:

```sh
python artifacts/math/n11-degree4/enumerate_signed_loopless.py --n 9 --output artifacts/math/n11-degree4/loopless_signed_degree4_universe_n9_v1.json.gz
python artifacts/math/n11-degree4/enumerate_signed_loopless.py --n 10 --output artifacts/math/n11-degree4/loopless_signed_degree4_universe_n10_v1.json.gz
python artifacts/math/n11-degree4/enumerate_signed_loopless.py --n 11 --output artifacts/math/n11-degree4/loopless_signed_degree4_universe_n11_v1.json.gz

python artifacts/math/n11-degree4/verify_signed_universe.py --universe artifacts/math/n11-degree4/loopless_signed_degree4_universe_n11_v1.json.gz --producer artifacts/math/n11-degree4/enumerate_signed_loopless.py --output artifacts/math/n11-degree4/loopless_signed_degree4_universe_n11_verification_v1.json

tools/colgen/target/release/max11-colgen validate-templates --input handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz --n 9 --branch-edges 4 --threads 4 --output artifacts/math/n11-degree4/colgen_validate_n9.json
tools/colgen/target/release/max11-colgen validate-templates --input handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz --n 10 --branch-edges 4 --threads 4 --output artifacts/math/n11-degree4/colgen_validate_n10.json

python artifacts/math/n11-degree4/verify_streamrank_results.py --universe artifacts/math/n11-degree4/loopless_signed_degree4_universe_n11_v1.json.gz --reports artifacts/math/n11-degree4/n11-degree4-m64000-p1000003-s2026090201-cuda.json artifacts/math/n11-degree4/n11-degree4-m64000-p1000003-s2026090202-cuda.json --output artifacts/math/n11-degree4/n11-degree4-streamrank-verification-v1.json
```

The successful remote seed commands (run from `/workspace/relu`) were:

```sh
artifacts/math/n11-degree4/build-c958975/target/release/max11-streamrank run-universe --backend cuda --input artifacts/math/n11-degree4/loopless_signed_degree4_universe_n11_v1.json.gz --n 11 --branch-edges 4 --modulus 1000003 --buckets 64000 --seeds 2026090201 --batch-size 1024 --gemm-block 8192 --rank-panel 64 --threads 8 --include-linear-carrier true --output artifacts/math/n11-degree4/n11-degree4-m64000-p1000003-s2026090201-cuda.json

artifacts/math/n11-degree4/build-c958975/target/release/max11-streamrank run-universe --backend cuda --input artifacts/math/n11-degree4/loopless_signed_degree4_universe_n11_v1.json.gz --n 11 --branch-edges 4 --modulus 1000003 --buckets 64000 --seeds 2026090202 --batch-size 1024 --gemm-block 8192 --rank-panel 64 --threads 8 --include-linear-carrier true --output artifacts/math/n11-degree4/n11-degree4-m64000-p1000003-s2026090202-cuda.json
```

Exact `run-saved` and n=9/n=10 `run-universe` control commands, including all
expected values and output paths, are the top-level `command` arrays in their
respective JSON reports.

## Complete trial log, including nulls and aborts

1. Local colgen release tests passed 6/6 and clippy passed for all targets and
   features.
2. Local streamrank release tests passed 5 library tests and 1 main test;
   clippy passed for all targets without CUDA. A local all-features clippy
   attempt failed because this host has no `nvcc`; no CUDA correctness claim
   was taken from that host.
3. The isolated remote CUDA build passed all 6 library tests, including CPU/CUDA
   pivot and reduction agreement, plus the main carrier test. The first remote
   cargo invocation failed because `cargo` was absent from non-login `PATH`; it
   was rerun after `source /root/.cargo/env` without changing tests.
4. The first carrier smoke used a stale pre-build local binary and emitted only
   `4E`; it is retained as `carrier_4e_4l_smoke.jsonl`. After an explicit
   release build, `carrier_4e_4l_smoke_v2.jsonl` emitted both exact `4E` and
   `4L` columns. An initial hostile-flag shell wrapper also used zsh's read-only
   variable name `status`; rerunning it with `exit_code` confirmed the intended
   k=4 rejection of legacy `--include-five-l`.
5. Enumeration/verification at n=9, n=10, and n=11 passed. No enumerated stratum
   or record was dropped after inspection.
6. Saved-system n=9 at 8,192 rows failed the exact-rank control in seed
   2026090202 (1,505 rather than 1,506). The failed report is retained. The
   unchanged control passed at 16,384 rows. Saved-system n=10 passed at 8,192.
7. The newly enumerated simple-edge subfamilies passed the n=9 and n=10 known
   MEMBER controls in both seeds.
8. The first combined two-sketch H100 process aborted on CUDA allocation before
   any rank result. Sequential one-seed processes with the same prime, row
   count, seeds, universe, and carrier both completed and agreed.
9. n=11 result verification passed, including the rank-gain mutant rejection.
   No second prime was attempted because the work order conditioned it on a
   MEMBER result.

## Handoff

The substantive yield is a new bounded obstruction: over p=1,000,003, each of
two named 64,000-row sketches separates MAX_11 from the named 18,286-column
loopless degree-4-plus-`4L` family by one rank. Promotion, broader interpretation,
or bead closure remains with orchestrator AmberBluff.
