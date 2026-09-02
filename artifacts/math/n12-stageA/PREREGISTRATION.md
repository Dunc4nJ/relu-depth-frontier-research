# EXP-0037 preregistration: n=12 loopless stage A

Frozen before any EXP-0037 control or subject run on the rented H100 NVL box.
This file fixes the finite subject, four modular arms, decision rule, controls,
and abort rules. It must not be edited in response to results.

## Subject

- Universe: `artifacts/math/n12-universe/loopless_signed_degree5_universe_n12_v1.json.gz`,
  SHA-256 `f98352ea4d1517f0b88aba0b38d34be0edb0b845aac3eaa724f3bd1f8f83f640`,
  787,523 records.
- Order: `artifacts/math/n12-universe/stage_a_order_n12_v1.json`,
  SHA-256 `691cb0368545f8834c98e891bbb771476e547ce9e140887c9791710a8786a7c1`,
  148,628 indices: record 0 first, then exactly the nonzero `s=5,
  abs_beta<=1` records.
- Append the engine's one 5L carrier with `--include-five-l true`, for a total
  denominator of 148,629 columns.
- Rows: all touched hinge directions plus 12 linear rows. Target linear part:
  `e_12` under the engine's existing MAX convention.
- Generator/reducer source: Git commit
  `fcdba82916e1958851767741d0e1f790ce445b2d`, with the `tools/streamrank`
  and `tools/colgen` trees byte-checked on the remote box before building.

## Four arms

The Cartesian product is fixed before observation:

- primes: 1,000,003 and 1,000,033;
- sketch seeds: 2,026,090,201 and 2,026,090,202;
- buckets `m=128,000`, one seed per CUDA process;
- batch size 1,024, GEMM block 8,192, rank panel 64, CUDA backend, and at most
  60/64 CPU threads for column generation.

An arm is eligible for a verdict only after processing 148,629/148,629
columns. It is unsaturated only if `rank(A) <= 127,000/128,000`; otherwise its
verdict is `SATURATED` and the preregistered response is a new run at `2m`, not
reinterpretation. The stricter resource gate aborts after a batch if any
sketch rank exceeds 100,000/128,000. Host high-water RSS is gated at
230,686,720 KiB; GPU memory is monitored, with 90,000/95,830 MiB the external
termination threshold.

For each completed arm:

- `MEMBER` means `rank(A)=rank([A|b])` in that named finite sketch and prime;
- `NON_MEMBER` means `rank([A|b])=rank(A)+1` in that named finite sketch and
  prime, with the emitted separator retained;
- disagreement, an abort, rank above 100,000, or saturation prevents the
  four-arm aggregate verdict.

Aggregate `MEMBER` or `NON_MEMBER` is reported only when all 4/4 completed,
unsaturated arms agree. Every arm's ordered pivot-list SHA-256 is reported.

## Known-answer gates on the exact remote binary

Before subject launch, both CPU and CUDA backends of the same CUDA-feature
binary run both seeds at both primes on both saved systems:

- n=10 all columns: 12,248/12,248 columns, rank pair 2,166/2,166, `MEMBER`;
  input SHA-256
  `bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18`;
- n=9 union-trees: 739/739 selected columns, rank pair 360/361,
  `NON_MEMBER`; input SHA-256
  `729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991`.

The gate requires the expected ranks/verdicts and byte-identical ordered
pivot SHA-256 between CPU and CUDA for all 2 systems x 2 seeds x 2 primes =
8/8 comparisons. A deliberate expected-rank mutation must fail on the same
binary; no control is weakened to obtain green.

## Trial and custody policy

All remote commands run under `nohup` with stdout, stderr, telemetry, process
IDs, timestamps, source hashes, binary hash, and input hashes retained.
Failures and aborts remain in `TRIALS.md`. JSON results and compact logs are
rsynced to `artifacts/math/n12-stageA/`; any file over 50 MB stays on the
remote box and is named with size and SHA-256.

## No claim

This is a finite randomized modular-sketch experiment over one preregistered
loopless signed-W column family. A four-arm `MEMBER` result is not exact
rational consistency and verifies no ReLU identity on every real row. A
`NON_MEMBER` result concerns only this finite family and is not an unrestricted
two-hidden-layer lower bound. MAX_12 remains open unless the separate exact
lift or separator leg succeeds.
