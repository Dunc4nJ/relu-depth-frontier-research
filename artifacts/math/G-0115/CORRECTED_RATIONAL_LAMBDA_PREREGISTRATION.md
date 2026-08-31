# G-0115 corrected rational-Lambda rerun preregistration

Timestamp: 2026-08-31T01:48+02:00. This document was written after the first
exact run exposed the `combined Lambda drift` assertion and before any solve
against the corrected target.

## Observed defect and claim boundary

The frozen kernel function `lambda_value` computes
`sum(a_i * int(b_i))`. That is exact on every integral atom and therefore on
the cached per-column semantics, but it is not a linear functional on a vector
whose coordinates are `Fraction` values. The target builder applied it to the
fractional sum of nine missing public terms and obtained `-28`; it likewise
obtained `29` for the retained partial public sum. Their apparent sum of one
was an artefact of coordinatewise truncation.

The first exact candidate therefore certifies membership for a malformed
hinge-plus-`Lambda` target only. It is retained as a negative control and must
not be reported as a MAX9 calibration. Its exact-minor checkpoint is
`semantic_repair_exact_checkpoint_v3.json`, SHA-256
`948f107038dc9b376340db575fc8db0809f01e4bd81835ea0104ccb740cb19a1`:
2,991 basis variables, 752 nonzero rational coefficients, maximum numerator
60 bits, maximum denominator 48 bits. It passed exact replay against the
malformed 20,686-coordinate target and then failed the independent combined
linear invariant, exactly as a useful end-to-end guard should.

## Frozen correction

For any integer or rational linear vector `b=(b_1,...,b_9)`, the corrected
functional is

`Lambda_Q(b) = sum_{r=1}^9 (-1)^(9-r) binom(8,r-1) b_r`,

with no coercion or rounding of `b_r`. The rerun will runtime-patch only this
functional before target construction. On integral atom vectors this is
identical to the old implementation; therefore the certified 22,338-column
hinge matrix, the linear cache, the column order, and all per-atom Lambda
coordinates remain unchanged.

Before solving, the runner must certify all of the following:

1. `Lambda_Q(linear_cache[j]) == matrix_cache[j,-1]` for all 22,338 columns.
2. Corrected retained-public Lambda plus corrected missing-public Lambda is
   exactly one.
3. Corrected retained-lift Lambda equals corrected retained-public Lambda.
4. The previously malformed target last coordinate is rejected by the
   corrected combined-linear check.

## Frozen search and decision rule

The ordered repair family, prefix schedule
`256,512,1024,2048,4096,8192,16384,22338`, initial hinge-row sample,
256-row counterexample batches, primes `1000003,1000033,1000037`, native PLUQ
projection solver, and complete-coordinate replay are unchanged.

An exact positive requires all of:

- a rational solution of a nonsingular selected minor;
- exact rational replay on every one of 20,685 hinge directions and the
  corrected Lambda coordinate;
- recomputation from the nine-coordinate linear cache with
  `Lambda_Q(retained + repair) == 1`;
- coefficient-mutation rejection and independent modular replays.

A finite-field nonmembership result, even for the full 22,338-column family,
is only a modular gate and is not a characteristic-zero obstruction. No MAX9,
MAX11, induction, or novelty claim follows without the exact positive checks
above and compilation of the remaining hinge-free linear correction.

## Bound inputs

- `semantic_repair.py`: `e400d35b6eb73a3e8821ed32c4c02742d46a15276aa2832b494dc9322d57f93d`
- `semantic_repair_solve.py`: `5023f3364db318521b73d464fba04dbfdecad5719170e3e0e1600ca57968b0a0`
- `semantic_repair_cegis.py`: `2ca5bf0ced2e5166abb6413c96a6c91d7d71674190de802166d648401342c71b`
- matrix cache file: `9342b7cd7b8e048b5ae38a3626766827e196c076be5fddaa94e0cb008ade49e5`
- matrix raw data: `c6f7ee5c0df99557a81d49e9771d79eaff261dea1c7490787bb573690a45e714`
- linear cache file: `4d98c6e6c2aa1a3317c13c541c50d25a025b6211ece448803462371a45a56100`
- native PLUQ source: `c8e6c0106930b2046a873de0bc1d4879914652ba4f2076163bcc9708ca96d2e0`
- native PLUQ binary: `8c5f71a8089f0ce9ad712de215043d3e076aae14187794072f79fc5271d907a9`
- native full replay source: `7f96e22cc2dae5c8c4a1a6665c0cc1ef35e78069210087bc81b22359ca658b16`
- native full replay binary: `0725a2cb305f89fc92f98b1ac45e59f6feafa684b26a3bd0e3765168c8ee9f31`

Any runner used for the corrected experiment must bind this preregistration by
SHA-256 and record its own source hash before the corrected target is solved.
