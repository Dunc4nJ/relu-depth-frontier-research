# G-0127 exact-master handoff

The exact next-master payload is now sealed:

```text
path   = artifacts/math/G-0127/batch32_coordinate_prices_v1.json
schema = max11-g0127-batch32-coordinate-prices-v1
result = EXACT_FULL_FAMILY_BATCH32_COORDINATES
sha256 = c4c5d59b13820027c81bd4e0b74c67027da851f0a6f90bd941484eb9c4533946
```

The consumer must retain the existing 348 rows and append these 32 rows with
exact target zero in serialized order, unless it produces an exact dependency
certificate for a discarded row.  It must bind the full payload and verify:

- 32 rows by 163,740 records;
- selected digest
  `0cd2699dec0bc5ffd7cb81c1454aac79143ae4a37c571fcb707c85a55a5c459e`;
- complete hinge digest
  `6435f44216f7545f466a793f31eb81c625a44ad94e21675dfab382e2d97550e5`;
- linear digest
  `84cc206d635fa7f651578ab46cda56f6154d0ebd22ca2be26ceeffcf0594aa51`;
- exact candidate-dot digest
  `000ae45daea6c4debf91f47f3accd7877762b830c30945d31f1f1c97d3c7262b`;
- every row's individual signed-i64-LE digest and exact G-0126 dot bridge.

The next scientific question is exact rational membership of the 380-row
system in the frozen 163,740-column family.  A member is only another finite-
row candidate and must undergo a new preregistered complete global replay.  A
nonmember is only a bounded obstruction for this frozen dictionary.  Neither
outcome alone settles MAX11 or triggers Lean.
