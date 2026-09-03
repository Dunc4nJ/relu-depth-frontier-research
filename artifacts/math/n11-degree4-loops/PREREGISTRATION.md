# n=11 loop-inclusive degree-4 preregistration

Frozen after the exact n=7/n=8 certificate replays and the n=10
known-answer control, but before any full n=11 target run.

## Inputs and implementation

- n=11 universe: 137,504 signed-W records, SHA-256
  `e507784414e85667cfe18f68e55b2db22015cf112f05ea110f5ccf388dafb5c0`.
- Columns: those 137,504 zero-common-loop-padding records, where record zero
  is 4E, followed by the separate 4L carrier: denominator 137,505.
- Streamrank loop-inclusive tool commit: `5ef65a3`; colgen-loops certificate
  extension commit: `3f437f4`.
- Isolated H100 CUDA binary SHA-256:
  `80cde98e172b79a4afdc816650fa1ce7b4deb4af99a132895843465bc4aa0a94`.

## Known answers observed before the target

- Upstream n=7 degree-3 certificate: 57/57 exact DP/literal columns and exact
  rational MAX7 identity; planted diagonal-sign mutant rejected.
- Upstream n=8 degree-3 certificate: 69/69 exact DP/literal columns and exact
  rational MAX8 identity; planted diagonal-sign mutant rejected.
- Complete n=10 loop-inclusive degree-4 universe plus 4L, prime 1,000,003,
  seed 2,026,090,201: rank 7,867, augmented rank 7,867, MEMBER, over
  136,037/136,037 columns.

## Frozen n=11 decision run

- Backend: CUDA on the isolated H100 workspace; sequential sketches so only
  one sou CUDA context is resident at a time.
- Prime: 1,000,003.
- Seeds: 2,026,090,201 and 2,026,090,202, in separate create-new reports.
- Buckets `m=32,768`; batch size 1,024; GEMM block 8,192; rank panel 64;
  four generation threads.
- Resource gates: process high-water RSS at 25,165,824 KiB; accepted rank at
  10,922. The rank gate makes `3 * rank <= 32,766 < m` an enforced property,
  not an after-the-fact description. Aggregate GPU use must remain below
  60,000 MiB; only the sou process may be stopped if that external gate fails.
- Rank expectation: approximately 8,900. This is the n=10 loop-inclusive rank
  7,867 scaled by the observed n=10-to-n=11 loopless degree-4 ratio
  3,514/3,109. Thus the frozen sketch has about 3.68 times the expected rank.

Both primary sketches must agree in rank, augmented rank, verdict, and ordered
pivot-source hash. If they return NON_MEMBER, repeat both seeds with the same
configuration at prime 1,000,033. Any cross-seed or cross-prime disagreement
is a failed gate and is reported without adjusting a control.

## Claim boundary

MEMBER is modular evidence only and is not an exact rational identity.
NON_MEMBER at both registered primes is a bounded two-prime null for this
finite loop-inclusive degree-4 family, not an unrestricted depth lower bound.
