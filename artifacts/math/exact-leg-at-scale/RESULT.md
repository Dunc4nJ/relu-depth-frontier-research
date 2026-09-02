# RESULT — exact leg at n=11-scale ranks

Bead: `relu-depth-frontier-research-max11-root-gmp.8`  
Agent: `AzureAspen`  
Date: 2026-09-02

## Bounded outcome

The exact-lift and exact-separator consumers are implemented and exercise the
shared `max11-streamrank-pivots-v1` / exact arbitrary-index `MCOLGEN1`
contract. The n=10 MEMBER known-answer path passes from a random row sketch of
6,498 buckets (= 3 x rank 2,166) through exact lifting, all 16,719 saved real
rows, and the pinned upstream verifier. The n=9 beta-zero tree NON_MEMBER
known-answer path produces exact rational separators at primes 1,000,003 and
1,000,033 and checks every 739/739 tree column. Deliberate witness and separator
mutations both fail.

The r=20,000 timing is an explicitly synthetic sparse block-diagonal fallback,
not a dense MAX11 pivot minor. It fits within 40 GiB. The present dense Python/
FLINT path, projected from its measured r=2,166 control, does not fit within
40 GiB at r=35,000 or r=60,000.

## Shared-format boundary

WildWillow owns `tools/colgen` and `tools/streamrank`. We agreed in the `.3` and
`.8` Agent Mail threads on one pivot schema, `max11-streamrank-pivots-v1`, and
one arbitrary-index exact-column encoding, `MCOLGEN1` with modulus 0. This bead
adds consumers only: it does not duplicate either the column generator or the
stream rank engine. `support_lift.py` honors explicit source indices, accepts
batches of at most 1,024 exact columns, rejects modular batches, and records
batch SHA-256 values.

## Inputs and custody

- n=10 saved system: SHA-256
  `bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18`;
  12,248/12,248 source columns and 16,719/16,719 real rows (16,709 hinge plus
  10 linear).
- n=9 saved system: SHA-256
  `729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991`;
  the named beta-zero tree filter contains 739/739 source columns and its
  support union contains 3,029 hinge rows.
- n=9 pivot reports: prime 1,000,003 SHA-256
  `f611558ade3ef2fabe5f5e637104cbc90b306f838169271fe2f526ca0941b7f5`;
  prime 1,000,033 SHA-256
  `385752aba49621e36d40fe01c1b037e10a9e07a42f9257f6c424af782c26c879`.
- n=10 pivot report: prime 1,000,003 SHA-256
  `fdba23baaa66ac08c84a96a2a7026b8ad5be30f8654e842d395940b1ad5a99de`.
  The streamrank binary used for that run was observed at SHA-256
  `a2f2e19e8c45843b921983c017ad9bf843f364b4498a2b2eec92422796375420`;
  WildWillow subsequently rebuilt that shared binary, so the current worktree
  binary hash is not substituted for the run-time hash.
- Pinned upstream verifier: SHA-256
  `d6da3030b719735b10a197dc79d7e311ecc90f70314ed748de81087f94f039a7`.

## Exact commands

All Python commands ran after `source .venv/bin/activate`; all threaded commands
used at most 6 threads.

```bash
tools/streamrank/target/release/max11-streamrank run-saved \
  --input handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --n 10 --branch-edges 4 --filter all --modulus 1000003 \
  --buckets 6498 --seeds 2026090201,2026090202 \
  --batch-size 256 --gemm-block 512 --threads 6 \
  --expected-columns 12248 --expected-rank 2166 \
  --expected-aug-rank 2166 --expected-verdict MEMBER \
  --output artifacts/math/exact-leg-at-scale/n10-sketch-m6498-p1000003.json

python tools/exactlift/support_lift.py \
  --pivot-report artifacts/math/exact-leg-at-scale/n10-sketch-m6498-p1000003.json \
  --sketch-index 0 \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --output artifacts/math/exact-leg-at-scale/n10_sketch_exact_witness.json \
  --report artifacts/math/exact-leg-at-scale/n10_sketch_exact_lift_report.json \
  --upstream-output artifacts/math/exact-leg-at-scale/n10_sketch_exact_upstream.json

python tools/exactlift/exactlift.py mutate-witness \
  --witness artifacts/math/exact-leg-at-scale/n10_sketch_exact_witness.json \
  --delta 1 \
  --output artifacts/math/exact-leg-at-scale/n10_sketch_exact_witness_mutated_plus1.json
python tools/exactlift/exactlift.py verify \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --witness artifacts/math/exact-leg-at-scale/n10_sketch_exact_witness_mutated_plus1.json \
  --report artifacts/math/exact-leg-at-scale/n10_sketch_exact_witness_mutated_verify.json

python tools/exactlift/exactlift.py bind-upstream-verification \
  --candidate artifacts/math/exact-leg-at-scale/n10_sketch_exact_upstream.json \
  --verified-certificate artifacts/math/exact-witness-n9-n10/recovered_n10_upstream.json \
  --verification-report artifacts/math/exact-witness-n9-n10/recovered_n10_upstream_parallel_verify.json \
  --verifier literature/repos/max-relu-certificates/verify_certificate.py \
  --output artifacts/math/exact-leg-at-scale/n10_upstream_verification_binding.json

python tools/exactlift/sketch_separator.py lift \
  --pivot-report artifacts/math/stream-rank-engine/n9-trees-p1000003-barrett-v2.json \
  --sketch-index 0 \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --output artifacts/math/exact-leg-at-scale/n9_tree_exact_separator.json \
  --report artifacts/math/exact-leg-at-scale/n9_tree_exact_separator_report.json
python tools/exactlift/sketch_separator.py lift \
  --pivot-report artifacts/math/stream-rank-engine/n9-trees-p1000033-barrett-v2.json \
  --sketch-index 1 \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --output artifacts/math/exact-leg-at-scale/n9_tree_exact_separator_p1000033_seed2.json \
  --report artifacts/math/exact-leg-at-scale/n9_tree_exact_separator_p1000033_seed2_report.json

python tools/exactlift/sketch_separator.py mutate \
  --separator artifacts/math/exact-leg-at-scale/n9_tree_exact_separator.json \
  --delta 1 \
  --output artifacts/math/exact-leg-at-scale/n9_tree_exact_separator_mutated_plus1.json
python tools/exactlift/sketch_separator.py verify \
  --system handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --separator artifacts/math/exact-leg-at-scale/n9_tree_exact_separator_mutated_plus1.json \
  --output artifacts/math/exact-leg-at-scale/n9_tree_exact_separator_mutated_verify.json

python tools/exactlift/scale_benchmark.py \
  --rank 20000 --block-size 64 \
  --output artifacts/math/exact-leg-at-scale/synthetic_exact_r20000.json

python -m unittest discover -s tools/exactlift -p 'test_*.py' -v
python -m py_compile tools/exactlift/*.py
git diff --check
./skill-runtime verify-quick
```

The unit suite, byte compilation, and whitespace check passed. Campaign quick
verification exited 1 only for the documented pre-existing SE-10 finding on
G-0015; this bead did not edit the ledger or any canonical claim/status file.

## n=10 MEMBER control: sketch to exact witness

The 6,498/6,498-bucket CountSketches at seeds 2,026,090,201 and 2,026,090,202
both returned rank(A)=2,166 and rank([A|b])=2,166 over prime 1,000,003, from
12,248/12,248 source columns. Both independently returned the same ordered
2,166/2,166 pivot-source list; its compact-JSON SHA-256 is
`b7e51a642bc3ea8610d6a14d5bf942777ef976587542807c44a65c1f19be3a6a`.
The stream run took 87.636991 seconds and peaked at 332,152 KiB.

On the 2,166/2,166 exact pivot columns, the lifter found 2,166 independent
real rows among 16,719 union rows, solved the exact minor, and reduced to a
424/2,166 nonzero witness with coefficient-denominator LCM 304,819,200. It
then checked 16,709/16,709 hinge rows and 10/10 linear rows exactly over Q:
PASS with zero residuals. The lift took 136.40899191610515 seconds total,
including 11.78330223634839 seconds for Dixon, and peaked at 1,702,536 KiB.
The lift report SHA-256 is
`86c14aaebbc3f0d95275aa3bd8f4b8bfddc6ef13a614975a93050667877a272c`.

The upstream-form certificate SHA-256 is
`4bcb155a416188d479f20a2009f077003e828f1f09d65476117523a3bb6644e9`,
byte-for-byte equal to the recovered n=10 certificate from bead `.2`. That
certificate was checked by 6/6 workers through the unchanged pinned upstream
`read_pair`/`symmetrized_pair` code: 424/424 terms, zero hinge residuals, zero
linear residuals, PASS. The completed verification report SHA-256 is
`31de498d2435f1676b1855b94c2ae26059026fe1e3950678a7396d656a86ef70`.
The binding report checks candidate byte identity plus both recorded hashes and
is PASS; its SHA-256 is
`5f4c34de6168ae7425539e8f5cc5a9fbb84f5b5bf8b9b5537ade61f54e24aeda`.

Why the support-union check is complete: coefficients outside the pivot set S
are exactly zero. A hinge row absent from the union of the exact columns in S
therefore has zero contribution from every possible nonzero witness term, and
the MAX target has zero coefficient on every hinge row. All 10/10 linear rows
are separately included. Thus every possibly nonzero row is checked; the full
saved-system replay is an additional known-answer control.

## n=9 NON_MEMBER control: exact composed separators

For the first sketch, rank(A)=360 and rank([A|b])=361 over prime 1,000,003.
The exact lift used 361/2,048 nonzero bucket weights and composed them to
722/3,029 nonzero real hinge weights. It annihilated 739/739 exact tree columns
and paired with the target as 1/1: PASS. Total time was
27.713999090716243 seconds, exact separator solve time was
0.1782456338405609 seconds, and peak RSS was 192,284 KiB. Separator SHA-256:
`92fb25b388743d38e54c5d2b1c9c96d3184e7debe61ea93b46ebc1c1ea6cc9f5`.

The independent second sketch used seed 2,026,090,202 and prime 1,000,033.
Again rank(A)=360 and rank([A|b])=361. It used 361/2,048 nonzero bucket weights,
666/3,029 nonzero real hinge weights, annihilated 739/739 exact columns, and
paired with the target as 1/1: PASS. Total time was 29.027677513659 seconds,
exact solve time was 0.162199966609478 seconds, and peak RSS was 192,264 KiB.
Separator SHA-256:
`73b54d26a10dfb977adc11f829ea970cf2f808f02b450bfad4979815a66e73c2`.

Exactness of composition: if `S` is the named signed one-bucket sketch and `y`
is the rational bucket functional, the emitted real-row functional is
`z = S^T y`. Hence for every exact source column `c`, `z^T c = y^T S c`.
The implementation does not infer this equality from modular ranks: it builds
`z` with rational arithmetic and directly checks all 739/739 exact columns and
the target pairing.

## Negative controls

- Adding exactly 1/1 to the first n=10 witness coefficient produced FAIL on
  the complete 16,719/16,719-row replay: 0/16,709 hinge failures but 9/10
  nonzero linear residuals. Mutation report SHA-256:
  `b7547f93a1a28fbda663d64e94a7c4db2ba6b9795e3334695e8415c8fa125c55`.
- Adding exactly 1/1 to real linear separator coordinate 5 produced FAIL:
  only 0/739 tree columns remained annihilated and 739/739 pairings were
  nonzero; the target pairing remained 1/1. Mutation report SHA-256:
  `b6899cd298ab1ba3695ef13117998026e636014dfc972ae9004a0d629e9bedbc`.
- Seven unit tests pass, including tiny MEMBER and NON_MEMBER instances, exact
  witness and separator mutations, arbitrary-index exact `MCOLGEN1` acceptance,
  modular-batch refusal, and upstream-binding success plus byte-mismatch FAIL.

## r=20,000 exact timing and projections

The measured scale control is a deterministic full-rank integer system with
20,000/20,000 rows and columns, split into 313 sequential blocks of at most
64/64 rows. It has 59,374 nonzeros among 400,000,000 matrix positions. A
denominator-30 planted rational solution was recovered and checked on
20,000/20,000 exact rows: PASS. A `1/30` mutation at coordinate 0 failed on
2/64 rows of its block. Dixon solve time was 0.29352503828704357 seconds;
total time was 3.7478434965014458 seconds; peak RSS was 121,380 KiB =
0.11575698852539062 GiB, or 0.28939247131347656% of the 40 GiB limit.
Artifact SHA-256:
`cd4f95ce9e33a2c0b75b92d81a0ead7bb92d641a804d7f9a578fcbcb3e754719`.

At fixed block size and sequential processing, the measured linear-time model
projects 6.55872611887753 seconds at r=35,000 and 11.243530489504337 seconds at
r=60,000, with the same 121,380 KiB peak; this sparse fallback fits 40 GiB.
This model says nothing about a dense pivot minor.

For the current dense path, the isolated real n=10 r=2,166 exact run measured
11.94080894626677 seconds and 363,856 KiB. Naive cubic-time/quadratic-memory
scaling projects:

| rank denominator | projected solve time | projected peak RSS | fits 40 GiB? |
|---:|---:|---:|:---:|
| 35,000 | 50,380.50609172469 s = 13.994585025479081 h | 90.60430047859023 GiB | no |
| 60,000 | 253,811.99570408234 s = 70.50333214002288 h | 266.26569936565284 GiB | no |

These are extrapolations from one r=2,166 denominator, not measurements at
r=35,000 or r=60,000. Therefore a dense n=11 lift still needs a lower-memory
exact algorithm or a decomposable/sparse real-row minor.

## No claim

No n=11 system was decided or exactly lifted here. The n=10 MEMBER result is a
known-answer control. The n=9 tree NON_MEMBER separators concern only the named
finite 739-column family; they are bounded nulls, not an unrestricted two-hidden-
layer lower bound. The r=20,000 benchmark is synthetic sparse block structure,
not evidence that an n=11 pivot minor has that structure. Nothing in this bead
establishes membership or nonmembership of MAX11.
