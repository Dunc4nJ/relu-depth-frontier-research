# Exact rational witness recovery for n=9 and n=10

Bead: `relu-depth-frontier-research-max11-root-gmp.2`  
Agent: `AzureAspen`  
Prime used for basis selection: `p = 1,000,003`

## Result

The modular-pivot/minor/Dixon pipeline recovered new exact rational witnesses
from both saved systems.

- n=9: rank `1,506/10,976` columns modulo `1,000,003`; recovered support
  `415/10,976` columns; exact residual zero on `6,335/6,335` saved rows
  (`6,326/6,326` hinge and `9/9` linear). The coefficient-denominator LCM is
  `326,592,000 = 2^9 * 3^6 * 5^3 * 7`. Witness SHA-256:
  `fa7f80281c9795e5a755cb490d5d9e4ae862ef43493c89ff1f7270b281053b13`.
- n=10: rank `2,166/12,248` columns modulo `1,000,003`; recovered support
  `424/12,248` columns; exact residual zero on `16,719/16,719` saved rows
  (`16,709/16,709` hinge and `10/10` linear). The coefficient-denominator LCM
  is `304,819,200 = 2^10 * 3^5 * 5^2 * 7^2`, exactly equal to the pinned
  upstream n=10 certificate's LCM. Witness SHA-256:
  `bc7a60476c4d06e72d2da0013c1a156ec69e81b6b7fb378536e311cfb4fe88f2`.

Both denominators satisfy the stated divisibility controls: `2` divides both
LCMs for n>=5, and `3` divides the n=10 LCM. Every equality above was checked
with exact rational arithmetic, not floating residuals.

The recovered JSON was translated back to the upstream one-based endpoint
format. The recovered n=9 certificate passed the pinned upstream CLI directly
on `415/415` nonzero terms (`OK`, exit `0/1`, `14:32.49` wall seconds format,
`870.16` CPU seconds, `22,832` KiB peak RSS). The recovered n=10 certificate
passed an exact six-worker outer-loop wrapper on `424/424` nonzero terms, with
zero hinge and linear residuals in `1,659.8585` seconds. That wrapper imports
the pinned upstream `read_pair` and `symmetrized_pair` functions unchanged and
records verifier SHA-256
`d6da3030b719735b10a197dc79d7e311ecc90f70314ed748de81087f94f039a7`;
it does not read the saved systems or import the new verifier.

## Inputs and implementation hashes

- n=9 system (`10,976/10,976` columns):
  `729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991`
- n=10 system (`12,248/12,248` columns):
  `bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18`
- pinned n=9 upstream certificate (`337/337` terms):
  `4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88`
- pinned n=10 upstream certificate (`402/402` terms):
  `10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4`
- `tools/exactlift/exactlift.py`:
  `cce468977855acbecf84003092a9560c3d77a4cbed69aab739cbba07de313acd`
- `tools/exactlift/upstream_parallel.py`:
  `626ce5c4e71803f6e1b383ccda099db434f9ab3100aec3ff043f92d2ebb34082`

## Commands

All Python commands ran after `source .venv/bin/activate`.

```bash
python -m unittest discover -s tools/exactlift -p 'test_*.py' -v

python tools/exactlift/exactlift.py translate-upstream \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --certificate literature/repos/max-relu-certificates/certificates/certificate_9_4.json \
  --output artifacts/math/exact-witness-n9-n10/upstream_n9_translated_witness.json
python tools/exactlift/exactlift.py translate-upstream \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --certificate literature/repos/max-relu-certificates/certificates/certificate_10_4.json \
  --output artifacts/math/exact-witness-n9-n10/upstream_n10_translated_witness.json

python tools/exactlift/exactlift.py recover \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --n 9 --prime 1000003 \
  --basis-cache artifacts/math/exact-witness-n9-n10/n9_basis_p1000003.json \
  --output artifacts/math/exact-witness-n9-n10/recovered_n9_witness.json \
  --report artifacts/math/exact-witness-n9-n10/recovered_n9_report.json
python tools/exactlift/exactlift.py recover \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --n 10 --prime 1000003 \
  --basis-cache artifacts/math/exact-witness-n9-n10/n10_basis_p1000003.json \
  --output artifacts/math/exact-witness-n9-n10/recovered_n10_witness.json \
  --report artifacts/math/exact-witness-n9-n10/recovered_n10_report.json

python tools/exactlift/exactlift.py to-upstream \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --witness artifacts/math/exact-witness-n9-n10/recovered_n9_witness.json \
  --output artifacts/math/exact-witness-n9-n10/recovered_n9_upstream.json
python tools/exactlift/exactlift.py to-upstream \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --witness artifacts/math/exact-witness-n9-n10/recovered_n10_witness.json \
  --output artifacts/math/exact-witness-n9-n10/recovered_n10_upstream.json

env TQDM_DISABLE=1 /usr/bin/time -v .venv/bin/python \
  literature/repos/max-relu-certificates/verify_certificate.py \
  artifacts/math/exact-witness-n9-n10/recovered_n9_upstream.json
python tools/exactlift/upstream_parallel.py \
  --verifier literature/repos/max-relu-certificates/verify_certificate.py \
  --certificate artifacts/math/exact-witness-n9-n10/recovered_n10_upstream.json \
  --workers 6 \
  --output artifacts/math/exact-witness-n9-n10/recovered_n10_upstream_parallel_verify.json
```

## Controls in both directions

1. Positive translation controls: the pinned upstream witnesses translated to
   `337/10,976` n=9 columns and `402/12,248` n=10 columns, then passed the new
   exact verifier on `6,335/6,335` and `16,719/16,719` saved rows respectively.
2. Negative coefficient control: adding exactly `1/1` to the first nonzero
   n=10 upstream coefficient failed the new exact verifier. It left `9/10`
   nonzero linear residual rows; for example row `1/10` had residual
   `322,560/1`. No tolerance was used.
3. Negative family control: the beta-zero union-spanning-tree n=9 subfamily
   contains `739/10,976` saved columns. At `p=1,000,003`, its rank is
   `360/739`, while adjoining the target raises rank to `361/740`; the pipeline
   therefore reported INCONSISTENT and produced no witness.
4. Upstream-wrapper controls: on the pinned n=5 certificate the direct CLI and
   wrapper both passed `3/3` terms. After a `+1/1` coefficient mutation, both
   failed; the wrapper found exact residuals `24/1`, `72/1`, and `144/1` on
   `3/5` linear rows.
5. Unit controls: `3/3` tests passed, including a synthetic exact member, its
   exact coefficient mutation, and modular-basis-to-Dixon recovery.

## Timing and scale boundary

- n=9 full run: `99.5486` seconds total; rank-`1,506` Dixon solve `3.8148`
  seconds; peak RSS `893,168` KiB.
- n=10 full run: `426.5039` seconds total; full modular RREF `227.8891`
  seconds; rank-`2,166` Dixon solve `11.1576` seconds; peak RSS `2,621,608`
  KiB.
- n=10 cached-basis isolation: exact-minor gather `20.5764` seconds,
  rank-`2,166` Dixon solve `11.9408` seconds, `76.7979` seconds including
  full-row replay, peak RSS `363,856` KiB. The witness was byte-identical to
  the full run (`bc7a604...f4fe88f2`).

A deliberately naive cubic time extrapolation of the isolated Dixon solve is
`2.61` hours at rank `20,000`, `8.81` hours at rank `30,000`, and `20.89`
hours at rank `40,000`; these are estimates with denominator one measured
rank-`2,166` run, not benchmarks. Quadratically scaling the current dense
Python/FLINT memory footprint gives about `29.6` GiB, `66.6` GiB, and `118.3`
GiB at those ranks. Therefore this dense implementation does not fit a 60 GiB
machine at rank `30,000` or `40,000`. The fallback is multi-modular solving and
CRT/rational reconstruction with one modular matrix/block resident at a time,
plus a sparse/out-of-core exact gather; the next scale bead must benchmark this
rather than treating the extrapolation as fact.

## Logged aborted trial

The direct single-core n=10 upstream CLI run was interrupted after `15:56.12`
wall time and `953.70` CPU seconds (exit `130/255`, peak RSS `23,184` KiB),
before any verdict. Extrapolation from the completed direct n=9 run made the
remaining multi-hour cost disproportionate. It was replaced by the six-worker
wrapper above only after the wrapper matched the pinned CLI on both n=5 control
arms. This aborted run is not counted as verification.

## No-claim

These are exact positive certificates for the two finite saved loopless systems
at n=9 and n=10, and the translated certificates pass the pinned upstream
semantics. They do **not** test or decide n=11, do not estimate the n=11 rank,
do not prove that a rank-20,000-or-larger exact lift will fit, and do not prove
anything about an unrestricted MAX11 representation or lower bound.
