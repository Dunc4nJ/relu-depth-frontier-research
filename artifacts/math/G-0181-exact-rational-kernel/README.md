# G-0181 — exact rational kernel audit

Status: **exact characteristic-zero rank certified**.

Exploration recovered 478 independent primitive integer row relations for the
frozen G-0180 restriction matrix and replayed them to zero.  The candidate
bytes are now frozen at SHA-256
`56b4177d3e584bbe96eb35b17ba799e5138cf071dc7fd72895a45de6d4d68232`.

The prospective gate in [PREREGISTRATION.md](PREREGISTRATION.md) passed under a
fresh clean-room verifier.  The frozen 5,769 by 6,795 integer matrix satisfies

\[
\operatorname{rank}_{\mathbb Q}(A)=5291,
\qquad \dim_{\mathbb Q}\ker(A^T)=478.
\]

See [RESULT.md](RESULT.md) for the rank sandwich and audit receipts.

The important claim boundary is unchanged: this settles the finite linear
algebra, but not the needed function-space statement that all 478 relations
lie in the old span \(O\).  G-0182 has now certified the first such lift.
