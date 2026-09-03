# Trial log — naive MAX10 lift test

All counts name their denominator. These trials concern one finite source-
derived dictionary; they are not exact MAX11 decisions.

- The first synthetic self-test failed before mapping 0 / 163,740 signed-W
  orbits. Its intended multiplicity mutant added an edge to only one branch,
  so the input was rejected as unbalanced instead of testing orbit
  discrimination. The control was corrected to add different nonloop edges to
  both branches; the balanced mutant is distinguished, and all self-tests pass.
- The first full mapping attempt audited 1,193,940 / 1,193,940 raw extensions
  by stored source-fiber multiplicity and mapped 163,740 / 163,740 signed-W
  orbits, but failed after writing the order and before writing its report: a
  relative output path was passed to `Path.relative_to` without normalization.
  The orphan order is retained as
  `max10-lift-g0027-order.failed-relative-path-run.json`, SHA-256
  `0ca84e6b40e9aedfac0c6d294822c11c2d314a38c24c37ad3771c04af92a1d56`.
- One retry command misspelled the directory as `n-lift-test`; Python exited 2
  before processing 0 / 163,740 signed-W orbits and wrote no output.
- The corrected full run completed. Its final order is byte-identical to the
  orphan order above, giving a deterministic replay check in addition to the
  exact certificate controls recorded in `max10-lift-map-report.json`.
- Before the subject run, the current remote CUDA executable (SHA-256
  `cdf835b269d25a37f110d72f16865e6f511d5154b5caf7808dd2eb1d82bc85c3`)
  passed known-answer controls at modulus 1,000,003 for both seeds
  2,026,090,201 and 2,026,090,202. The n=10 positive processed
  12,248 / 12,248 columns and returned rank(A) = rank([A|b]) = 2,166,
  MEMBER and unsaturated; both pivot hashes were
  `13ef82302f2e50e9f9555cd77eab1881bd3ef87f33677badd2b9fe079e39a87d`.
  The n=9 union-tree negative processed 739 / 739 columns and returned
  rank(A) 360, rank([A|b]) 361, NON_MEMBER and unsaturated; both pivot hashes
  were `3885bf4223184e19c9d6cfdc1632d24d33c47c7cbc4a859f4208257af0933cdd`.
  The JSON SHA-256 values are respectively
  `18692d5574e8a9a2056634cadb0a724e6b2ea3c0b1b192fb8da80261f354ae8c`
  and `1a3c242d39641a145aee4e41b1db1edbdd76b8541992cf6a3fbc2c25c57da208`.
- Immediately before the subject launch, `nvidia-smi` reported 81,559 MiB
  total, 42,247 MiB used, and 38,835 MiB free. NavyTiger's two n=12 processes
  were left untouched. The subject was launched with eight host threads.
- The first subject launch placed both requested sketches in one process. At
  10,240 / 163,740 ordered lift records both ranks were 10,240, but aggregate
  GPU use had risen to 67,494 MiB, leaving only 13,587 MiB before the next
  rank-capacity growth step. To protect the two pre-existing n=12 jobs, only
  this subject process was terminated and the same two sketches were
  rescheduled sequentially with unchanged family, prime, buckets, and seed
  values. No JSON decision report was written. The preserved log SHA-256 is
  `265fdbb7115f0fa4efe009ca68898656d8715863a6c6381f40ade2ea2378c45c`.
  Before the one-sketch seed-1 relaunch, 38,835 MiB was again free; after its
  fixed allocation, 29,981 MiB remained free.

No-claim: these failures and controls audit dictionary construction only. They
do not establish modular or exact-rational target membership.
