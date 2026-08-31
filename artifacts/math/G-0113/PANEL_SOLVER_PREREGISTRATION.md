# G-0113e preregistration — 301-row target-aware solver seed

Registered after the target-blind quotient and common-nonloop transfer audits,
and before evaluating any G-0113 column on the G-0108 support panel.

## Frozen inputs and semantics

- 163,740-record signed-W representative/fiber map SHA-256:
  `57888d8e24ffa0d53490592a0b3e94c2f74ebb4fa91cc10fdac94ce4245f9b48`;
- common-nonloop transfer verification SHA-256:
  `a829faa3543f2f4e8d9efab5c619674dc3f5c6d43f98a6adf46e6b1849c20b34`;
- G-0111 reconstruction of the 301 G-0108 rows SHA-256:
  `0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c`;
- G-0108 exact restricted matrix SHA-256:
  `d73747a4fb0c8061605ffbc557442f787f45af8966c25fded72b8437711f50c5`;
- G-0109 formal-stabilizer reference source SHA-256:
  `44821eb32bfd49b8a7480e6f6d3370808739e309148d1a59e56927c0547e6df2`;
- G-0111 direct-profile reference source SHA-256:
  `ea88f3ff0aa1051f0d2a54d035a092de4e8283dc459a4329b84817f78da7d29b`.

Each selected row is a four-formal-colour row.  Its column entry is the sum
over distinct formal-colour assignments, not the full `11!` permutation sum.
For a loopless degree-five record with signed graph `W=B'-A'`, evaluate

```text
5 E_r + sum_assignments max(0, S_W),
```

where `E_r` is the assignment sum of one fixed nonloop pairwise maximum.
The common-nonloop transfer audit proves this is the complete symmetrized atom
entry in the G-0108 row normalization.  Reconstruct the target as
`(11!/formal_stabilizer)*max(levels)` and require exact equality with the last
column of the frozen G-0108 matrix on all 301 rows.

The primary evaluator is an exact active-colour enumeration implemented in
Rust.  It groups colourings by formal profile and signed level-difference word,
then evaluates all 301 rows over the integers.  A Python consumer must replay
deterministic low-cost record/row entries by literal formal assignments using
the frozen G-0109 assignment semantics.

## Scan and rank policy

Scan every semantic representative in this fixed order:

1. every record with DISJOINT membership, in v1 orbit-index order;
2. every remaining SHARED_DISTINCT-only record, in v1 orbit-index order.

Thus a record in both slices occurs once, in the first stage.  The expected
stage counts are 133,449 and 30,291, totaling 163,740.  Retain exact 301-entry
integer vectors only for columns that grow a modular echelon basis and for the
small frozen literal-control sample.  Hash every evaluated exact vector in
scan order.

Use exactly the two preregistered G-0108 fresh primes

```text
p1 = 2,000,081
p2 = 3,000,017.
```

Maintain independent incremental column bases at both primes and record ranks
after DISJOINT and after the union.  Reduce the target last.  Preserve the
rank-growing descriptors at each prime; choose the p1 basis as the canonical
candidate support.  No column may be filtered by coefficient, target residual,
dual price, source coefficient, or topology.

## Frozen decisions

- Any binding, target normalization, literal control, scan census, or vector
  hash replay failure makes the run INVALID.
- If the p1 and p2 ranks or target-membership decisions disagree, report
  `MODULAR_DISAGREEMENT` with both bases; make no characteristic-zero claim.
- If the union rank is 301 at either prime, its 301 selected exact columns have
  a nonzero integer minor and hence rank 301 over Q.  Exact rationally solve
  the target on the canonical 301-column p1 support and replay all 301 rows.
  A passing solve is the immediate finite-panel CEGIS seed.
- If the agreed rank is below 301, exact-Q postprocessing must operate on the
  union of both retained bases.  A separator is reportable only after an exact
  integer vector annihilates all 163,740 streamed exact columns and pairs
  nontrivially with the target.

This is a finite 301-row discovery gate.  Panel membership is not a global
CPWL identity.  Any rational seed must advance immediately to complete
ordered-cone normal-form replay with residual-row CEGIS; a failed global replay
is evidence only against that seed/support, not against unrestricted networks.
