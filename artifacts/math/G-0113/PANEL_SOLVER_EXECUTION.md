# G-0113e 301-row panel scan and exact-Q execution

The corrected all-record scan and the frozen exact-rational postprocessor both
completed successfully.  The resulting status is
`EXACT_Q_MEMBER_FINITE_PANEL`.

## Frozen result artifacts

```text
6f3f52bf9709cda495258f760bf51bdde33eea015e0db499cacf04c28eabb85e  panel_scan_v1.json
615e264dd64e43c8374131e6934e9728ee4c043a8b15f19ed50ec8d676fe1393  panel_retained_columns_v1.json
7bb06fc52d9ee5a69cab96bd4b80c5bf8514fa1be6c5f346091ae8fc24da35ff  panel_exact_postprocess_v1.json
```

The exact postprocessor was frozen before the modular outcome was observed:

```text
94d50a6b4defa5ce9e5502009b624d26c915ab49c4be8b4064c95b755640f44a  PANEL_EXACT_POSTPROCESS_PREREGISTRATION.md
07f20ee167483aedc0c06f40650fd3edc671ef7fc5cf1e1050b1ad388ba3ec48  exact_panel_postprocess.py
8be4583119a49d63ef41ab4c86d2f9eb1ee473c99578047c8c62bdcaa01ed47f  src/main.rs
```

## Modular scan

The scanner evaluated all 163,740 records in the preregistered order: 133,449
DISJOINT records followed by 30,291 SHARED-only records.  At the DISJOINT
boundary, both primes gave rank 113 and target membership.  At the union
boundary, both primes gave rank 115 and target membership.  Rank and membership
agreed at each boundary separately, and the two primes selected the identical
ordered list of 115 rank-support sequences.

The scan retained 120 records in total, of which 115 were in the union rank
support.  It used 12 Rayon threads and completed in 3,758.384 seconds.  The
complete vector-stream hash is
`da045a6fc004afeb6c9b67c8fc093a191ed3e9c515bc8e97901a6e64cb125c5b`;
the ordered vector-digest-stream hash is
`0d6dadb15a8e72cf37c119c2d73f0750e38f5708f09a98c48f36b4f44b59815b`.
All eight preregistered vector-hash controls matched.  The observed exact entry
range was 271,530 through 58,253,040, and no record had more than two feedback
vertices.

## Exact-rational replay

The retained union matrix has exact rank 115, while its target-augmented matrix
also has exact rank 115.  Hence the 301-row target is in the retained span over
the rationals.  The postprocessor chose 115 coordinate rows, solved for 115
rational coefficients, and replayed the resulting equality on all 301 rows
exactly.  It completed in 2.236 seconds with maximum RSS 470,120 KiB.

The actual-certificate mutation control added one to the first nonzero
coefficient and was rejected by the full 301-row replay.  The three planted
exact controls also passed: a member, its coefficient-`+1` mutant, and a
nonmember with an exact separating left-null vector.  The support sequences,
coordinate rows, coefficients, and common denominator are serialized in
`panel_exact_postprocess_v1.json` rather than repeated here.

## Claim boundary and handoff

This is exact membership on one frozen finite 301-row panel.  It is a CEGIS
seed, not a global CPWL identity, not an exact MAX11 representation, and not a
MAX11 lower bound.  Establishing or refuting global equality requires the
independent ordered-cone normal-form residual replay and counterexample search
preregistered under G-0117.  No G-0117 global-normal-form work is duplicated in
this artifact.
