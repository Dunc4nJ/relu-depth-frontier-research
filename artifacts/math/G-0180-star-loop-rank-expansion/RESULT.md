# G-0180 result — 1,024 new directions add zero modular rank

Status: **completed negative rank gate; characteristic-zero kernel unresolved**.

The preregistered G-0180 experiment was anchored at Git commit `3190baa`
before the first expansion price was computed.  Independent audit verified
that `HEAD == origin/master`, all 22 declared hashes matched the executing
bytes, and the exact frozen command began only after that anchor.

## Exact outcome

After deleting STAR sequences `1548,3140,4259,5656`, the retained restriction
matrix has 5,769 rows.  G-0180 appended 1,024 frozen active primitive
directions with \(d_0=1\) to the original 5,771 columns.

| frozen gate | columns | rank mod 1,000,003 | rank mod 1,000,033 | increment over base |
|---|---:|---:|---:|---:|
| quotient base | 5,771 | 5,291 | 5,291 | — |
| hash prefix 480 | 6,251 | 5,291 | 5,291 | 0 at both primes |
| rank-directed prefix 1,024 | 6,795 | 5,291 | 5,291 | 0 at both primes |

The pivot lists are identical across the two primes and across both augmented
gates.  No appended column becomes a pivot.  Thus, over each of the two fixed
finite fields, every one of the 1,024 appended columns lies in the column span
of the original restriction matrix and the retained-row left nullity is 478.
The 1,024 prefix includes all 465 deterministic dependency matches belonging
to retained quotient rows; none adds a pivot.

## Custody

- expansion matrix: shape `5769 x 1024`, 47,259,648 bytes,
  SHA-256 `db6912d65015918c0e2e80c03261da0f286bcab18faf3846ed4b4f9ef63c85fb`
- augmented matrix: shape `5769 x 6795`, 313,602,840 bytes,
  SHA-256 `d57ec8abb9a843dc68327d88d0fe9c5843a055762cd3ae9f53ac45fb9eb50efd`
- expansion receipt SHA-256:
  `6e7d58666b9a58d1ea68141595bdd1404a519f10e7f47068166c7d7a290864d5`
- assembly receipt SHA-256:
  `3998739a30abb69f82a43900ecfa689896a7d4fa4e775e519ad9a1ed4371d91d`
- rank bundle SHA-256:
  `e6cd41e8ef4156db9874882ffb4e69e77e22691ba5612d9aef40098888a69676`

The rank wrapper re-hashed the pricer source and binary, assembler source and
all inputs, expansion and augmented matrices, ranker source and binary, both
base-rank receipts, the intrinsic relations, semantic controls and their
old-primary binding, and the structural-premise receipt before and after rank.

## What this establishes

For both registered primes, the two exact augmented matrices have rank 5,291.
This decisively falsifies the registered hypothesis that 480 hash-selected unused
directions, or the full 1,024 prefix containing every available structural
match to the dependent records, would restore quotient row rank.

It is strong evidence for persistent relations in the sampled \(d_0=1\)
restriction data rather than a poor choice within the two registered direction
gates.  Whether those relations extend over every active \(d_0=1\) hinge and
lift to full-function identities in \(O\) is precisely the unresolved question;
the registered computation does not establish that lift.

## What this does not establish

Rank modulo a prime is a lower bound on rational rank, not an upper bound.
Failure at both fixed primes therefore does **not** prove that the rational
rank is 5,291, that all 10,890 frozen unused directions are redundant, or that
the 478 modular kernel vectors are exact function identities.  It does not
decide whether `MAX11` lies in the old span \(O\), prove ansatz completeness,
or yield an unrestricted neural-network lower bound.

In particular, the conditional 5,769-row theorem in
`PREREGISTRATION.md` did not fire.

## Highest-leverage next obligation

Stop adaptive retries of the same sampled-column strategy.  The frozen 16,661
candidate set was formed from eight deterministic candidates per record and is
not the complete STAR hinge-support universe, so exhausting its remaining
directions would still not close the theorem.  Instead, extract a canonical
478-dimensional left kernel at both primes and search for common sparse/local
generators.  For a
basis of those relations, certify exact complete-normal-form identities and
prove that each residual lies in \(O\).  The already certified relations

\[
q_{22}-q_{3140}=0,
\qquad
q_{2986}-q_{5656}=2p_{15947}-p_{22121}-p_{36968}
\]

are the first two examples of precisely this mechanism.

If 478 independent characteristic-zero relations can be lifted into \(O\),
then the STAR quotient has dimension at most 5,291.  The existing modular
rank-5,291 minor would give the matching lower bound and make the selected
\(d_0=1\) restriction injective on that corrected quotient, proving the desired
target-specific quarantine within the frozen STAR extension.  Until those
exact lifts exist, that conclusion remains open.
