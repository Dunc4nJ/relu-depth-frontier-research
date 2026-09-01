# G-0185 result — the retained signed-mass-at-most-three kernel lies in \(O\)

Let \(A_{\leq3}\) be the 70 by 6,795 submatrix of the frozen G-0180
restriction matrix selected by the retained G-0179 STAR records of signed mass
at most three. Then

\[
\operatorname{rank}_{\mathbb Q}(A_{\leq3})=67,
\qquad
\ker_{\mathbb Q}(A_{\leq3}^{T})
=\operatorname{span}_{\mathbb Q}\{c_0,c_{15},c_{130}\},
\]

where \(c_j\) denotes exact G-0181 basis column \(j\). G-0182, G-0183, and
G-0184 certify respectively that \(c_{15},c_0,c_{130}\) are complete
characteristic-zero functions in the old-primary span \(O\). Therefore every
rational relation supported entirely on these 70 STAR records belongs to
\(O\).

## Exact certificate

The verifier derives exactly 70 retained rows: four of signed mass two and 66
of signed mass three. Their canonical 70 by 6,795 integer matrix has SHA-256
`332e238b36abc07f9c8fe817afd5b1cf6afb91e810f8ee7adc8b543920f47cb7`.

Independent modular row reductions give rank 67 at both 1,000,003 and
1,000,033, with the same 67 pivot columns. Either computation supplies a
nonzero integer 67-minor, hence rational rank at least 67. Exact replay of
G-0181 columns 0, 15, and 130 checks all 20,385 entries of their product with
the selected matrix and finds zero residual. Their coefficients at STAR
sequences 2,124, 3,944, and 5,155 form the 3 by 3 identity, so they are
independent and rational rank is at most 67. The two bounds meet.

The clean replay then reruns each of the three complete-normal-form lift
verifiers and requires byte-identical receipts. A one-unit mutation of column
0 produces 629 nonzero restriction equations.

| object | SHA-256 |
|---|---|
| frozen theorem candidate | `7d3f6c5e78934fa57c08326d2ea9a8543d07c538a47be45e5f70d5b112e3d0e2` |
| clean verifier | `0120eafcc606ab64cae1b112b545808dc2fd440e7d0a77a5487bf1a599ca67aa` |
| promoted replay receipt | `f6de93bb67f49f8db193e949df82260cbe032dba7c7276b4ef2428d995a71b5f` |
| exact three-vector residual | `81a1e01704e43b8dd51cc7f6501685eafd03f8410c70783326c048b7ca84a007` |

An adversarial fresh replay reproduced the promoted receipt byte for byte and
matched both modular RREFs independently with FLINT. This is same-family
computational review, not a human or different-family T2 referee.

## What changed

This is stronger than three isolated lifted identities: it classifies every
relation in a complete, exactly characterized three-dimensional subkernel.
It is the first closed stratum of the 478-dimensional retained STAR kernel.

## Claim boundary

Only relations supported entirely on the 70 retained low-mass rows are
classified. The four low-mass records excluded upstream by the frozen G-0180
quotient, every relation mixing a higher-mass STAR record, the other 475
global kernel dimensions, MAX11 membership, ansatz completeness, and
unrestricted two-hidden-layer ReLU lower bounds remain outside the theorem.
