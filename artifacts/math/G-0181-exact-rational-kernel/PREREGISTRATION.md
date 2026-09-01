# G-0181 freeze — exact rational kernel of the G-0180 matrix

Frozen at `2026-09-01T09:56:11Z`, after exploratory reconstruction but before
the independent verification required for promotion.

## Epistemic status

This is not an outcome-blind discovery preregistration.  Four modular kernels
had already been inspected, a 478-vector rational candidate had already been
reconstructed, and one NumPy replay had already returned exact zeros.  The
purpose of this freeze is narrower and prospective: bind the candidate bytes
before a fresh implementation attempts to refute or certify them.

The frozen candidate is
`candidate/exact_left_kernel_basis_v1.jsonl`, with 5,366,383 bytes and SHA-256

```text
56b4177d3e584bbe96eb35b17ba799e5138cf071dc7fd72895a45de6d4d68232
```

It contains one header and 478 primitive sparse integer row relations for the
frozen G-0180 matrix.  Its exploratory provenance is retained under
`exploratory/`; those receipts are evidence to audit, not the independent
promotion gate.

## Frozen inputs

| object | bytes | SHA-256 |
|---|---:|---|
| augmented integer matrix (external, ignored by Git) | 313,602,840 | `d57ec8abb9a843dc68327d88d0fe9c5843a055762cd3ae9f53ac45fb9eb50efd` |
| exact candidate basis | 5,366,383 | `56b4177d3e584bbe96eb35b17ba799e5138cf071dc7fd72895a45de6d4d68232` |
| G-0180 rank receipt, prime 1,000,003 | 26,869 | `61925993c97c40fac1ced04f374ffa05144026f2c2c8d3a579fa483d2219178a` |
| exploratory reconstructor | 12,106 | `5bfaae0da6a7545195cb01c3a335f25b73e876c2e04afeb6c98b87a5c61897bb` |
| exploratory reconstruction receipt | 6,301 | `58ffdd9d844db401f36f511115d306ba9b3c33ae133039faaa8c6417b435afe0` |
| exploratory exact replayer | 8,340 | `08f34d06abde94badb78ffeebb9f24c4ae1c0de6f7c33fd7c7600fc9308ae6d5` |
| exploratory replay receipt | 2,504 | `cec5089d318405e8a25811f2219512172fee45e4c7fde328df027613c2a66100` |

The matrix path is
`../G-0180-star-loop-rank-expansion/results/augmented5769x6795.i64le`.
The rank receipt path is
`../G-0180-star-loop-rank-expansion/results/rank_certificate_v1/rank_directed_1024_rank_mod_1000003.json`.

## Independent promotion gate

A new verifier, written after this freeze and not copied from the exploratory
replayer, must:

1. re-hash all three decisive inputs and reject any drift;
2. parse exactly 478 relations in basis-column order;
3. check every row index, record-sequence binding, support count, primitive
   gcd, stored coefficient statistic, and the 478 by 478 diagonal nonzero
   free-coordinate witness;
4. use exact arithmetic to check all 3,248,010 scalar equations in
   \(C^T A=0\), without relying on the exploratory residual receipt;
5. independently reproduce a deterministic digest of the zero residual;
6. mutate one frozen coefficient by `+1` and require the same verifier to
   detect a nonzero residual;
7. re-hash inputs at exit.

If these gates pass, the 478 columns of \(C\) are independent over
\(\mathbb Q\), hence

\[
\operatorname{rank}_{\mathbb Q}(A)\le 5769-478=5291.
\]

The frozen modular rank 5,291 gives the reverse inequality because reduction
modulo a prime cannot increase rank.  The promoted conclusion would therefore
be

\[
\operatorname{rank}_{\mathbb Q}(A)=5291,
\qquad \dim_{\mathbb Q}\ker(A^T)=478.
\]

Any failed relation, arithmetic-bound failure, candidate-format ambiguity,
or hostile-control escape is a failure of promotion, not something to repair
in place.  A revised candidate requires a new frozen experiment.

## Claim boundary

Even a passing result concerns only the finite frozen 5,769 by 6,795
restriction matrix.  It does not prove that the 478 STAR combinations vanish
as functions or lie in the old primary span \(O\); it does not decide MAX11
membership, ansatz completeness, or an unrestricted neural-network lower
bound.  The next mathematical gate remains an exact lift of these restriction
relations into \(O\).
