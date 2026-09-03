# F2 forest-pair candidate: verify11 T1 result

Date: 2026-09-03 (Europe/Berlin)  
Bead: `relu-depth-frontier-research-max11-root-gmp.14`  
Coordination thread: `relu-depth-frontier-research-max11-root-gmp.4`  
Verifier source remained frozen throughout receipt, full verification, literal spot check, and planted negative.

## Frozen verifier and input

- Candidate: `artifacts/math/n11-stageA-exact-lift/member-F2-forestpair-m64000-p1000003-s1-cuda/member_upstream.json`
- Candidate bytes: 10,450,607 bytes/file.
- Candidate SHA-256: `767f9e66fd3dcb7b5c43e5ffdbbfa50967684d7b263c41cbd7c35e2db7938670` (exactly the orchestrator-supplied SHA-256).
- Release binary SHA-256: `bab4ab22fa0acaa2c49c5c91bc6fa5fb006afd7ed843f6a008049bc65d4d1eb9`.
- `tools/verify11/src/lib.rs` SHA-256: `5bc9a14f1df11fd027ff9f0e4bf3ac005e7f0d16364bd1f2c83cd1663a1667c5`.
- `tools/verify11/src/main.rs` SHA-256: `5d0299374c39288c21393f964a40ef42f26b408dd784cf270eec5b7ae627c203`.
- Arithmetic: exact integer accumulation after exact rational denominator clearing; no modular primes (`0/0` primes).

## Full DP verification: positive control

Exact command (the preceding `mkdir -p artifacts/math/verify11/n11-F2` only created the report directory):

```text
/usr/bin/time -v tools/verify11/target/release/max11-verify11 analyze --certificate artifacts/math/n11-stageA-exact-lift/member-F2-forestpair-m64000-p1000003-s1-cuda/member_upstream.json --threads 4 --output artifacts/math/verify11/n11-F2/full_dp_report.json
```

Verdict: `VERIFY11_OK`.

- Terms checked: 11,320/11,320 supplied terms; nonzero terms 11,320/11,320; DP columns 11,320/11,320.
- Linear rows exact: 11/11; bad linear rows 0/11.
- Hinge rows exact: 145,530/145,530; bad hinge rows 0/145,530.
- Emitted hinge entries accumulated: 370,466,002/370,466,002.
- Coefficient common denominator (one denominator for the exact cleared system): `2032384268838473579482535490442063909129682057809661017159659920134519970817370311316991044308899378691892477647865002625338395403654427827258452332289146057714892015588003235501956737918366591328159078464129440153600000`.
- Coefficient numerator decimal digits: minimum 1 digit/coefficient, maximum 229 digits/coefficient.
- Coefficient denominator decimal digits: minimum 6 digits/coefficient, maximum 220 digits/coefficient.
- Internal compute wall: 1,444.807190509 seconds/11,320 terms at 4 threads.
- External elapsed wall: 1,444.94 seconds/11,320 terms (`24:04.94`) at 4 threads.
- Peak RSS: 369,920 KiB/process at 4 threads.
- Full report SHA-256: `330ff0353f2e25118aaf04479f4b490cf77b00669bdbfc03aca734349f094bc8`.

## Literal-permutation versus DP spot check

The sample was selected deterministically without replacement with seed `20260904`:

```text
tools/verify11/target/release/max11-verify11 sample --certificate artifacts/math/n11-stageA-exact-lift/member-F2-forestpair-m64000-p1000003-s1-cuda/member_upstream.json --terms 20 --seed 20260904 --output artifacts/math/verify11/n11-F2/sample20_seed20260904.json
/usr/bin/time -v tools/verify11/target/release/max11-verify11 analyze --certificate artifacts/math/verify11/n11-F2/sample20_seed20260904.json --threads 4 --literal-check --output artifacts/math/verify11/n11-F2/sample20_literal_dp_report.json
```

- Literal/DP matches: 20/20 sampled terms.
- Literal permutations: 39,916,800 permutations/term; 798,336,000/798,336,000 total sampled permutations.
- Sample terms checked by DP: 20/20.
- Sample common denominator: `508096067209618394870633872610515977282420514452415254289914980033629992704342577829247761077224844672973119411966250656334598850913606956814613083072286514428723003897000808875489184479591647832039769616032360038400000`.
- Internal compute wall: 101.362058394 seconds/20 terms at 4 threads.
- External elapsed wall: 101.57 seconds/20 terms (`1:41.57`) at 4 threads.
- Peak RSS: 284,480 KiB/process at 4 threads.
- The subset's whole-identity verdict is `FAIL`, as expected for only 20/11,320 terms; this was not weakened or treated as a failed spot check.
- Sample JSON SHA-256: `378d172ebcf106b0e94f9e5c6ce6854fbd52e0be3d3fa829a9013d8122520517`.
- Literal/DP report SHA-256: `105a77bbbd032b84b0f0e05e079821a4eb1dd980e9be585ee438ee9e294677a4`.

## Planted `+1` coefficient negative control

The mutation was made in an uncommitted temporary copy; the candidate was not modified.

```text
tools/verify11/target/release/max11-verify11 mutate-coefficient --certificate artifacts/math/n11-stageA-exact-lift/member-F2-forestpair-m64000-p1000003-s1-cuda/member_upstream.json --output /tmp/verify11-f2-mutant.a3c7Ug/member_upstream_coefficient_plus_one.json
/usr/bin/time -v tools/verify11/target/release/max11-verify11 verify --certificate /tmp/verify11-f2-mutant.a3c7Ug/member_upstream_coefficient_plus_one.json --threads 4 --output artifacts/math/verify11/n11-F2/planted_plus_one_report.json
```

Verdict: `VERIFY11_FAIL`; process exit status 1/1 expected failure status.

- Terms checked: 11,320/11,320; DP columns 11,320/11,320.
- Bad linear rows: 9/11; first bad linear residual `3225600/1`.
- Bad hinge rows: 7,853/145,530; first bad hinge residual `20160/1`.
- Mutant common denominator: `2032384268838473579482535490442063909129682057809661017159659920134519970817370311316991044308899378691892477647865002625338395403654427827258452332289146057714892015588003235501956737918366591328159078464129440153600000`.
- Internal compute wall: 1,558.698554090 seconds/11,320 terms at 4 threads.
- External elapsed wall: 1,558.81 seconds/11,320 terms (`25:58.81`) at 4 threads.
- Peak RSS: 387,144 KiB/process at 4 threads.
- Temporary mutant SHA-256: `e95bf773e8af47d12eda2ffa147965b9930d18c5c7791a284168e157ff5134fa`.
- Negative-control report SHA-256: `a14ed9f281546d975532506b66f1e02393cb503c54367eb4a6bc460e00ab138b`.

## No-claim

This is a T1 check of one supplied finite exact certificate under the frozen verify11 semantics. It exactly checked every row represented by that verifier and passed the stated controls, but it is not the independent T2 referee review and is not, by itself, a theorem or an unrestricted depth result. The temporary mutant was not committed. No certificate copy was committed in this report directory.
