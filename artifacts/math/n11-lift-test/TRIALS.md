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
- The sequential subject arms each processed 163,741 / 163,741 columns
  (163,740 / 163,740 lifted signed-W orbits plus 5L) at modulus 1,000,003.
  Seeds 2,026,090,201 and 2,026,090,202 both returned
  rank(A) = rank([A|b]) = 30,200, MEMBER and unsaturated. Their independently
  emitted pivot lists were byte-identical as packed little-endian u64 values,
  SHA-256
  `c5a54c0ceb5bb71c5693ae343d96c8d16d08c3128e6ff4c605d45148b9b1c646`.
  The JSON SHA-256 values are respectively
  `5f8741e180cc994052ae577da8614a8988fffa89cb9afa80d09980d2f46cb1db`
  and
  `79b5219ac3d6639dc4f21944d15c73cc51078a83cbd3b13c402bf21bdefc45b6`.
- The first n=9 -> n=10 same-lift family-build attempt ran on the H100, where
  the Python environment lacked `pynauty`; it failed before 0 / 667,260 raw
  extensions and wrote no family artifacts. The 60-byte stderr log is retained
  as `n9-lift-n10-build.failed-no-venv.log`.
- The corrected n=9 -> n=10 construction ran locally with six workers. From
  337 / 337 pinned MAX9 certificate terms it audited 667,260 / 667,260 raw
  ordered edge-pair extensions (424,620 disjoint and 242,640 shared-distinct),
  reduced them to 114,814 / 114,814 signed-W orbits including record zero,
  mapped 337 / 337 source terms, and found 0 / 667,260 raw extensions and
  0 / 114,814 orbits outside the constructed loopless family. Exact
  construction time was 51.43911637738347 s with maximum RSS 286,516 KiB.
  The family-universe, order, and map-report SHA-256 values are respectively
  `c22d925e66ab83ae31eb873346ef3709a17753e3b0c36fc03e2d3b12d2123cb3`,
  `1b099f8040665aa4895f3989b297aa7389e725241aceebde47411d09c0653498`,
  and
  `a8525ef549ac15a103935893797afa5e483c75069fe59aa62981a654545295cc`.
- The n=9 -> n=10 same-lift rank control processed 114,815 / 114,815 columns
  (114,814 lift orbits plus 5L) at modulus 1,000,003, sketch seed
  2,026,090,201 and 64,000 buckets. It returned
  rank(A) = rank([A|b]) = 17,127, MEMBER and unsaturated. Its pivot-list
  little-endian-u64 SHA-256 is
  `ea63faabeae00cf8414b90a4f4a655cd65169fa70569913a0676ed847fc3327f`;
  its JSON SHA-256 is
  `a9f6adc6e4f30dee0c5c75f93125540caad3f6baf800c4c31a8cd68f8755b08c`.
- After both primary-prime sketches returned `MEMBER`, a second-prime seed-1
  arm was launched at modulus 1,000,033 under the original bead trigger.  On
  AmberBluff's explicit cancellation order (the H100 was to be destroyed and
  this rank cross-check was no longer needed for the recursion route), only
  that process was sent `SIGTERM`.  It had processed 93,184 / 163,740 ordered
  lift records and reached rank 29,558 in 64,000 buckets.  It emitted no JSON
  decision report, so it supplies no verdict.  The retained partial log
  SHA-256 is
  `06bc3fc66d56ced3d3fa7816aa328987e933451cb5bf4083b56554da245156e0`.

No-claim: the subject and same-lift controls are finite modular membership
results. They do not verify an exact rational identity, an unrestricted MAX11
representation, or a general induction theorem.
