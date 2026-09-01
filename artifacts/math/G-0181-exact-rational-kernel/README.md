# G-0181 — exact rational kernel audit

Status: **candidate frozen; independent promotion audit pending**.

Exploration recovered 478 independent primitive integer row relations for the
frozen G-0180 restriction matrix and replayed them to zero.  The candidate
bytes are now frozen at SHA-256
`56b4177d3e584bbe96eb35b17ba799e5138cf071dc7fd72895a45de6d4d68232`.

The prospective gate is in [PREREGISTRATION.md](PREREGISTRATION.md).  Until a
fresh verifier passes that gate, the exact-rank statement is a strong candidate,
not a promoted campaign result.

The important claim boundary is unchanged: exact rank of this sampled
restriction matrix would settle the finite linear algebra, but not the needed
function-space statement that its 478 relations lie in the old span \(O\).
