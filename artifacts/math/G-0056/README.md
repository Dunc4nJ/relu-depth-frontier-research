# G-0056 — exact rational lift of the S0 kernel

G-0054 found the same rank-867, nullity-598 S0 matrix over two primes but did
not justify an exact-Q conclusion.  G-0056 attempts the missing exact lift.

The two modular nullspace bases have identical sparse supports.  Each
coefficient is combined by CRT modulo `1,000,003 * 1,000,033`, uniquely
rationally reconstructed below the standard square-root bound, and cleared to
an integer vector.  Every lifted vector must then replay exactly to zero on all
99,858 degree-four hinge rows and on the normalized eleventh finite-difference
functional.  The common 867-square nonzero modular minor supplies the exact-Q
rank lower bound; 598 independent lifted relations supply the matching upper
bound.

Run:

```bash
.venv/bin/python -m py_compile artifacts/math/G-0056/exact_s0_kernel_lift.py
.venv/bin/python -B artifacts/math/G-0056/exact_s0_kernel_lift.py --self-test
.venv/bin/python -B artifacts/math/G-0056/exact_s0_kernel_lift.py --preflight-only
.venv/bin/python -B artifacts/math/G-0056/exact_s0_kernel_lift.py \
  --workers 8 --minimum-available-gib 12 \
  --output artifacts/math/G-0056/exact_s0_kernel_lift_v1.json.gz
```

## Executed result

The frozen run returned
`EXACT_Q_S0_RANK_867_KERNEL_598_ALL_LAMBDA_ZERO`.

- All 7,764 modular coefficients reconstructed uniquely.  Their maximum
  absolute numerator is 13; denominators are only 1, 2, or 4.
- The 598 lifted relations have supports between 3 and 60 columns.  After
  clearing denominators, the maximum absolute integer coefficient is 24.
- All 598 relations replayed exactly to zero on all 99,858 complete rows,
  totaling 61,862,142 sparse nonzero terms.  All 598 normalized `lambda`
  pairings also equal exactly zero.
- Every relation has coefficient one on one distinct nonpivot column and no
  other nonpivot column.  They are therefore independent over `Q` and give
  rank at most 867.
- The common 867-by-867 integer minor has nonzero determinant modulo both
  frozen primes, so its integer determinant is nonzero and gives rank at
  least 867.  Hence the exact rational rank is 867.

The canonical exact S0 basis contains 867 ordered source columns, with manifest
hash `c608b393ff49a9f958d7017a9d5229cd16fca2817cee4d8493cfb51be94486dc`
and ordered sparse-stream hash
`4918538dad89020784645c3cfd25c12b88b2b63857a4703a8ca4f5f522516f5c`.

Frozen artifacts:

```text
exact_s0_kernel_lift.py
  484d86ccc494019c802f3f793c8f40c4deda2e7e86913191888a2188fef527c7
exact_s0_kernel_lift_v1.json.gz
  131312761477dc3ae47167caa83aabdde1d7dc6da40b71e33c40c8b5401088d4
canonical report payload
  3d91bc9d6bc869b8e31a8adf6d15c42752f7e3d90674a343d772a99793e26837
```

The report remains classified as `COMPUTED_BOUNDED_PENDING_INDEPENDENT_REPLAY`
until a separate auditor reproduces the certificate.

## Claim boundary

Even a successful exact lift concerns only the 1,465 frozen full-core
signed-mass-4 orbit columns.  It excludes neither the 132,728 proper-core
mass-four columns nor higher masses, arbitrary weights, nonsymmetric models,
or unrestricted two-hidden-layer representations of MAX11.
