# Upstream verification of the n=11 exact-lift certificates

Bead: `relu-depth-frontier-research-23b`  
Operator: Agent Mail identity `BoldFrog`  
Remote host: `455dc67367ba` via `ssh -p 15464 root@ssh1.vast.ai`  
Remote workspace: `/workspace/relu`  
Status: **n=11 F2 target running** (started `2026-09-03T00:42:20Z`; remote supervisor PID `32659`)

## Scope and unchanged verification semantics

This run imports the authors' pinned `verify_certificate.py` and calls its
`read_pair` and `symmetrized_pair` functions without modification.  The local
driver parallelizes only the outer certificate-term loop and aggregates Python
`Fraction` values exactly.

The bead explicitly allowed at most 60 processes on the 128-vCPU NVL host.
The driver initially refused more than 6, so commit `8cc8ec7` changes only its
worker-ceiling guard from 6 to 60.  The verifier calls, chunk contents, exact
aggregation, residual tests, and verdict rule are unchanged.

| Input/tool | SHA-256 |
|---|---|
| `tools/exactlift/upstream_parallel.py` after scaling-only change | `8acb725f7cee5deb01631d9179e838ba463ea0c0eb78693d719f990a24979e75` |
| pinned upstream `verify_certificate.py` | `d6da3030b719735b10a197dc79d7e311ecc90f70314ed748de81087f94f039a7` |
| n=10 known-answer certificate (402 terms) | `10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4` |
| n=10 equality-destroying mutant (402 terms) | `c27f54bb8d94b069f6f31eb9dd30b9c76150f3cc0a3bd3c3fb221a73d5068734` |
| n=11 F2 target (11,320 terms) | `767f9e66fd3dcb7b5c43e5ffdbbfa50967684d7b263c41cbd7c35e2db7938670` |
| n=11 run7 alternative (15,896 terms) | `8bd2270a801f6af679ccbf00aa7357f4e89ebb069d1211671082f3f5f07d25c5` |

## Environment and launch reconciliation

At `2026-09-03T00:22:23Z`, before adding this workload, the host reported
128 logical CPUs, 251 GiB total RAM, 209 GiB available RAM, and load averages
57.48/55.28/54.74 over 1/5/15 minutes.  Two pre-existing n=12 arms each had a
60-thread setting; this bead used no more than 60 verifier processes.

Remote Python is 3.10.12.  The upstream source imports `tqdm` even though the
parallel driver does not call its progress wrapper.  The base image lacked it.
The campaign already pins `tqdm==4.70.0`; the exact wheel was downloaded,
checked against the campaign-recorded SHA-256
`7f585706bfddbdebf89daac705b2dfcc16890130727d3197ca62c732b4310953`,
installed with `--no-index --no-deps`, and import/version-tested as 4.70.0.

```bash
python3 -m pip download --only-binary=:all: --no-deps tqdm==4.70.0 \
  --dest /tmp/relu-23b-wheelhouse
sha256sum /tmp/relu-23b-wheelhouse/tqdm-4.70.0-py3-none-any.whl
python3 -m pip install --no-index --no-deps \
  /tmp/relu-23b-wheelhouse/tqdm-4.70.0-py3-none-any.whl
python3 -c 'import importlib.metadata, tqdm; print(importlib.metadata.version("tqdm")); print(tqdm.__file__)'
```

## Trial ledger

All 4 completed launch/control trials and the 1 live target trial are recorded;
none were omitted.

1. **Environment trial, aborted before verifier startup.** The first positive-control
   command prefixed `/usr/bin/time -v`; the remote image has no `/usr/bin/time`.
   Exit 127, no report, no certificate terms processed.  The driver itself
   reports monotonic wall time plus parent and child `ru_maxrss`, so no timing
   wrapper was substituted.
2. **Environment trial, aborted before mathematical computation.** The unchanged
   upstream import failed with `ModuleNotFoundError: No module named 'tqdm'`.
   Exit 1, no report, no certificate terms processed.  The pinned dependency
   was then installed as documented above.
3. **Known-answer positive control: PASS.** All 402/402 certificate terms were
   nonzero and processed.  Exact residuals: 0/10 linear coordinates nonzero and
   0 hinge directions nonzero.  Wall time 438.4483312293887 seconds with 60/60
   requested workers.  Parent max RSS 144,584 KiB; child max RSS 26,616 KiB.
   Report SHA-256:
   `2cf706b6badf6e0c732c13ba2d41c9ed00ef8429c76ef128f024128992245e7f`.
4. **Equality-destroying mutant control: expected FAIL.** All 402/402 terms were
   nonzero and processed.  Exact residuals: 9/10 linear coordinates nonzero and
   0 hinge directions nonzero.  Wall time 491.6766019426286 seconds with 60/60
   requested workers.  Parent max RSS 144,724 KiB; child max RSS 26,448 KiB.
   Report SHA-256:
   `20315a0ff4a1a4b010edd82fa4fcfd0bed0aaa162ff377a2c9bd9ea60c3d7f87`.
5. **n=11 F2 target:** started at `2026-09-03T00:42:20Z`, 60/60 requested
   workers, pending.  No verdict is inferred from startup or runtime.

## Exact control commands

Run from `/workspace/relu` on the remote host:

```bash
python3 -B tools/exactlift/upstream_parallel.py \
  --verifier literature/repos/max-relu-certificates/verify_certificate.py \
  --certificate literature/repos/max-relu-certificates/certificates/certificate_10_4.json \
  --workers 60 \
  --output artifacts/math/upstream-verify-n11/n10-pass.json

python3 -B tools/exactlift/upstream_parallel.py \
  --verifier literature/repos/max-relu-certificates/verify_certificate.py \
  --certificate artifacts/math/exact-witness-n9-n10/certificate_10_4_mutated_plus1.json \
  --workers 60 \
  --output artifacts/math/upstream-verify-n11/n10-mutant-fail.json
```

The live target uses:

```bash
python3 -B tools/exactlift/upstream_parallel.py \
  --verifier literature/repos/max-relu-certificates/verify_certificate.py \
  --certificate artifacts/math/n11-stageA-exact-lift/member-F2-forestpair-m64000-p1000003-s1-cuda/member_upstream.json \
  --workers 60 \
  --output artifacts/math/upstream-verify-n11/n11-f2.json
```

## Run7 stop decision

The driver's unchanged core does one full `n!` permutation enumeration per
certificate term.  Scaling the measured positive-control wall time by
`(15,896 / 402) * (11! / 10!)` projects run7 at 52.9749 hours; scaling the
mutant-control wall time projects 59.4062 hours.  Both measured projections
exceed the bead's 12-hour run7 threshold, so run7 is explicitly skipped unless
new contrary timing evidence emerges from the mandatory F2 target.

## No claim

**No claim:** the upstream verifier checks the supplied finite identity in its
own ordered-cone/symmetrization semantics.  Even a PASS for the F2 certificate
would certify only that isolated n=11 identity under those semantics; it would
not prove a construction for any `n > 11`, trainability, efficiency, or any
other statement beyond n=11.  While the F2 run is pending, this artifact makes
no n=11 identity claim at all.
