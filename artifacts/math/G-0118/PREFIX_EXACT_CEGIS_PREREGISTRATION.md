# G-0118 preregistration — exact early-prefix CEGIS shortcut

Registered after the G-0117 cache had written beyond sequence 40,000, but
before solving any 313-row system on this prefix.

## Fixed question

Let `S` be the union of:

- sequences `0,...,39999` in the canonical 163,740-column G-0113 order; and
- the 115 sequences selected by both frozen G-0113 modular panel scans.

The second set is retained even when a sequence lies beyond the prefix so that
the exact 301-row panel member is present at the start.  Those out-of-prefix
panel vectors must come from the frozen retained-column artifact.  Every
overlapping retained vector must agree byte-for-byte with the cache.

The frozen first 40,000 cache columns occupy exactly 192,640,000 bytes and have
SHA-256

```text
d88dc897dbbfd77b98dd4edf2cecfd9696c5760e7c0dd3f2184b626659af7cde
```

The target and row order are the same 313 exact rows preregistered for G-0117
iteration 1: 301 panel rows, eleven ordered-cone linear rows with target
`(0,...,0,11!)`, then the hinge direction
`(0,0,0,0,0,0,0,0,1,-5,4)` with target zero.

## Algorithm and stopping rule

Start from the 115 common panel-basis sequences.  Over `Q`, either solve the
current selected columns exactly or extract the first primitive left-null
vector that separates the target.  Scan every sequence of `S` in increasing
order and add the first column on which that separator is nonzero.  Repeat.
Each added column must strictly increase exact rank.  Stop with exactly one of:

1. an exact rational member replayed on all 313 rows, with a freshly computed
   denominator LCM and a coefficient-plus-one mutant rejected; or
2. a primitive integer separator annihilating every column of `S` and pairing
   nontrivially with the target.

At most 20 iterations are allowed; the quotient over the 301-row panel span
has only twelve appended coordinates, so exceeding this bound is an
implementation failure, not a third outcome.

## Controls and claim boundary

The runner must refuse prefix-hash drift, row/target drift, mismatched retained
vectors, duplicate selected sequences, a non-rank-increasing added column, and
an existing output.  A toy member/nonmember pair and coefficient mutation are
required in self-test.

A positive is an exact member of a genuine subset of the global atom family
and may proceed immediately to complete global replay.  A negative is only
nonmembership in `S`; it says nothing about the remaining columns, the full
163,740-column family, or unrestricted two-hidden-layer networks.  Neither
finite-row outcome is itself a MAX11 identity.

