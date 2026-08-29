# G-0054 clean-room exact S0 rank audit

## Verdict

**HARD PASS, with an exact bounded upgrade.** For the frozen 1,465 full-core
mass-four columns,

```text
rank_Q(H) = rank_Q([H; lambda]) = 867.
```

Thus this S0 column set contains no rational hinge-cancelling combination
with nonzero `lambda`. This is an exact negative for S0, not merely agreement
at two primes.

The G-0054 producer was right to leave its exact conclusion null: its two
finite-field computations alone did not earn a rational theorem. This audit
adds the missing exact evidence by independently lifting and replaying the
complete kernel.

## Why the exact conclusion follows

1. A separately reconstructed `867 x 867` integer minor has determinant
   `940763 mod 1000003` and `985434 mod 1000033`. Either nonzero residue proves
   that the integer determinant is nonzero, so `rank_Q(H) >= 867`.
2. The two modular certificates have identical supports for all 598 kernel
   vectors. CRT plus unique rational reconstruction yields 598 primitive
   integer vectors: 7,764 sparse entries, support sizes 3 through 60, and
   maximum absolute coefficient 24.
3. The audit replays those vectors on every one of the 99,858 complete
   degree-four rows. Every integer residual is exactly zero. Distinct unique
   coordinates prove the 598 vectors independent, so
   `nullity_Q(H) >= 598` and `rank_Q(H) <= 1465 - 598 = 867`.
4. The audit recomputes `lambda` directly from each raw signed core using the
   binary-chamber formula, matches G-0052 entry by entry, and obtains exact
   zero against all 598 integer vectors. The vectors are therefore a complete
   basis of `ker_Q(H)`, and `lambda` lies in the rational row span of `H`.

The exact integer replay uses a worst-case hinge accumulator bound of
250,822,656 and lambda bound of 258,660,864,000, both strictly below signed
`int64`. No floating-point zero test is involved.

## Independently replayed facts

| Quantity | Audit result |
|---|---:|
| complete rows | 99,858 |
| frozen S0 columns | 1,465 |
| reconstructed nonzeros | 12,331,131 |
| exact nonzero-row union | 42,457 |
| finite-field rank at both primes | 867 |
| exact kernel vectors | 598 |
| exact sparse coefficients | 7,764 |
| support min / median / max | 3 / 8.5 / 60 |
| rational denominator counts `1 / 2 / 4` | 7,022 / 686 / 56 |
| vector denominator-LCM counts `1 / 2 / 4` | 415 / 155 / 28 |
| maximum rational numerator magnitude | 13 |
| maximum primitive integer coefficient magnitude | 24 |

The primitive integer basis SHA-256 is
`96fd94111df58828ea1efc5c969f8f1f12c28a7624cab1f759b5da60da09069b`.
The independently reconstructed lambda-vector SHA-256 is
`f7700f52883e107bbc5d94b7d7c183d50f316178b45babdd6342a22351bc4e71`.

## Claim boundary and research consequence

This result covers only the 1,465 frozen **full-core** mass-four S0 columns.
It excludes 132,728 proper-core mass-four columns. A negative on S0 does not
rule out a circuit after adding other columns, and it proves no mass-four-wide
or unrestricted MAX11 obstruction.

The useful update is surgical: the S0-only circuit search is now exactly
closed and should not receive more compute. Any continued mass-four search
must add genuinely new columns or exploit a structural reduction that proves
those columns irrelevant.

## Artifact bindings and replay

- verifier SHA-256:
  `5d3088ae13fe2d4455e5d662a56ab3e112457959d3d61923a82b8511664d1967`
- report SHA-256:
  `ed6669bd80514c7178ef97be2fd866e145d88c9040cafe5d7c7b569646385cf0`
- report canonical-payload SHA-256:
  `d233b35c28945dae14a75c11bbc9812d8ead7bef2319984975164e830a2de425`
- frozen G-0054 README / script / report SHA-256:
  `4842f4d6e72200a5ef39a27cf949375004d3f0fb929162bf506b1538ac71c277`,
  `cf8b4527863a02b97e169c4473c728d6f8f5c14bc37e6351e3b7e42ac11a6fe2`,
  `c9a80de54a367cd78eac820cac83568508fa65afbc9a26f74c941495ff334053`

```bash
python -B artifacts/cleanroom/G-0054-rank-audit/independent_s0_rank_audit.py --self-test
python -B artifacts/cleanroom/G-0054-rank-audit/independent_s0_rank_audit.py \
  --workers 8 \
  --output artifacts/cleanroom/G-0054-rank-audit/replay.json
```

## Anti-ceremony and honesty record

Creation gate: the consumer is the research lead deciding whether to promote
G-0054; the gate is an exact S0 rank/no-gain conclusion; the observed risk is
promotion from agreeing modular ranks without an exact upper certificate.
This audit retires when that decision is recorded. It consists of one
executable verifier, one machine-readable report, and this bounded handoff.

The first full semantic run stopped because the audit compared the subject's
raw little-endian `uint32` row-index digest to a JSON digest. That was an
audit-side encoding error, not a subject defect; it was corrected explicitly.
The final verifier then completed all 1,465 columns, both independent
determinants, all 598 modular replays, and all 598 exact integer replays. A
second full run after adding raw-record lambda reconstruction also passed.

No test was weakened or skipped; no mock, regenerated golden, solver-status
substitute, floating tolerance, post-selected prime, suppressed failure, or
hidden exception was used. The producer's cautious null exact conclusion is
preserved as honest-at-delivery rather than retrospectively relabelled. The
strongest evidence is the complete exact integer kernel replay; agreement of
two modular ranks or two implementations is treated only as triangulation.
