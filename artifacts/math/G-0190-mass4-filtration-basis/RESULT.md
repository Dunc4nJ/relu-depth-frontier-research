# G-0190 result — complete mass-at-most-four restriction kernel

Let (A_{\le 4}\) be the `851 x 6795` integer matrix obtained by retaining
exactly the STAR restriction rows of signed mass at most four. Then

\[
\operatorname{rank}_{\mathbb Q}(A_{\le4})=808,
\qquad
\dim_{\mathbb Q}\ker(A_{\le4}^{\mathsf T})=43.
\]

The 43 columns in
[`candidate/mass4_filtration_basis43.jsonl`](candidate/mass4_filtration_basis43.jsonl)
form a complete exact basis of this left kernel.

## Exact certificate

A fresh implementation reconstructed all 851 rows (signed-mass histogram
`{2:4, 3:66, 4:781}`), parsed all 43 vectors and 560 nonzero terms, and found
zero in all `43 * 6795 = 292185` scalar equations of
(C^{\mathsf T}A_{\le4}=0). A one-unit coefficient mutation produced 368
nonzero coordinates.

At each fresh prime `1000037` and `1000099`, the coefficient matrix (C) has
rank 43 and (A_{\le4}) has rank 808. Thus a nonzero modular 808-minor gives
`rank_Q(A_<=4) >= 808`, while 43 exact independent left-null vectors give
`rank_Q(A_<=4) <= 851 - 43 = 808`. This proves both the rank and completeness
claims over (mathbb Q).

The first 42 columns are literal G-0187 basis columns, in the frozen order.
The last column is exactly

\[
B_{24}+B_{174}+B_{235}-B_{295}+B_{345}.
\]

## Support minimum

Z3 4.13.3 returned `UNSAT` for support at most 33 and `SAT` for the displayed
support-34 witness in the affine coset

\[
(B_{174}-B_{295}+B_{345})+\operatorname{span}_{\mathbb Q}(\text{old 42}).
\]

A fresh implementation independently rebuilt the exact 169-row,
18-variable component formula with a different SHA-256 and again obtained
`UNSAT`. This is exact-SMT evidence with Z3 in the trust base; it is not a
proof-assistant certificate.

## Reproducibility

The original `313602840`-byte matrix is retained losslessly as
`../G-0180-star-loop-rank-expansion/results/augmented5769x6795.i64le.zst`.
Its compressed SHA-256 is
`84761d297bed5b5e8b6df399bf1b54cb4d99b03dbdb8674a23e6863989a46588`;
decompression yields SHA-256
`d57ec8abb9a843dc68327d88d0fe9c5843a055762cd3ae9f53ac45fb9eb50efd`.

From the repository root:

```sh
zstd -d artifacts/math/G-0180-star-loop-rank-expansion/results/augmented5769x6795.i64le.zst \
  -o artifacts/math/G-0180-star-loop-rank-expansion/results/augmented5769x6795.i64le
audit_dir=$(mktemp -d)
.venv/bin/python -B artifacts/math/G-0190-mass4-filtration-basis/audit/audit_g0190_cleanroom.py \
  --repo "$PWD" \
  --output-dir "$audit_dir" \
  --rank-source artifacts/math/G-0190-mass4-filtration-basis/audit/rank_mod_flint.cpp
```

The registered clean-room receipt is
[`audit/g0195_cleanroom_receipt_v1.json`](audit/g0195_cleanroom_receipt_v1.json).

## Boundary

This is a finite exact restriction-matrix theorem. It does not yet classify
the 40 genuinely mass-four directions as functions in the old-primary span
(O), settle MAX11, prove completeness of the network ansatz, or imply an
unrestricted two-hidden-layer ReLU lower bound.
