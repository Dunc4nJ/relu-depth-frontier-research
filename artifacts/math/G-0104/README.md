# G-0104 — joint semantic/incidence discriminator

## Outcome

The preregistered joint system is inconsistent over
`F_1,000,003` for the frozen 22,265-column
registered + all-tree + `5E`/`5L` dictionary:

```text
8,427 semantic rows:          A c = MAX11
1,387 leaf/bridge rows:       D c = MAX10 dominant-c2

rank of incidence Schur system       = 1,380
rank after adjoining its target       = 1,381
```

The exported lifted modular dual annihilates every one of the 22,265 joint
columns and pairs with the joint target by `239271 mod 1000003`.  A separate
replay reconstructed all semantic column values from the pinned sources,
reconstructed `D` from G-0099, and obtained zero residual on all 22,265
columns.  Incrementing one incidence entry produces a nonzero dual residual.

This is a **finite imposed-gauge no-go only**.  G-0103 proves that extending
`D` by zero on non-tree atoms is not representation-independent already at
`n=5`; therefore the incidence equation is not known to be semantically
necessary.  G-0104 does not imply a lower bound for MAX11, completeness of
the degree-five dictionary, rational nonmembership, or anything about
unrestricted two-hidden-layer networks.

## Controls

- All input hashes and 27 transitive G-0046 semantic inputs were stable.
- All 12,459 G-0099 trees aligned bijectively: 3,615 registered cross-family
  columns and 8,844 missing-tree columns.
- The reconstructed 171,131-nonzero `D` is zero on non-trees and `5E`/`5L`.
- The frozen 1,387-square `D` minor has determinant `217662`; its target
  replayed on all rows.
- The direct/reverse stabilizer identity passed; an `r += 1` mutation failed.
- The G-0046 modular solution replayed on all 8,427 semantic rows but failed
  1,319 of the 1,387 incidence rows.
- The lifted dual was replayed directly on all 22,265 dictionary columns;
  an incidence-entry mutation was detected.

## Reproduction

```bash
nice -n 10 .venv/bin/python -B \
  artifacts/math/G-0104/joint_semantic_incidence.py \
  --block-width 128 --minimum-available-gib 12 \
  --output artifacts/math/G-0104/joint_semantic_incidence_p1000003_v1.json.gz

nice -n 10 .venv/bin/python -B \
  artifacts/math/G-0104/verify_joint_separator.py \
  --block-width 128 \
  --output artifacts/math/G-0104/separator_replay_v1.json
```

The main run used one nice process, peaked at 6,211,264 KiB RSS, and left
29.43 GiB available.  It did not touch G-0081.

## Trial ledger

1. The first preflight invocation aborted before any solve because the new
   runner looked up the G-0033 report path under the wrong imported module.
   The path was corrected; no outcome was observed.
2. The corrected preflight passed and is frozen as `preflight_v1.json.gz`.
3. The sole outcome-producing run returned the rank pair `1380/1381` and is
   frozen as `joint_semantic_incidence_p1000003_v1.json.gz`.
4. The direct separator replay passed and is frozen as
   `separator_replay_v1.json`.

No second prime, rational lift, global candidate replay, or CEGIS round was
run: the preregistered member branch did not fire.
