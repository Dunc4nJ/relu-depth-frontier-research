# run7 dense-insurance candidate: verify11 T1 result

Date: 2026-09-03 (Europe/Berlin)  
Bead: `relu-depth-frontier-research-max11-root-gmp.14`  
Coordination thread: `relu-depth-frontier-research-max11-root-gmp.4`  
Verifier source remained frozen throughout receipt, full verification, literal spot check, and planted negative.

## Frozen verifier and input

- Candidate: `artifacts/math/n11-stageA-exact-lift/run7-dense-insurance/member_upstream.json`
- Candidate bytes: 13,892,835 bytes/file.
- Candidate SHA-256: `8bd2270a801f6af679ccbf00aa7357f4e89ebb069d1211671082f3f5f07d25c5`.
- Release binary SHA-256: `bab4ab22fa0acaa2c49c5c91bc6fa5fb006afd7ed843f6a008049bc65d4d1eb9`.
- `tools/verify11/src/lib.rs` SHA-256: `5bc9a14f1df11fd027ff9f0e4bf3ac005e7f0d16364bd1f2c83cd1663a1667c5`.
- `tools/verify11/src/main.rs` SHA-256: `5d0299374c39288c21393f964a40ef42f26b408dd784cf270eec5b7ae627c203`.
- Arithmetic: exact integer accumulation after exact rational denominator clearing; no modular primes (`0/0` primes).

## Full DP verification: positive control

Exact command:

```text
/usr/bin/time -v tools/verify11/target/release/max11-verify11 analyze --certificate artifacts/math/n11-stageA-exact-lift/run7-dense-insurance/member_upstream.json --threads 4 --output artifacts/math/verify11/n11-run7/full_dp_report.json
```

Verdict: `VERIFY11_OK`.

- Terms checked: 15,896/15,896 supplied terms; nonzero terms 15,896/15,896; DP columns 15,896/15,896.
- Linear rows exact: 11/11; bad linear rows 0/11.
- Hinge rows exact: 169,166/169,166; bad hinge rows 0/169,166.
- Emitted hinge entries accumulated: 681,123,474/681,123,474.
- Coefficient common denominator (one denominator for the exact cleared system): `31040975848430974402390020701903357221464788368928297084263726551477370244737050508531573901482703297988991672610503602927913049577479499773520196901216019559755648991358920327741375713713756125753330981090099200000`.
- Coefficient numerator decimal digits: minimum 1 digit/coefficient, maximum 223 digits/coefficient.
- Coefficient denominator decimal digits: minimum 8 digits/coefficient, maximum 215 digits/coefficient.
- Internal compute wall: 2,765.283736191 seconds/15,896 terms at 4 threads.
- External elapsed wall: 2,765.44 seconds/15,896 terms (`46:05.44`) at 4 threads.
- Peak RSS: 448,552 KiB/process at 4 threads.
- Full report SHA-256: `5a2091d21725309e986407bf48f20cfa39b1e2468c4048b932bfc94f7ddd2b92`.

## Literal-permutation versus DP spot check

The sample was selected deterministically without replacement with seed `20260903`:

```text
tools/verify11/target/release/max11-verify11 sample --certificate artifacts/math/n11-stageA-exact-lift/run7-dense-insurance/member_upstream.json --terms 20 --seed 20260903 --output artifacts/math/verify11/n11-run7/sample20_seed20260903.json
/usr/bin/time -v tools/verify11/target/release/max11-verify11 analyze --certificate artifacts/math/verify11/n11-run7/sample20_seed20260903.json --threads 4 --literal-check --output artifacts/math/verify11/n11-run7/sample20_literal_dp_report.json
```

- Literal/DP matches: 20/20 sampled terms.
- Literal permutations: 39,916,800 permutations/term; 798,336,000/798,336,000 total sampled permutations.
- Sample terms checked by DP: 20/20.
- Sample common denominator: `31040975848430974402390020701903357221464788368928297084263726551477370244737050508531573901482703297988991672610503602927913049577479499773520196901216019559755648991358920327741375713713756125753330981090099200000`.
- Internal compute wall: 108.795176207 seconds/20 terms at 4 threads.
- External elapsed wall: 109.17 seconds/20 terms (`1:49.17`) at 4 threads.
- Peak RSS: 361,888 KiB/process at 4 threads.
- The subset's whole-identity verdict is `FAIL`, as expected for only 20/15,896 terms; this was not weakened or treated as a failed spot check.
- Sample JSON SHA-256: `acce932388eb376bf32942e4cc0e73eee4fbb95b562c8f2752f2c9937bab86ac`.
- Literal/DP report SHA-256: `7cb783798d741d8284e4861d4ae7f396001b00c3f52179233b2d0b0f436db1d9`.

## Planted `+1` coefficient negative control

The mutation was made in an uncommitted temporary copy; the candidate was not modified.

```text
tools/verify11/target/release/max11-verify11 mutate-coefficient --certificate artifacts/math/n11-stageA-exact-lift/run7-dense-insurance/member_upstream.json --output /tmp/verify11-run7-mutant.fBs00O/member_upstream_coefficient_plus_one.json
/usr/bin/time -v tools/verify11/target/release/max11-verify11 verify --certificate /tmp/verify11-run7-mutant.fBs00O/member_upstream_coefficient_plus_one.json --threads 4 --output artifacts/math/verify11/n11-run7/planted_plus_one_report.json
```

Verdict: `VERIFY11_FAIL`; process exit status 1/1 expected failure status.

- Terms checked: 15,896/15,896; DP columns 15,896/15,896.
- Bad linear rows: 9/11; first bad linear residual `2822400/1`.
- Bad hinge rows: 23,011/169,166; first bad hinge residual `80640/1`.
- Mutant common denominator: `31040975848430974402390020701903357221464788368928297084263726551477370244737050508531573901482703297988991672610503602927913049577479499773520196901216019559755648991358920327741375713713756125753330981090099200000`.
- Internal compute wall: 2,691.084727443 seconds/15,896 terms at 4 threads.
- External elapsed wall: 2,691.28 seconds/15,896 terms (`44:51.28`) at 4 threads.
- Peak RSS: 441,444 KiB/process at 4 threads.
- Temporary mutant SHA-256: `365852887a705cb0c753d7954eca43f1fe45dcee22dbeccbe991c5f3f9f55fa7`.
- Negative-control report SHA-256: `73cd1761f869b8dfc6b35835092efc44ed69203737e35e621ebfc150a67d05d4`.

## No-claim

This is a T1 check of one supplied finite exact certificate under the frozen verify11 semantics. It exactly checked every row represented by that verifier and passed the stated controls, but it is not the independent T2 referee review and is not, by itself, a theorem or an unrestricted depth result. The temporary mutant was not committed. No certificate copy was committed in this report directory.
