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
inspection finds only 5,681 unique columns and 5,769 unique rows.  Thus the
integer square is singular over every field.  The 90 duplicate-column pairs
and two duplicate-row pairs do not explain the entire observed modular
deficiency.

## What follows, and what does not

The two modular ranks prove that the rational rank is at least 5,291.  Their
agreement is strong evidence that the rational rank is 5,291, but two zero
determinants do not prove that upper bound.  The exact duplicates prove only
the weaker upper bound 5,681.

Consequently:

- the selected restriction is not injective on the 5,771 retained `STAR`
  columns;
- the conditional G-0179 direct-summand and target-membership theorem is not
  established;
- this does not show that the full active \(d_0=1\) restriction is singular;
- it says nothing by itself about whether `MAX11` lies in the old span, and it
  is not a neural-network depth or width lower bound.

The stable two-prime RREFs isolate 480 nonpivot record coordinates.  Among the
10,890 candidate directions absent from the G-0179 STAR matrix, a deterministic
structural matching covers 466 of those 480 coordinates.  The diagnostic
freezes a nested continuation before any of those STAR prices are observed:
first 480 domain-hash-selected directions, then a 1,024-column batch containing
all 466 structural matches, with the full remaining order fixed.  Any result
from that continuation belongs to a separately preregistered experiment.

## Receipts

| object | SHA-256 |
|---|---|
| producer receipt | `cf6ba0b568c67d0a18d273695b8f09515bab7089510b9de0ed9afd6bb6fc6e23` |
| two-prime certificate bundle | `afd476742e4fa2ac6fc306ac41559a83d9a5b49ff61467e653573957fb1528bc` |
| transpose rank, prime 1,000,003 | `850f4953f266888139b97d2bac552fa35e83a0ff209fbad3286b32d999258222` |
| transpose rank, prime 1,000,033 | `0f815c8b779688d11301025f3a9f74784ee97c052995a84bb7c4359e34eb24f3` |
| deficiency diagnostic | `95eb3e24cb6b867c99e310bdbed40c2f4c6087e71d2867b4d441b677d9d7b69f` |
| diagnostic source | `ee5a0301d1fb45505469f1d6bbc470cbe43eb52467ca0497a1d64b859ed56858` |

The large matrix is intentionally excluded from Git; its producer receipt,
external hash pin, exact byte count, rank receipts, and downstream diagnostics
bind the local artifact.
