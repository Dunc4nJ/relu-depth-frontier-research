# G-0179 result — the frozen square is singular

The preregistered 5,771 by 5,771 full-rank gate failed.  This is a clean
negative result for the selected square, not the target-membership theorem
described conditionally in `PREREGISTRATION.md`.

## Decisive outcome

The exact record-major signed-i64 matrix has SHA-256
`0e7236e06adc906f2859338b12848e6fc04156963d1567de84dd1e83784162ad`,
33,304,441 entries, and 266,435,528 bytes.  Its values range from 0 to 69,120;
13,164,950 entries are nonzero.

Both frozen modular computations returned the same result:

| prime | exact modular rank | determinant mod prime | receipt SHA-256 |
|---:|---:|---:|---|
| 1,000,003 | 5,291 | 0 | `c368c31700b498847256337973d51d9804351704f44cbb74da163aea750bf5d5` |
| 1,000,033 | 5,291 | 0 | `1b20292d0e297ed7bdceccd53d637abed5836d07d78b9976c7f5c8d7d64c4e51` |

The pivot-direction lists agree exactly across the two primes.  Independent
rank runs on the physical transpose also return rank 5,291 at both primes,
with identical pivot-record lists.

There is also characteristic-zero evidence that settles the preregistered
full-rank question without relying on a bad-prime inference: exact bytewise
inspection finds only 5,681 unique columns and 5,769 unique rows.  A stronger
audit finds 98 disjoint proportional-column pairs: 90 equal pairs and eight
additional nontrivial scalar pairs.  Thus the integer square is singular over
every field and has rational rank at most 5,673.  These exact relations do not
explain the entire observed modular deficiency.

An independent FFLAS-FFPACK implementation reproduces rank 5,291 at both
frozen primes and at the fresh prime 1,000,099.

## The two intrinsic row collisions lie in the old space

Complete normal forms, independently recomputed by the frozen G-0109 and
G-0179 evaluators, certify

\[
q_{22}-q_{3140}=0
\]

and

\[
q_{2986}-q_{5656}=2p_{15947}-p_{22121}-p_{36968}.
\]

The second identity matches all 11 linear coordinates and all 434 hinge
directions appearing across its five columns.  Before the primary columns are
subtracted, \(q_{2986}-q_{5656}\) has 210 nonzero hinges, all with \(d_0=0\).
The right side consists entirely of frozen G-0113 primary columns, so the
difference lies in \(O\).

Therefore no enlargement using only \(d_0=1\) directions can make the formal
5,771-row restriction injective, but both known intrinsic kernel vectors are
validly quotientable modulo \(O\).  This changes the correct sufficient
condition from formal injectivity to

\[
\ker(R_{d_0=1}|_{\operatorname{span}(S)})\subseteq O.
\]

## What follows, and what does not

The two modular ranks prove that the rational rank is at least 5,291.  Their
agreement is strong evidence that the rational rank is 5,291, but two zero
determinants do not prove that upper bound.  The exact proportional pairs prove
only the upper bound 5,673.

Consequently:

- the selected restriction is not injective on the 5,771 retained `STAR`
  columns;
- the conditional G-0179 direct-summand and target-membership theorem is not
  established;
- the full active \(d_0=1\) restriction on all formal rows is singular because
  of the two complete relations above;
- it says nothing by itself about whether `MAX11` lies in the old span, and it
  is not a neural-network depth or width lower bound.

The stable two-prime RREFs isolate a 480-dimensional modular nullspace.  Two
explicit directions in that nullspace are now settled inside \(O\); the other
478 modular dimensions remain unclassified.  The highest-value next test is
the complete \(d_0=1\) kernel modulo \(O\), equivalently a quotient-aware rank
test after removing the two certified redundant cosets.  Any such computation
is a separately frozen experiment.

## Receipts

| object | SHA-256 |
|---|---|
| producer receipt | `cf6ba0b568c67d0a18d273695b8f09515bab7089510b9de0ed9afd6bb6fc6e23` |
| two-prime certificate bundle | `afd476742e4fa2ac6fc306ac41559a83d9a5b49ff61467e653573957fb1528bc` |
| transpose rank, prime 1,000,003 | `850f4953f266888139b97d2bac552fa35e83a0ff209fbad3286b32d999258222` |
| transpose rank, prime 1,000,033 | `0f815c8b779688d11301025f3a9f74784ee97c052995a84bb7c4359e34eb24f3` |
| deficiency diagnostic | `95eb3e24cb6b867c99e310bdbed40c2f4c6087e71d2867b4d441b677d9d7b69f` |
| diagnostic source | `ee5a0301d1fb45505469f1d6bbc470cbe43eb52467ca0497a1d64b859ed56858` |
| intrinsic-relation receipt | `c2fe511b628169929cce87fc116ab7fde09defc5746d1e40663660502d2ad6fa` |
| intrinsic-relation verifier | `329ad0a6f4714616cbaba0d18fcf8fe6e04c76d669b5aa8901f27fca29f518ec` |
| independent rank audit | `2d8663d80df6cb03862985dc658785c8e3749a862a7fee3696ceaef819b00e6a` |

The large matrix is intentionally excluded from Git; its producer receipt,
external hash pin, exact byte count, rank receipts, and downstream diagnostics
bind the local artifact.
