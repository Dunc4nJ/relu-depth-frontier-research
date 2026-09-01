# G-0180 — quotient-aware STAR loop quarantine

Status: **frozen before expansion STAR pricing or augmented rank**.

G-0179's formal 5,771-row full-rank gate cannot pass because two pairs have
identical complete \(d_0=1\) restrictions.  Both relations are now certified
inside the old space \(O\):

\[
q_{22}=q_{3140},\qquad
q_{2986}-q_{5656}=2p_{15947}-p_{22121}-p_{36968}\in O.
\]

After also removing the already known \(q_{1548},q_{4259}\in O\), 5,769 STAR
coset representatives remain.  This experiment asks the right target-specific
question: are those quotient rows independent under a frozen finite set of
active \(d_0=1\) hinges?

The first gate appends 480 domain-hash-selected directions to the original
5,771.  If needed, the second gate uses a 1,024-direction prefix which contains
all 466 available structural matches to G-0179's two-prime nonpivot records.
Neither gate used a new STAR price or any `MAX11` value in selection.

Full row rank modulo either fixed prime proves rational full row rank.  The
conservative promotion rule requires both fixed primes to pass the same gate.
Combined with the
certified quotient relations, that would prove, within the full frozen
common-apex STAR extension,

\[
f\in\operatorname{span}(O\cup S)\Longleftrightarrow f\in O
\]

for every \(f\) whose active \(d_0=1\) hinges vanish, including `MAX11`.
It would not decide whether `MAX11` lies in \(O\), establish completeness of
the ansatz, or prove an unrestricted neural-network lower bound.

The theorem, custody hashes, exact commands, and outcome rules are frozen in
[PREREGISTRATION.md](PREREGISTRATION.md).
