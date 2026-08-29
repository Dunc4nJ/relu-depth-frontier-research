# G-0059 — modular Schur/quotient oracle

G-0059 tests whether two structurally motivated proper mass-four families can
break the zero-`lambda` obstruction of the frozen G-0057 S1 baseline.  It does
not use one scalar dual price as a construction criterion.  For each prime it
selects an explicit rank-1,288 minor `B = H[R,C]` and reduces every candidate
to its full Schur signature

```text
a = B^-1 h_R
r = h - H_C a
delta = -lambda_C a.
```

For a batch, the relevant modular augmented gain is
`rank([R; delta]) - rank(R)`.

## Candidate families

The primary joint family is ordered as:

1. G-0058 sequence 92,489, the exact uniform support-eight column;
2. 328 signed-mass-four supports reconstructed independently from the frozen
   public MAX10 certificate, in original certificate-term order.

The MAX10 reconstruction multiset-cancels common branch edges, retains the
328 terms with signed mass four, quotients by coordinate relabelling and one
global branch swap through a typed incidence graph, and looks up the unique
G-0038 orbit.  All 328 classes and sequences are distinct.  Their active-count
histogram is `{8: 10, 9: 44, 10: 274}`; the term-order sequence hash is
`6b967f3604ef2774ebf2d5c6c1860ea2da5328a77a97673acb2cff9ad16d60f1`.

## Executed result

The primary result is

```text
NO_JOINT_329_QUOTIENT_GAIN_AT_EITHER_FROZEN_PRIME
```

| scope | prime | residual rank | rank with delta | gain |
|---|---:|---:|---:|---:|
| joint 329 | 1,000,003 | 323 | 323 | 0 |
| joint 329 | 1,000,033 | 323 | 323 | 0 |
| subordinate MAX10-only 328 | 1,000,003 | 322 | 322 | 0 |
| subordinate MAX10-only 328 | 1,000,033 | 322 | 322 | 0 |

Sequence 92,489 alone has a nonzero residual of support 15,027 and rank 1 at
both primes; adjoining its delta leaves rank 1.  Its scalar dual price is
therefore non-decisive, exactly as the quotient formulation requires.

Both primes independently selected the same 1,288 pivot columns and complete
rows.  The pivot determinants are nonzero at both primes.  The sparse dual
replays `w_R^T H[R,:] = lambda` on all 1,358 baseline columns.  Each prime's
70-dimensional nullspace was normalized to one distinct free coordinate per
vector and replayed as `H K = 0`; the ordered supports and distinguished free
coordinates agree across primes.  These retained kernels are inputs for a
separate exact-Q lift, not an exact-Q conclusion here.

Frozen producer artifacts:

```text
modular_quotient_oracle.py
  dd743b702a99541e835b52bbdf5ec4c50c9650344bdf2ea0d4f81d22a7678ecd
modular_quotient_oracle_v1.json.gz
  72ade3d6c9c507d6843f161419dc92b7b1273a299a7eff7c9def6a7d3e0ddb37
deterministic canonical scientific payload
  9f5d1dfde5a8ccaa4e0e02d98a588e41025c1a973211a7829f14af9ab74c5d6b
```

## Reproduce

```bash
source scripts/activate-toolchain.sh
python -m py_compile artifacts/math/G-0059/modular_quotient_oracle.py
python -B artifacts/math/G-0059/modular_quotient_oracle.py --self-test
python -B artifacts/math/G-0059/modular_quotient_oracle.py --preflight-only
python -B artifacts/math/G-0059/modular_quotient_oracle.py \
  --workers 8 --minimum-available-gib 16 \
  --output artifacts/math/G-0059/modular_quotient_oracle_replay.json.gz
```

## Claim boundary

Every rank, dual, Schur residual, delta, nullspace, and no-gain conclusion in
this artifact is finite-field evidence at the separately reported primes.
Agreement at two primes is not an exact rational theorem.  The tested family
contains only 329 proper mass-four atoms beyond the baseline, not all 132,728
proper mass-four atoms, higher signed masses, arbitrary weights, nonsymmetric
models, or unrestricted two-hidden-layer representations of MAX11.
