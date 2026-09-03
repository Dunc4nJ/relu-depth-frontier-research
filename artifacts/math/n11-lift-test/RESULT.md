# KSI — naive certificate-lift test

## Outcome

The finite MAX10-derived n=11 dictionary contains the sketched MAX11 target
at modulus 1,000,003 in both preregistered sketches.  Each arm processed
163,741 / 163,741 columns (163,740 / 163,740 lift orbits plus 5L), was
unsaturated at rank(A) = rank([A|b]) = 30,200 in 64,000 buckets, and returned
`MEMBER`.  Both pivot lists have the same packed-little-endian-u64 SHA-256:
`c5a54c0ceb5bb71c5693ae343d96c8d16d08c3128e6ff4c605d45148b9b1c646`.

This is evidence for the naive induction structure in this finite modular
model.  It is not itself an exact rational identity.

## Exact lift definition and census

Start from all 402 / 402 terms of the pinned degree-four MAX10 certificate
`subjects/max-relu-known/certificates/certificate_10_4.json`, SHA-256
`10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4`.
Embed its labels 1 through 10 as the fixed subset of `[11]`; quotienting by
`S_11` covers every injection into `[11]`.  Append an ordered pair of distinct
nonloop edges `(e_L,e_R)`, one edge to each branch.  For each source term this
has 1,980 / 2,970 disjoint-edge choices and 990 / 2,970 shared-distinct-edge
choices.  Cancel common branch occurrences, then quotient the signed `W` by
`S_11` relabeling and global branch/sign reversal.

The construction audited 1,193,940 / 1,193,940 raw extensions and reduced them
to 163,740 / 163,740 signed-W orbits, with the zero orbit occurring once.
All 163,740 / 163,740 orbits mapped to G-0027 record indices; 0 / 1,193,940
raw extensions and 0 / 163,740 quotient orbits were outside the complete
loopless G-0027 universe.  The order has record 0 first and then nonzero
records in frozen G-0113 orbit-index order.

Bindings:

- G-0027 universe: 754,017 / 754,017 records, SHA-256
  `8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8`.
- G-0113 representatives: SHA-256
  `57888d8e24ffa0d53490592a0b3e94c2f74ebb4fa91cc10fdac94ce4245f9b48`.
- G-0027 order: 163,740 / 163,740 indices, SHA-256
  `0ca84e6b40e9aedfac0c6d294822c11c2d314a38c24c37ad3771c04af92a1d56`.
- Mapping report: SHA-256
  `07fb44d1f36a56d8bb180fbda5ac4701fe1f121ecfe04251d7dc2b2d8e085d49`.
- Mapper: SHA-256
  `b2185841680dc3b16ea1b083e2d777aee2e3af8efa213cfd793d376fc8798f97`.

## Modular arms at p = 1,000,003

Both arms used the CUDA streamrank executable with SHA-256
`cdf835b269d25a37f110d72f16865e6f511d5154b5caf7808dd2eb1d82bc85c3`,
64,000 buckets, batches of 1,024 columns, GEMM blocks of 8,192, rank panels of
64, eight host threads, and 5L coefficient 18,144,000 / 18,144,000 on each of
the 11 / 11 linear coordinates.

- Seed 2,026,090,201: 163,741 / 163,741 columns; rank(A) =
  rank([A|b]) = 30,200; `MEMBER`; unsaturated; wall time
  3,928.299468533 seconds; maximum host RSS 9,091,528 KiB.  JSON SHA-256
  `5f8741e180cc994052ae577da8614a8988fffa89cb9afa80d09980d2f46cb1db`;
  log SHA-256
  `a984df65937c13aabe1f1d126a025c0d6c18fa66fa22871298e8f06bb2aac998`.
- Seed 2,026,090,202: 163,741 / 163,741 columns; rank(A) =
  rank([A|b]) = 30,200; `MEMBER`; unsaturated; wall time
  3,766.816122857 seconds; maximum host RSS 9,081,236 KiB.  JSON SHA-256
  `79b5219ac3d6639dc4f21944d15c73cc51078a83cbd3b13c402bf21bdefc45b6`;
  log SHA-256
  `eeb35f5bdd4478ac88669ecda1db6b0623a3655b0beb68546add776f408fff42`.

A second-prime seed-1 arm at modulus 1,000,033 was started under the original
bead trigger, then cancelled on AmberBluff's explicit order because the H100
was being destroyed and the recursion route no longer required that rank
cross-check.  Only that KSI process received `SIGTERM`; the A100 exact-lift
pipeline was not touched.  At cancellation it had processed
93,184 / 163,740 ordered lift records and reached rank 29,558 in 64,000
buckets.  It wrote no JSON report and therefore has no verdict.  Its partial
log SHA-256 is
`06bc3fc66d56ced3d3fa7816aa328987e933451cb5bf4083b56554da245156e0`.

## Known-answer controls

The same CUDA executable first passed controls in both directions at modulus
1,000,003 and both seeds 2,026,090,201 and 2,026,090,202:

- Positive: saved n=10 complete loopless system, 12,248 / 12,248 columns,
  rank(A) = rank([A|b]) = 2,166 in 6,498 buckets, `MEMBER`, unsaturated.
  Both pivot-list SHAs are
  `13ef82302f2e50e9f9555cd77eab1881bd3ef87f33677badd2b9fe079e39a87d`;
  JSON SHA-256
  `18692d5574e8a9a2056634cadb0a724e6b2ea3c0b1b192fb8da80261f354ae8c`.
- Negative: saved n=9 union-tree system, 739 / 739 columns, rank(A) 360 and
  rank([A|b]) 361 in 1,080 buckets, `NON_MEMBER`, unsaturated, with a separator
  checked against 360 / 360 basis columns in each sketch.  Both pivot-list SHAs
  are
  `3885bf4223184e19c9d6cfdc1632d24d33c47c7cbc4a859f4208257af0933cdd`;
  JSON SHA-256
  `1a3c242d39641a145aee4e41b1db1edbdd76b8541992cf6a3fbc2c25c57da208`.

The bead-specific n=9 -> n=10 same-lift control used all 337 / 337 terms of
the pinned MAX9 certificate, SHA-256
`4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88`.
The identical construction with fixed `[9]` inside `[10]` audited
667,260 / 667,260 raw extensions (424,620 / 667,260 disjoint and
242,640 / 667,260 shared-distinct) and produced 114,814 / 114,814 signed-W
orbits.  It mapped 337 / 337 source terms; 0 / 667,260 raw extensions and
0 / 114,814 orbits were outside the constructed loopless family.

The rank arm processed 114,815 / 114,815 columns (114,814 / 114,814 orbits
plus 5L) at modulus 1,000,003, seed 2,026,090,201 and 64,000 buckets.  It
returned rank(A) = rank([A|b]) = 17,127, `MEMBER`, unsaturated.  The pivot-list
SHA-256 is
`ea63faabeae00cf8414b90a4f4a655cd65169fa70569913a0676ed847fc3327f`;
the JSON SHA-256 is
`a9f6adc6e4f30dee0c5c75f93125540caad3f6baf800c4c31a8cd68f8755b08c`.
The family-universe, order, and map-report SHA-256 values are respectively
`c22d925e66ab83ae31eb873346ef3709a17753e3b0c36fc03e2d3b12d2123cb3`,
`1b099f8040665aa4895f3989b297aa7389e725241aceebde47411d09c0653498`,
and `a8525ef549ac15a103935893797afa5e483c75069fe59aa62981a654545295cc`.

## Commands

Construction and fail-closed verification:

```sh
source .venv/bin/activate
python artifacts/math/n11-lift-test/build_order.py --self-test
python artifacts/math/n11-lift-test/build_n9_to_n10_control.py --self-test --workers 6
python artifacts/math/n11-lift-test/verify_outputs.py \
  --subject artifacts/math/n11-lift-test/max10-lift-plus5L-m64000-p1000003-s1-cuda.json
```

The subject arms differed only in `--seeds` and their output/log names:

```sh
nohup tools/streamrank/target/release/max11-streamrank run-universe \
  --backend cuda \
  --input artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --order-file artifacts/math/n11-lift-test/max10-lift-g0027-order.json \
  --n 11 --branch-edges 5 --modulus 1000003 --buckets 64000 \
  --seeds 2026090201 --batch-size 1024 --gemm-block 8192 --rank-panel 64 \
  --threads 8 --include-five-l true --expected-columns 163741 \
  --output artifacts/math/n11-lift-test/max10-lift-plus5L-m64000-p1000003-s1-cuda.json \
  > artifacts/math/n11-lift-test/max10-lift-plus5L-m64000-p1000003-s1-cuda.log 2>&1 < /dev/null &
```

The later-cancelled second-prime arm used the same command with
`--modulus 1000033`, seed 2,026,090,201, and basename
`max10-lift-plus5L-m64000-p1000033-s1-cuda`.  After re-reading its `/proc`
command line to match all three of streamrank, modulus 1,000,033, and that
output basename, it was stopped with `kill -TERM 42070`.

The n=9 -> n=10 control rank command was:

```sh
nohup tools/streamrank/target/release/max11-streamrank run-universe \
  --backend cuda \
  --input artifacts/math/n11-lift-test/n9-lift-n10-family-universe.json.gz \
  --order-file artifacts/math/n11-lift-test/n9-lift-n10-order.json \
  --n 10 --branch-edges 5 --modulus 1000003 --buckets 64000 \
  --seeds 2026090201 --batch-size 1024 --gemm-block 8192 --rank-panel 64 \
  --threads 8 --include-five-l true --expected-columns 114815 \
  --output artifacts/math/n11-lift-test/n9-lift-n10-plus5L-m64000-p1000003-s1-cuda.json \
  > artifacts/math/n11-lift-test/n9-lift-n10-plus5L-m64000-p1000003-s1-cuda.log 2>&1 < /dev/null &
```

The exact-rational follow-on was launched on the A100 only after notifying the
owners of the concurrent PSU/HHS jobs:

```sh
MAX11_THREADS=8 nohup \
  artifacts/math/n11-stageA-exact-lift/run_remote_member_pivot.sh \
  artifacts/math/n11-lift-test/max10-lift-plus5L-m64000-p1000003-s1-cuda.json \
  > artifacts/math/n11-stageA-exact-lift/member-lift.launch.log 2>&1 < /dev/null &
```

The follow-on gathered 30,200 / 30,200 pivot columns in 30 / 30 batches and
completed the exact-sketch problem build with 243,111 hinge rows and
1,428,344,693 nonzeros.  The problem and build-report SHA-256 values were
`ff7ee9cb610db598616cd174e5d1eda542969497af35385683da10adefcb25b5`
and `6f3d94a9058e24a1119bcebfff1d094435b8d8f38e29b7ccfab6efe85bbc6523`.
It entered dense LU at internal prime 65,521, but the solver was terminated on
the 2026-09-03 03:35 UTC human pause order.  There is no solver JSON, no
`PIPELINE_DONE`, no exact witness, and no exact verdict.

## Recorded failures

- A balanced-mutant mistake in the mapper self-test was rejected before
  0 / 163,740 orbits; it was fixed without weakening the intended negative
  control.
- The first mapping run processed 1,193,940 / 1,193,940 raw extensions and
  wrote the final order but failed before its report due to a relative-path
  formatting bug.  The retained order is byte-identical to the successful
  replay.  One misspelled retry processed 0 / 163,740 orbits.
- A two-sketch subject process was stopped after 10,240 / 163,740 ordered
  records when its two resident bases left only 13,587 MiB GPU headroom for
  pre-existing jobs.  The unchanged sketches were rerun sequentially.  The
  aborted log SHA-256 is
  `265fdbb7115f0fa4efe009ca68898656d8715863a6c6381f40ade2ea2378c45c`.
- The first n=9 -> n=10 family build failed before 0 / 667,260 raw extensions
  because the H100 lacked `pynauty`.  The same code and controls then completed
  locally with six workers; the 60-byte failure log SHA-256 is
  `95d108782192535c6e725def51fd16bd73e769de7c68b95975e285e014b5e19d`.
- The A100 exact solve was cancelled by the campaign-wide human pause after
  30,200 / 30,200 exact columns had been gathered and the exact-sketch problem
  built, but before 0 / 1 solver reports and 0 / 1 exact witnesses were
  emitted.

## No claim

The modular `MEMBER` verdict is membership only in two randomized 64,000-row
sketches of this finite 163,741-column family.  It is not an exact-rational
identity, an unrestricted two-hidden-layer MAX11 representation, or a proof of
a general n -> n+1 induction theorem.  No identity is claimed here unless the
separate exact-lift pipeline reports exact rational verification on every real
and combined row.
