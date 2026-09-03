# t2-referee controls v1

Independent, method-disjoint lattice-point falsifier for max certificates, built
for T2 review of the MAX11 campaign. This file records every control run with its
exact command, input and output hashes, verdict and wall time.

**No-claim line.** Agreement on lattice points falsifies but does not prove the
identity; this tool is a referee-side check, not a certificate verifier.

## 1. What is being checked

The identity certified by the upstream format is

```
sum_t coefficient_t * sum_{sigma in S_n} atom_t(x_sigma)  ==  max(x_1, ..., x_n)
atom_t(x) = max( sum_{(a,b) in left} max(x_a,x_b), sum_{(a,b) in right} max(x_a,x_b) )
```

with the symmetrization running over **all `n!` permutations, with no normalizing
constant and no deduplication of equal images**, and target coefficient exactly `1`.
Semantics were read off the pinned upstream verifier
`literature/repos/max-relu-certificates/verify_certificate.py`
(SHA-256 `d6da3030b719735b10a197dc79d7e311ecc90f70314ed748de81087f94f039a7`)
at lines 1-10 (atom), 28-48 (schema, `1 <= a <= b <= n`, equal branch sizes),
79-107 (symmetrization, loop over `permutations(range(n))` at line 84), 123-126
(zero-coefficient terms skipped before their pair is validated) and 136-143 (the
target subtracts exactly one copy of the top sorted coordinate, which is `max(x)`
on the sorted cone). Full citations are in `tools/t2-referee/README.md`.

The reading was confirmed rather than assumed: a throwaway brute force summed the
atom over all `5!` and `6!` permutations at random rational points and matched
`max(x)` exactly for `certificate_5_2.json` and `certificate_6_2.json`, while the
`/n!`-normalized variant was off by exactly `n!`.

The checker evaluates both sides pointwise and exactly at every point of `{0,1}^n`
and `{0,1,2}^n`. Both sides are symmetric, so only the multiset of coordinate
values matters: `n+1` value profiles for `{0,1}^n` and `C(n+2,2)` for `{0,1,2}^n`.
It shares no evaluator logic with `tools/verify11` or with the upstream verifier:
no sorted cone, no linear-form/hinge decomposition, no summation by parts, no
dynamic program over vertex placements.

## 2. Environment

| item | value |
| --- | --- |
| host | AMD EPYC, 16 cores, Linux 6.17.0-14-generic |
| interpreter | `.venv/bin/python`, CPython 3.13.7, numpy 2.5.2 |
| processes | 4 for every run (`--processes 4`) |
| repo commit before this work | `8fc94d5259ff696894ef2cb8d4d7ca4865786c8b` |

Other campaign jobs shared the host throughout, so wall times are upper bounds
rather than clean benchmarks.

## 3. Commands

Every report below was produced by exactly one command of this form, run from the
repository root:

```bash
.venv/bin/python tools/t2-referee/lattice_check.py <INPUT> \
    --profiles both --processes 4 --output artifacts/math/t2-referee/controls-v1/<REPORT>.json
```

The two mutants I built myself were produced by a rule fixed before the outcome
was known, and their generators are reproduced in `tools/t2-referee/README.md`:

- `certificate_9_4_mutated_edge_swap.json` and `certificate_6_2_mutated_edge_swap.json`:
  term 0, left branch, edge 0 `[a,b]`; replace `b` by `(b mod n) + 1` and re-sort so `a <= b`.
  Both become `[1,2] -> [1,3]`.
- `certificate_6_2_mutated_zero_one_blind.json`: for the first term admitting one,
  replace the branch pair by the lexicographically first structure whose fully
  symmetrized value agrees at every `{0,1}^6` profile but differs on `{0,1,2}^6`.
  Result: `[[1,2],[1,2]] / [[3,4],[3,4]]` becomes `[[1,2],[1,2]] / [[3,4],[3,5]]`.

Synthetic timing inputs were built with:

```bash
.venv/bin/python tools/t2-referee/make_synthetic.py --n 11 --terms 16000 \
    --branch-edges 5 --min-bits 1000 --max-bits 4000 --denominators shared \
    --seed 20260903 --output synthetic_n11_16000_shared.json
```

The pinned upstream verifier was run as
`python verify_certificate.py <INPUT>` from inside
`literature/repos/max-relu-certificates/`.

## 4. Control results

| control | input | expected | `{0,1}^n` | `{0,1,2}^n` | verdict | as expected | wall s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `upstream_certificate_5_2` | `certificate_5_2.json` | PASS | PASS | PASS | PASS | yes | 0.063 |
| `upstream_certificate_6_2` | `certificate_6_2.json` | PASS | PASS | PASS | PASS | yes | 0.148 |
| `upstream_certificate_7_3` | `certificate_7_3.json` | PASS | PASS | PASS | PASS | yes | 0.161 |
| `upstream_certificate_8_3` | `certificate_8_3.json` | PASS | PASS | PASS | PASS | yes | 0.102 |
| `upstream_certificate_9_4` | `certificate_9_4.json` | PASS | PASS | PASS | PASS | yes | 0.708 |
| `upstream_certificate_10_4` | `certificate_10_4.json` | PASS | PASS | PASS | PASS | yes | 1.909 |
| `recovered_n9_upstream` | `recovered_n9_upstream.json` | PASS | PASS | PASS | PASS | yes | 1.029 |
| `recovered_n10_upstream` | `recovered_n10_upstream.json` | PASS | PASS | PASS | PASS | yes | 2.676 |
| `mutant_certificate_5_2_plus1` | `certificate_5_2_mutated_plus1.json` | FAIL | FAIL | FAIL | FAIL | yes | 0.06 |
| `mutant_certificate_10_4_plus1` | `certificate_10_4_mutated_plus1.json` | FAIL | FAIL | FAIL | FAIL | yes | 4.04 |
| `mutant_certificate_9_4_edge_swap` | `certificate_9_4_mutated_edge_swap.json` | FAIL | FAIL | FAIL | FAIL | yes | 1.093 |
| `mutant_certificate_6_2_edge_swap` | `certificate_6_2_mutated_edge_swap.json` | FAIL | FAIL | FAIL | FAIL | yes | 0.1 |
| `mutant_certificate_6_2_zero_one_blind` | `certificate_6_2_mutated_zero_one_blind.json` | FAIL | PASS | FAIL | FAIL | yes | 0.047 |
| `timing_synthetic_n11_16000_shared` | `synthetic_n11_16000_shared.json` | FAIL | FAIL | FAIL | FAIL | yes | 102.8 |
| `timing_synthetic_n11_1000_independent_denominators` | `synth_indep_1000.json` | FAIL | FAIL | FAIL | FAIL | yes | 327.516 |
| `timing_synthetic_n11_2000_independent_denominators` | `synth_indep_2000.json` | FAIL | FAIL | FAIL | FAIL | yes | 872.294 |

Every control matched its expectation. No expectation and no code was adjusted
after seeing a result.

Notes on individual controls:

- `upstream_certificate_5_2`: upstream n=5.
- `upstream_certificate_6_2`: upstream n=6.
- `upstream_certificate_7_3`: upstream n=7.
- `upstream_certificate_8_3`: upstream n=8.
- `upstream_certificate_9_4`: upstream n=9.
- `upstream_certificate_10_4`: upstream n=10.
- `recovered_n9_upstream`: campaign recovered n=9.
- `recovered_n10_upstream`: campaign recovered n=10.
- `mutant_certificate_5_2_plus1`: coefficient +1 on term 0.
- `mutant_certificate_10_4_plus1`: coefficient +1 on term 0.
- `mutant_certificate_9_4_edge_swap`: one edge endpoint moved (mine).
- `mutant_certificate_6_2_edge_swap`: one edge endpoint moved (mine).
- `mutant_certificate_6_2_zero_one_blind`: 0/1-invisible structure swap (mine).
- `timing_synthetic_n11_16000_shared`: required perf case, one shared denominator.
- `timing_synthetic_n11_1000_independent_denominators`: adversarial denominators probe.
- `timing_synthetic_n11_2000_independent_denominators`: adversarial denominators probe.

## 5. Agreement with the pinned upstream verifier

| certificate | upstream | upstream exit | upstream wall s | lattice_check | agree |
| --- | --- | --- | --- | --- | --- |
| `certificate_5_2.json` | OK | 0 | 0.193 | PASS | yes |
| `certificate_6_2.json` | OK | 0 | 0.201 | PASS | yes |
| `certificate_7_3.json` | OK | 0 | 1.781 | PASS | yes |
| `certificate_8_3.json` | OK | 0 | 16.07 | PASS | yes |
| `certificate_5_2_mutated_plus1.json` | Fail | 1 | 0.256 | FAIL | yes |
| `certificate_6_2_mutated_edge_swap.json` | Fail | 1 | 0.2 | FAIL | yes |
| `certificate_9_4.json` | OK | 0 | 899.304 | PASS | yes |
| `certificate_9_4_mutated_edge_swap.json` | Fail | 1 | 850.768 | FAIL | yes |
| `certificate_6_2_mutated_zero_one_blind.json` | Fail | 1 | 0.247 | FAIL | yes |

The upstream verifier enumerates `n!` permutations, so it was run only where
that is affordable. It agrees with this tool on every case tried.

## 6. Timing

The performance requirement was a 16,000-term `n = 11` certificate with
1,000-4,000 bit coefficients finishing `--profiles both` in under one hour at
4 processes. Measured:

| input | terms | n | distinct denominators | common denominator bits | wall s |
| --- | --- | --- | --- | --- | --- |
| `synthetic_n11_16000_shared.json` | 16000 | 11 | 2 | 4000 | 102.8 |
| `synth_indep_1000.json` | 1000 | 11 | 1000 | 3991791 | 327.516 |
| `synth_indep_2000.json` | 2000 | 11 | 2000 | 7981842 | 872.294 |

The required case finishes in 102.8 s, roughly
35x inside the budget.

The two adversarial probes are not representative and are included only to state
the cost honestly. They use independently random denominators of up to 4,000 bits,
so the exact common denominator grows linearly in the number of terms and the
merge, not the lattice evaluation, dominates. Going from 1,000 to 2,000 such terms
costs 2.7x, an exponent near 1.4 on that segment; extrapolating to 16,000 terms
puts the run in the multi-hour range, which would miss the one-hour budget.
Nothing produced by exact linear algebra looks like this. The pinned upstream
`certificate_10_4.json` has 50 distinct denominators whose least common multiple
is 29 bits, and the campaign's own n=11 candidate
(`artifacts/math/n11-stageA-exact-lift/run7-dense-insurance/member_upstream.json`,
15,896 terms) has 1,362 distinct denominators whose least common multiple is only
713 bits. Both are far outside the adversarial regime, and the report fields
`distinct_coefficient_denominators` and `common_denominator_bits` let a referee
see at a glance which regime an input is in.

### Independent use on the campaign's n=11 candidate

Not one of my controls, and recorded here only as a cross-reference: another agent
in this campaign ran this tool on the n=11 candidate above, and its report at
`artifacts/math/t2-review/n11-run7/lattice_check_t2_report.json` records PASS on
all 90 profiles of `{0,1}^11` and `{0,1,2}^11`, 179,195 lattice points, in 175 s
at 4 processes. Per the no-claim line that proves nothing; it means the candidate
survived this check.

## 7. Synthetic inputs (not committed)

The timing inputs are tens of megabytes and are reproducible from their seed, so
they are recorded by hash rather than committed:

- `synthetic_n11_16000_shared.json` (33230552 bytes), SHA-256 `763d6748bfe937aefbda389981add7f1cbdc04a674a54cce00bf7bca20ce98b6`
  - `make_synthetic.py --n 11 --branch-edges 5 --min-bits 1000 --max-bits 4000 --seed 20260903 --terms 16000 --denominators shared`
- `synth_indep_1000.json` (2084577 bytes), SHA-256 `1910aa44bade4dd843fb6b444c6098ee23062cb1f44716c2d9cdb3cf7adce2d9`
  - `make_synthetic.py --n 11 --branch-edges 5 --min-bits 1000 --max-bits 4000 --seed 20260903 --terms 1000 --denominators independent`
- `synth_indep_2000.json` (4167347 bytes), SHA-256 `4e18363c9cb3a29db822e979c371d5ca7944d2c59ca123ab505e480b4c26636f`
  - `make_synthetic.py --n 11 --branch-edges 5 --min-bits 1000 --max-bits 4000 --seed 20260903 --terms 2000 --denominators independent`

## 8. Hashes

### Inputs

| input | SHA-256 |
| --- | --- |
| `literature/repos/max-relu-certificates/certificates/certificate_5_2.json` | `698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694` |
| `literature/repos/max-relu-certificates/certificates/certificate_6_2.json` | `026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83` |
| `literature/repos/max-relu-certificates/certificates/certificate_7_3.json` | `b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be` |
| `literature/repos/max-relu-certificates/certificates/certificate_8_3.json` | `68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3` |
| `literature/repos/max-relu-certificates/certificates/certificate_9_4.json` | `4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88` |
| `literature/repos/max-relu-certificates/certificates/certificate_10_4.json` | `10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4` |
| `artifacts/math/exact-witness-n9-n10/recovered_n9_upstream.json` | `d0302e2eecfdd85ca3a3887086b03d1aec86e9e5db7c2ed19666a4d9636c3f28` |
| `artifacts/math/exact-witness-n9-n10/recovered_n10_upstream.json` | `4bcb155a416188d479f20a2009f077003e828f1f09d65476117523a3bb6644e9` |
| `artifacts/math/exact-witness-n9-n10/certificate_5_2_mutated_plus1.json` | `e4b6f78ff0975136c2f4db9d1f88d9f94a424dd392ef8ca7a75e4f3659b498cb` |
| `artifacts/math/exact-witness-n9-n10/certificate_10_4_mutated_plus1.json` | `c27f54bb8d94b069f6f31eb9dd30b9c76150f3cc0a3bd3c3fb221a73d5068734` |
| `artifacts/math/t2-referee/controls-v1/certificate_9_4_mutated_edge_swap.json` | `94b8f6d67b03504043fecd7b84f715516eb5cb8249abf0262ceb0eb49c0a039e` |
| `artifacts/math/t2-referee/controls-v1/certificate_6_2_mutated_edge_swap.json` | `edcaace456b4d96e333f1b3a6c1e431bc4fbd93b6752ebb6703adb812b020453` |
| `artifacts/math/t2-referee/controls-v1/certificate_6_2_mutated_zero_one_blind.json` | `53683cd8db216debabeb8e79248cc9f1060cce5bcb5e3e9bfe4c9570467695e6` |
| `literature/repos/max-relu-certificates/verify_certificate.py` | `d6da3030b719735b10a197dc79d7e311ecc90f70314ed748de81087f94f039a7` |
| `tools/t2-referee/lattice_check.py` | `e8175f87cc131ce032a185afa7a387ab532608cee606dd21afec15a5ee3ae89b` |
| `tools/t2-referee/make_synthetic.py` | `4c3e771bb95878138c7d2ec48704eefa06dbbf4c51c04956fb557412648259ba` |
| `tools/t2-referee/test_lattice_check.py` | `e6b922905a08531a4aea302eac6198dd59f9e58f865b167ca6cea78a46f2ce10` |
| `tools/t2-referee/README.md` | `1233f5a2e7619d0b2f825611469a606d91c81b4922a194a71a8c687e899905d1` |

### Outputs in this directory

| file | SHA-256 |
| --- | --- |
| `certificate_6_2_mutated_edge_swap.json` | `edcaace456b4d96e333f1b3a6c1e431bc4fbd93b6752ebb6703adb812b020453` |
| `certificate_6_2_mutated_zero_one_blind.json` | `53683cd8db216debabeb8e79248cc9f1060cce5bcb5e3e9bfe4c9570467695e6` |
| `certificate_9_4_mutated_edge_swap.json` | `94b8f6d67b03504043fecd7b84f715516eb5cb8249abf0262ceb0eb49c0a039e` |
| `mutant_certificate_10_4_plus1.json` | `005a271f80df280a7c68a97698443155c7f8d2330f2f9e72760eb726c976ec47` |
| `mutant_certificate_5_2_plus1.json` | `673ea1c9f6f3dfcfe853caa5b27c2475b9a5009e10018b302d5a9dea996d8f44` |
| `mutant_certificate_6_2_edge_swap.json` | `9b5ee791196fbe050524b39761d96073a352dd82be452004d4106874d46e74c6` |
| `mutant_certificate_6_2_zero_one_blind.json` | `6763cedcd89fdec03ebf68cb717f4c31d282ba03b0be689c806ee626f4a755db` |
| `mutant_certificate_9_4_edge_swap.json` | `76bbb36553d15c7dc67dafa30c0b214588ec8cfffe29c4970774e8dd8d0aea8c` |
| `recovered_n10_upstream.json` | `90149ea87feb6ffcc75c66586d623c49bce7b803eae82b2f78d5b4d5454b1402` |
| `recovered_n9_upstream.json` | `97bf870993edb4ebfaeccd981ca6392980d359410161631e3c8d0ed2996269a5` |
| `timing_synthetic_n11_1000_independent_denominators.json` | `e516f785b17392fa2c451564f9db92d56cdd04447f69014275d1e7509e80c564` |
| `timing_synthetic_n11_16000_shared.json` | `233d911505d703329b43f6fd1a96ca8c2f5a98ad63464f21d081df198105f12f` |
| `timing_synthetic_n11_2000_independent_denominators.json` | `af4ab3c2d2a7c7250a1c3dc612ad37f8ed3e60739971054ed44ddfd9fe22aced` |
| `upstream_certificate_10_4.json` | `2e87781bdb449c8697fd9303a32902308e3c855caede1261e429d50aa09c2bc2` |
| `upstream_certificate_5_2.json` | `8786f0008b8797e16702840aeadc8c1ae9685d8707110f8f2a29e6c523dcfb0c` |
| `upstream_certificate_6_2.json` | `1783cacae2a990dfde1a484aa8d1df9a04793ce776ba1c2cf059afa3c9856ad1` |
| `upstream_certificate_7_3.json` | `60b3177a0e8de1b50c4a2e9d13062e5f68bbc7779da9822e1c31758a040d34cb` |
| `upstream_certificate_8_3.json` | `a9ecd8d06f466ca9d5f76c0c58a1d513861dab0301bdbedbf673bf88f34c7ce6` |
| `upstream_certificate_9_4.json` | `fb186dba17459f8a7a26f90d8a5519dd304cd97ecb1f45639050d862ee1cf273` |
| `upstream_verifier_crosscheck.json` | `3482269af532657221f9fe3cbe041343e60e4483ee1f5e82ae9b6da3f83a137e` |

## 9. Limitations and residual risk

- **Lattice agreement is not a proof.** Both sides are continuous piecewise-linear
  and positively homogeneous; a finite point set cannot pin such a function down. A
  FAIL is conclusive, a PASS is evidence.
- **`{0,1}^n` alone has a measured blind spot.** At `n = 6` with two edges per
  branch there are 12,630 pairs of distinct term structures that agree at every
  `{0,1}^6` profile and differ on `{0,1,2}^6`; the
  `certificate_6_2_mutated_zero_one_blind` control is built from one of them and
  passes the 0/1 cube. Always run `--profiles both`.
- **Shared-semantics risk.** This tool and `tools/verify11` are method-disjoint but
  read the same schema. If the upstream semantics had been misread in the same way
  by both, both would agree and both would be wrong. This is why the convention was
  re-derived from the upstream source and confirmed by literal `S_n` brute force,
  and why the upstream verifier itself was run wherever affordable.
- **Exact-merge cost depends on coefficient shape.** Real certificates carry few
  denominators with a small least common multiple, and the exact merge is then
  free. Thousands of pairwise-coprime multi-thousand-bit denominators push the
  common denominator into the millions of bits and the merge dominates; the
  adversarial probes above quantify that. Any exact tool pays this, since the exact
  answer genuinely has that denominator.
- **Not a proof of MAX11.** A PASS on a supplied n=11 candidate says the candidate
  survives 179,195 lattice points. It says nothing about MAX11 membership or about
  any unrestricted depth lower bound.

**No-claim line (repeated).** Agreement on lattice points falsifies but does not
prove the identity; this tool is a referee-side check, not a certificate verifier.
