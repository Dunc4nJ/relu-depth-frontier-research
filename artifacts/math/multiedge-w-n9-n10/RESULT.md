# gmp.9 — multi-edge loopless W span at n=9 and n=10

## Outcome

**Yes: multi-edge signed-W records add span at both n=9 and n=10.**  The
complete degree-four loopless W family has rank 2,232 rather than 1,506 at n=9,
and rank 3,108 rather than 2,166 at n=10, identically over both registered
fields `F_1,000,003` and `F_1,000,033`.  Multiplicity exactly 2 and exactly 3
add dimensions; multiplicity exactly 4 adds none after the lower strata.

The simple-W prefix already contains `MAX_n` at both arities, so every
cumulative multi-edge superset also contains it.  This is witnessed by equal
rank and augmented rank in every table row.  The result rejects the hypothesis
that the simple-W columns carry the complete loopless span at low arity.  It
does **not** decide whether they contain `MAX_11`, nor whether multi-edge columns
add rank at n=11.

“Simple prefix” below means maximum absolute edge multiplicity at most one and
includes the single `W=0` record.  Thus the requested denominators are
6,197/16,311 records at n=9 and 7,203/17,775 records at n=10.  Excluding `W=0`,
the exact-multiplicity-one counts are 6,196/16,311 and 7,202/17,775.

## Complete modular rank tables

`r/R` and `a/R` are rank and augmented rank over the complete normal-form row
denominator `R`.  The two prime rows are independent finite-field runs.  `M`
means `MAX_n` is a member over the named field.

### n=9

There are 8,304/8,304 normal-form rows: 8,295 hinge directions and 9 linear
coordinates.

| cumulative family | columns / 16,311 W | added columns | rank / 8,304 | augmented rank / 8,304 | added dimensions / added columns | MAX |
|---|---:|---:|---:|---:|---:|:---:|
| max multiplicity <= 1 | 6,197/16,311 | 6,197 | 1,506/8,304 | 1,506/8,304 | 1,506/6,197 | M |
| + multiplicity 2 | 14,920/16,311 | 8,723 | 2,148/8,304 | 2,148/8,304 | 642/8,723 | M |
| + multiplicity 3 | 16,185/16,311 | 1,265 | 2,232/8,304 | 2,232/8,304 | 84/1,265 | M |
| + multiplicity 4 = all | 16,311/16,311 | 126 | 2,232/8,304 | 2,232/8,304 | 0/126 | M |

This entire table is identical at 2/2 primes: 1,000,003 and 1,000,033.

### n=10

There are 20,695/20,695 normal-form rows: 20,685 hinge directions and 10
linear coordinates.

| cumulative family | columns / 17,775 W | added columns | rank / 20,695 | augmented rank / 20,695 | added dimensions / added columns | MAX |
|---|---:|---:|---:|---:|---:|:---:|
| max multiplicity <= 1 | 7,203/17,775 | 7,203 | 2,166/20,695 | 2,166/20,695 | 2,166/7,203 | M |
| + multiplicity 2 | 16,365/17,775 | 9,162 | 3,013/20,695 | 3,013/20,695 | 847/9,162 | M |
| + multiplicity 3 | 17,648/17,775 | 1,283 | 3,108/20,695 | 3,108/20,695 | 95/1,283 | M |
| + multiplicity 4 = all | 17,775/17,775 | 127 | 3,108/20,695 | 3,108/20,695 | 0/127 | M |

This entire table is identical at 2/2 primes: 1,000,003 and 1,000,033.

## Exact-Q controls at n=7 and n=8

The optional small-arity leg remained cheap enough to finish with
`python-flint` integer RREF.  These are exact rational ranks, not modular
estimates.

| n | cumulative max multiplicity | columns / complete W universe | exact-Q rank / normal-form rows | exact-Q augmented rank / rows | added dimensions / added columns | MAX |
|---:|---:|---:|---:|---:|---:|:---:|
| 7 | <=1 | 2,034/8,282 | 296/931 | 296/931 | 296/2,034 | M |
| 7 | <=2 | 7,152/8,282 | 512/931 | 512/931 | 216/5,118 | M |
| 7 | <=3 | 8,166/8,282 | 553/931 | 553/931 | 41/1,014 | M |
| 7 | <=4 | 8,282/8,282 | 553/931 | 553/931 | 0/116 | M |
| 8 | <=1 | 4,315/13,146 | 776/2,983 | 776/2,983 | 776/4,315 | M |
| 8 | <=2 | 11,821/13,146 | 1,196/2,983 | 1,196/2,983 | 420/7,506 | M |
| 8 | <=3 | 13,022/13,146 | 1,262/2,983 | 1,262/2,983 | 66/1,201 | M |
| 8 | <=4 | 13,146/13,146 | 1,262/2,983 | 1,262/2,983 | 0/124 | M |

The common integer-RREF denominators were 120,960 at n=7 and 65,318,400 at
n=8.  The same qualitative pattern therefore holds for 4/4 checked arities:
multiplicities 2 and 3 add span, while multiplicity 4 adds no further span.
Only n=7 and n=8 were checked over Q; n=9 and n=10 were not.

## Exhaustive universe census and Burnside cross-check

The enumerator uses G-0027's incidence-graph canonical form unchanged.  For
each uncoloured absolute multigraph with a valid balanced twin-monochromatic
signing, it computes sign orbits two ways:

1. explicit traversal under pynauty automorphism generators and global sign
   reversal;
2. Burnside's lemma, summing fixed valid sign masks over the closed induced
   action group.

The two counts agreed graph-by-graph for every valid denominator below.  A
fresh `verify_outputs.py --replay-enumeration` run regenerated all four record
streams and matched both the record-stream hashes and full census objects.

| n | absolute multigraphs | with valid signings | signed-W orbits | exact multiplicity counts `0,1,2,3,4` / total |
|---:|---:|---:|---:|---|
| 7 | 1,502/1,502 | 1,430/1,502 | 8,282/8,282 | 1, 2,033, 5,118, 1,014, 116 / 8,282 |
| 8 | 2,030/2,030 | 1,957/2,030 | 13,146/13,146 | 1, 4,314, 7,506, 1,201, 124 / 13,146 |
| 9 | 2,354/2,354 | 2,281/2,354 | 16,311/16,311 | 1, 6,196, 8,723, 1,265, 126 / 16,311 |
| 10 | 2,520/2,520 | 2,447/2,520 | 17,775/17,775 | 1, 7,202, 9,162, 1,283, 127 / 17,775 |

The simple prefixes reproduce the required known answers exactly:
6,197/6,197 at n=9 and 7,203/7,203 at n=10, each including `W=0`.

## What this does to the n=11 experiment

The frozen G-0027 census has these exact multiplicity strata:

| maximum multiplicity | records / 754,017 |
|---:|---:|
| 0 (`W=0`) | 1/754,017 |
| 1 | 243,467/754,017 |
| 2 | 436,335/754,017 |
| 3 | 67,265/754,017 |
| 4 | 6,457/754,017 |
| 5 | 492/754,017 |

Consequently, the n=11 cumulative sizes including `W=0` are 243,468/754,017
through multiplicity 1, 679,803/754,017 through multiplicity 2,
747,068/754,017 through multiplicity 3, 753,525/754,017 through multiplicity 4,
and 754,017/754,017 through multiplicity 5.  The exact multi-edge count
`max multiplicity >= 2` is 510,549/754,017.  The often-quoted complement
754,017 - 243,467 = 510,550 includes the single zero record and is therefore
“outside exact multiplicity 1,” not literally all multi-edge.

The 243,467 nonzero simple-W columns remain a legitimate one-sided n=11 MAX
probe: membership would be informative, but non-membership would not decide the
complete family.  They are no longer a calibrated proxy for full loopless span.
The low-arity data instead say that any staged full-span experiment must at
least plan to price multiplicity 2 and 3.  Carrying all records through
multiplicity 3 already costs 747,068/754,017 columns, so this route does not
deliver the hoped-for 3x full-span reduction at n=11.  No n=11 rank was run.

## Known-answer and negative controls

- `max11-colgen` passed 5/5 release tests: branch-swap invariance, literal
  permutation agreement, sign-corruption rejection, common-edge cancellation,
  and the zero-W base column.
- Saved-system validation recomputed 10,976/10,976 raw n=9 templates and
  12,248/12,248 raw n=10 templates with colgen.  All exact sparse integer
  columns matched.
- Canonical-key bridging then matched every enumerated simple-W representative
  to the saved system: 6,197/6,197 at n=9 and 7,203/7,203 at n=10.  This checks
  the actual enumerated representatives rather than only the generator on raw
  templates.  All 13,400/13,400 one-unit coefficient mutations were rejected.
- The simple-prefix rank gates passed at 2/2 primes: 1,506/8,304 rows at n=9
  and 2,166/20,695 rows at n=10, with equal augmented ranks.
- A real column was deliberately duplicated in each of 6/6 rank runs (four
  modular n=9/n=10 runs and two exact-Q n=7/n=8 runs).  It was non-pivot in
  6/6 runs and raised rank by 0/1 possible dimension each time.
- The bundle verifier accepted the unmodified bundle and rejected 2/2 planted
  corruptions: one rank-table entry and one stored record multiplicity.
- A preliminary n=9 CountSketch trial at prime 1,000,003, 16,384 buckets and
  2/2 deterministic seeds observed rank=augmented rank 2,232/16,384 buckets.
  It was an exploratory preview only; every reported table entry above comes
  from dense `python-flint`, not the sketch.

## Inputs, toolchain, and custody

Primary frozen inputs:

| file | SHA-256 |
|---|---|
| saved n=9 system | `729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991` |
| saved n=10 system | `bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18` |
| G-0027 n=11 universe | `8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8` |
| G-0027 README census source | `f0531ff45a3e4082f0a78a76e52e7333a0d5297df2634a00b0e93b99dd5a2474` |

Generated universes:

| n | SHA-256 |
|---:|---|
| 7 | `d1c6c77a355bc6a2e64fa5633029624d754bd712b9fd935406b14739a48a7ac2` |
| 8 | `9a4c698f69560d761ea1458b278a3bf8b5b1e7446faabb2dd0ad0917e9323a98` |
| 9 | `ed554d15161254d153df6aba638a9c89dbbb664e2ecaae09681df3cf95c6c41b` |
| 10 | `3e45f84d8413bdf97f3297d4410b0fa19c597a5520814458bebdc79c5ae2eb76` |

The exact colgen streams were too large to commit and are reproducible
transients.  They were present for the full bridge/rank/verifier runs and were
then removed after hashing:

| n | bytes | SHA-256 |
|---:|---:|---|
| 7 | 26,179,032 bytes | `ed94dff8c66bcef0c64cfc9c0b160694963b5c29bcda1a8f18a44c13bfbda281` |
| 8 | 150,387,004 bytes | `52f6cf3452da2828993dc435974e82ecc8c5cf0cb7bb259be306c161455c0a3a` |
| 9 | 607,123,414 bytes | `8cef996e205883c1eaaa5490561668653933c227226ce4e92fdd2b9721fbbde0` |
| 10 | 1,928,874,468 bytes | `a0f0deb8028210c99c51540de33a7ab3ddf3077984c6f2ad1a3692a6d8045ff7` |

The release colgen binary SHA-256 was
`32620edca7e14874c5065f421ae2fbe906339bcccdd67bdd0167223bd49e319f`;
`src/lib.rs` was
`81f6618d57c09fb1694f0b97a4e493853193f48249ddde5a7b612e795a850eb5`;
`src/main.rs` was
`cadc4d79cef6bfc9fe7a06a0207a60f79333d34da193355b382873a74f36cca1`.
The Python environment reported python-flint 0.9.0, pynauty 2.8.8.1 and
networkx 3.6.1.

Peak RSS denominators for the largest jobs were 2,481,872/12,582,912 KiB for
n=9 modular RREF, 6,796,784/12,582,912 KiB for n=10 modular RREF,
747,724/12,582,912 KiB for n=7 exact-Q RREF, and 2,227,196/12,582,912 KiB for
n=8 exact-Q RREF.  No computation used more than 6/6 allowed threads.

Resource deviation: at the packaging inbox check I first saw AmberBluff's newer
host-wide 4 GiB cap, issued while the Stage-A pilot was running.  Both n=10 RREF
jobs had already completed at approximately 6.80 GiB peak RSS, so 2/2 n=10
rank jobs exceeded that later 4 GiB cap even though they stayed below the
bead's original 12 GiB cap.  I disclosed this immediately in the bead thread;
no further large computation was launched after the message was read.

## Exact replay commands

Run from the repository root after `source scripts/activate-toolchain.sh`.
All producer commands refuse to overwrite existing outputs.

```bash
CARGO_BUILD_JOBS=6 cargo test --release --manifest-path tools/colgen/Cargo.toml
CARGO_BUILD_JOBS=6 cargo build --release --manifest-path tools/colgen/Cargo.toml

for n in 7 8 9 10; do
  python artifacts/math/multiedge-w-n9-n10/enumerate_degree4.py \
    --n "$n" --branch-edges 4 \
    --output "artifacts/math/multiedge-w-n9-n10/universe_n${n}_k4.json.gz"
done

tools/colgen/target/release/max11-colgen validate-templates \
  --input handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --n 9 --branch-edges 4 --threads 6 \
  --output artifacts/math/multiedge-w-n9-n10/colgen_validate_n9.json
tools/colgen/target/release/max11-colgen validate-templates \
  --input handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --n 10 --branch-edges 4 --threads 6 \
  --output artifacts/math/multiedge-w-n9-n10/colgen_validate_n10.json

for n in 7 8 9 10; do
  tools/colgen/target/release/max11-colgen emit-universe \
    --universe "artifacts/math/multiedge-w-n9-n10/universe_n${n}_k4.json.gz" \
    --threads 6 --format binary \
    --output "artifacts/math/multiedge-w-n9-n10/columns_n${n}_k4_exact.bin"
done

python artifacts/math/multiedge-w-n9-n10/verify_simple_columns.py \
  --n 9 \
  --universe artifacts/math/multiedge-w-n9-n10/universe_n9_k4.json.gz \
  --columns artifacts/math/multiedge-w-n9-n10/columns_n9_k4_exact.bin \
  --saved-system handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --output artifacts/math/multiedge-w-n9-n10/simple_bridge_n9.json
python artifacts/math/multiedge-w-n9-n10/verify_simple_columns.py \
  --n 10 \
  --universe artifacts/math/multiedge-w-n9-n10/universe_n10_k4.json.gz \
  --columns artifacts/math/multiedge-w-n9-n10/columns_n10_k4_exact.bin \
  --saved-system handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz \
  --output artifacts/math/multiedge-w-n9-n10/simple_bridge_n10.json

for n in 9 10; do
  for p in 1000003 1000033; do
    python artifacts/math/multiedge-w-n9-n10/rank_multiedge.py \
      --n "$n" --prime "$p" \
      --universe "artifacts/math/multiedge-w-n9-n10/universe_n${n}_k4.json.gz" \
      --columns "artifacts/math/multiedge-w-n9-n10/columns_n${n}_k4_exact.bin" \
      --output "artifacts/math/multiedge-w-n9-n10/rank_n${n}_p${p}.json"
  done
done

for n in 7 8; do
  python artifacts/math/multiedge-w-n9-n10/rank_exact_q.py \
    --n "$n" \
    --universe "artifacts/math/multiedge-w-n9-n10/universe_n${n}_k4.json.gz" \
    --columns "artifacts/math/multiedge-w-n9-n10/columns_n${n}_k4_exact.bin" \
    --output "artifacts/math/multiedge-w-n9-n10/rank_n${n}_Q.json"
done

python artifacts/math/multiedge-w-n9-n10/verify_outputs.py \
  --require-columns --replay-enumeration \
  --output artifacts/math/multiedge-w-n9-n10/verification.json
```

The final verifier command completed in 35.97 seconds, with 167,468 KiB peak
RSS, and accepted 1/1 unmodified bundle while rejecting 2/2 planted mutants.
The four dense modular rank commands are the authoritative rank replays; the
verifier deliberately does not silently rerun their approximately 33-minute
combined RREF cost.

## No-claim

This is a bounded computation over the complete finite loopless signed-W
degree-four universes at n=7,8,9,10.  It is not an n=11 rank or membership
result, not an exact-Q identity at n=9 or n=10, not a proof that multiplicity
4 or 5 is redundant at n=11, and not an unrestricted two-hidden-layer lower
bound or upper-bound construction.
