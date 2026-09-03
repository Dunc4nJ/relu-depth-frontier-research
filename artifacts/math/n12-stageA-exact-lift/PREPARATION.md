# EXP-0037 n=12 exact-lift preparation

Bead: `relu-depth-frontier-research-hhs`

Prepared on 2026-09-03 before any n=12 stage-A arm had reported a verdict.
The trigger remains the first independently verified stage-A `MEMBER` report
with `rank_a = rank_augmented`.

## Compatibility change

`tools/exactlift/prepare_pivot_batches.py` formerly fixed the real-universe
count at 754,017, the n=11 count. It now reads that boundary from
`five_l_carrier.source_index` in the streamrank report. It retains the 754,017
fallback only for historical n=11 reports that predate the carrier field and
fails closed for any non-n=11 report without the field.

Local controls:

```text
python3 tools/exactlift/prepare_pivot_batches.py \
  --pivot-report artifacts/math/n12-stageA-exact-lift/preflight/tiny_member_fixture_n12.json \
  --output-dir $TMP/gather --batch-size 1
```

- n=12 carrier-derived boundary: 787,523/787,523 records.
- n=12 pivot/order recovery: 1/1 column.
- n=12 missing-carrier mutant rejected: 1/1.
- historical n=11 carrier-free fallback recovered 754,017/754,017: 1/1.

## A100 interface preflight

Host: `ssh -p 29562 root@ssh5.vast.ai`, checkout `/workspace/relu`.

Exact invocation (started under `nohup`):

```text
cd /workspace/relu
nohup bash artifacts/math/n12-stageA-exact-lift/run_a100_preflight.sh \
  > artifacts/math/n12-stageA-exact-lift/preflight-a100-v1.supervisor.log \
  2>&1 < /dev/null &
```

Remote interval: `2026-09-03T00:26:03Z` through
`2026-09-03T00:26:07Z`. Verification command after rsync:

```text
python3 artifacts/math/n12-stageA-exact-lift/verify_preflight.py \
  --run-dir artifacts/math/n12-stageA-exact-lift/preflight-a100-v1 \
  --output artifacts/math/n12-stageA-exact-lift/preflight-a100-v1/verification.json
```

Result: `PASS`.

- n=12 colgen emission: 1/1 columns.
- independent order-file replay equal byte-for-byte: 1/1.
- n=12 exact-lift problem builds: 1/1 ELIFTQ02 problems.
- planted n=11 MCOLGEN-header mutant against the n=12 pivot report rejected:
  1/1, with `incompatible dimensions/modulus`.
- fail-closed verifier mutation replay rejected: 1/1.

The first attempt is preserved at
`preflight-a100-attempt0-mutant-ordering-failure/`. It changed the pivot
report's `n`; the builder rejected it earlier because the recomputed target
sketch no longer matched the report, so it did not exercise the intended
batch-dimension check. No result from that aborted attempt is counted above.

## Inputs and outputs

```text
f98352ea4d1517f0b88aba0b38d34be0edb0b845aac3eaa724f3bd1f8f83f640  n=12 universe (787,523/787,523 records)
1b1982a266617ccd419d4874abc596f917bf0396acbafac4d7aa67d3054bb2b1  max11-colgen
a50338c305b8855a4540a8f55c4d21b1b388428223b0f4e3b7c80280c30f0429  max11-lift-large-a50338c3
09b57ad6361e2b240c7f5f3bb1c3fc7f99971cb10a564d7e647b162722d6ac0f  prepare_pivot_batches.py
8b28588564113fe0ee3ea9d79ac3145698f4297e36bfefe7bf5f2c5f46ebb4b6  run_remote_member_pivot.sh
92f225694803219cda59c24b27a5355e1c649d1e9a1fc165b279c278721ef1dd  n=12 structural pivot fixture
f046f105723f8dd40209dfbc13c68c9a17da6bd6f8a3d5db8072f037b382c28a  emitted n=12 MCOLGEN batch
5be39668392913dd047e65d1419e4360a9022e0a2bb6fc28857e8c390939bb4f  built ELIFTQ02 problem
771f3c83739d415de9225e82ef08f55b6d8b4cc519fe84ae733ab03277ad5243  build report
5dda6d10225d538eaa82388c1f8578cb75718c4d618d099b1bdf3ed87e5b859e  preflight verification
```

The authoritative path-qualified hashes are in
`preflight-a100-v1/inputs.sha256` and `preflight-a100-v1/outputs.sha256`.

## Capacity and coordination

At the preflight sample the A100 host reported
2,083,739,856,896/2,151,664,680,960 bytes available host RAM and 0/81,920 MiB
GPU memory used. The exact-lift runner defaults to 16/128 host threads. A
AzureAspen agreed in thread `relu-depth-frontier-research-hhs` to cap this bead
at 16 threads and 64 GiB host RAM while retaining an 80 GiB floor for bead
`relu-depth-frontier-research-psu`. At `2026-09-03T00:46:14Z`, AzureAspen
reported that the 16-thread sketch builder had completed and authorized the
HHS launch to overlap PSU's single-core parity/HiGHS phases under that split.
The resource gate is therefore open; the MEMBER gate is not yet open.

## Trigger path

`launch_a100_member_lift.sh` is fail-closed. It requires the explicit
`RAM_AGREEMENT_CONFIRMED=1` guard, accepts only one of the four preregistered
n=12 arm paths, reruns `verify_outputs.py --one-arm`, checks the universe and
remote binary hashes, requires at least 68,719,476,736 bytes available RAM,
and refuses to start beside another `run_remote_member_pivot.sh`. It then
starts `run_a100_triggered_member.sh` under `nohup`; that wrapper invokes the
existing runner unchanged with 16 threads, prime 65,521, at most 40,000 Dixon
steps, reconstruction every 50 steps, and 1,024-column gather batches.

Preparation controls for the trigger path:

- missing RAM agreement rejected: 1/1.
- planted n=10 pivot-report input rejected as not the n=12, k=5 experiment:
  1/1.
- remote colgen binary hash matched its pinned hash: 1/1.
- remote exact-lift binary hash matched its pinned hash: 1/1.

The trigger has no positive full-arm control yet because no n=12 arm report
exists. Its first positive invocation will therefore be retained in full,
including the wrapper PID, timestamps, exit code, and pipeline log.

`verify_member_lift_outputs.py` is ready for the completed run. It rehashes the
build, solver, witness, pivot, and upstream JSONs; requires every stored exact
row numerator to equal its named denominator; recomputes the coefficient
denominator LCM; and checks coefficient-for-coefficient agreement across the
witness and upstream translation. Against the existing exact n=11 member it
accepted 146,187/146,187 real rows, 162,091/162,091 combined rows, and 11,320
nonzero terms out of 15,904 pivot columns. A planted decrement of the real-row
verification numerator was rejected: 1/1 mutants.

After launch, `monitor_a100_member_lift.sh` watches the wrapper receipt, copies
only the small custody/JSON/log outputs (not the multi-gigabyte ELIFTQ02 problem
or exact-column batches), runs the custody verifier, and sends the verified
upstream path and SHA-256 to IndigoCarp. Its not-yet-launched control returned
the expected refusal: 1/1.

## No claim

This one-column structural preflight did not run `solve-big`, Dixon recovery,
finalization, or upstream translation. It is not an n=12 membership result, an
exact identity, or a successful rational lift. Even a future verified n=12
witness would establish only a finite identity at n=12.
