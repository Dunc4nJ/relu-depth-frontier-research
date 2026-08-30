# G-0068 — natural single-edge degree-five kernel gate

## What this gate actually tests

The public MAX10 certificate has 252 eligible support terms.  Attaching the
new coordinate once to each branch gives 25,200 raw single-edge lifts and
13,419 registered orbit representatives:

- 9,804 same-component classes;
- 3,615 cross-component classes.

The first proposed rank subject was all 13,419 columns.  That formulation is
wrong: exact multiset cancellation shows that 1,877 same-component classes
have the same appended edge in both branches.  They are signed mass four, not
five, and are automatically zero on degree-five-only rows.  The frozen
genuine-mass-five subject therefore has 11,542 columns:

- 7,927 same-component classes;
- all 3,615 cross-component classes.

Even that restriction does not make the high-degree matrix full rank.  Three
independently found genuine mass-five same-family representatives have an
exactly empty degree-five-only fingerprint:

| Same class | Boolean charge | Nonzero lower-degree hinges | Full normal-form SHA-256 |
|---:|---:|---:|---|
| 161 | 0 | 13,208 | `f974ab397de0a03e7f177ba87a05ecbbc2ab879f0033c37033fa5b1ae53e458a` |
| 3,600 | 0 | 13,818 | `bbf1a2120103c99fe246d5cca61274c60a9794e1c7556ac0d329f6cbc9f4ad02` |
| 7,172 | -12 | 16,108 | `f8d330b3fcbaca7d5dc0562828b2a6684614dabcd351eafc2b1e109ad6ebfcab` |

Class 7,172 is the immediate constructive lead: it has no `D5 \ D4` hinges
but has nonzero exact Boolean Möbius charge.  Its complete lower-degree normal
form must be projected through the exact lower-mass quotient; it must not be
discarded as a failed high-degree column.

## Complete row universe

Using the independently bound G-0054 direction-universe implementation:

```text
|D4|       =  99,858
|D5|       = 657,822
D4 subset D5
|D5 \ D4|  = 557,964
```

The lexicographically ordered `D5 \ D4` list has canonical compact-JSON
SHA-256

```text
657f53d4eccbf3ef7cd97b14baef4f6d2e9a7629aee9181d2cc8956bd2f296f1
```

Its first and last rows are respectively

```text
(0,0,0,0,0,0,0,0,1,-5,4)
(4,0,0,0,0,0,0,0,0,-5,1)
```

For a primitive zero-sum direction, membership in `D5 \ D4` is equivalently
positive-coordinate mass exactly five.  The stream can therefore classify a
hinge without materializing a 557,964-entry row dictionary.

## Exact decision logic

The full execution performs these steps in order:

1. reconstruct and hash-bind all registered representatives;
2. cancel common branch edges and retain the 11,542 genuine mass-five atoms;
3. regenerate every complete exact semantic normal form with G-0049's
   subset dynamic program;
4. partition columns into exact zero-high and nonzero-high blocks;
5. persist every zero-high descriptor, Boolean charge, and complete
   lower-degree normal form;
6. rank a deterministic CountSketch of only the nonzero-high block.

The theorem boundary is deliberately one-sided:

> After explicit zero-high columns are removed, full sketch column rank
> certifies full degree-five-only matrix column rank for the remaining block.
> Sketch deficiency is inconclusive pending complete-row kernel replay.

If the nonzero-high sketch reaches its column-count upper bound, left
multiplication could not have increased rank.  A nonzero modular maximal minor
is a nonzero integer minor, so the result holds over `Q` and `R`.  The complete
high-degree kernel is then exactly the coordinate span of the emitted
zero-high columns.

If the sketch is deficient, that deficiency is not a dependency of the full
matrix: CountSketch may destroy rank.  No modular kernel is promoted until it
is replayed on every one of the 557,964 rows and, for a positive result, lifted
and replayed exactly over `Q`.

## Resumable first-pass cache

The multi-hour semantic pass is written in immutable 128-column shards.  Each
shard binds:

- script and upstream input hashes;
- subject descriptors and ordering;
- prime, seed, bucket count, and complete row-universe hash;
- the `uint32` sketch matrix and its file/scientific hashes;
- every per-column semantic digest and statistics;
- complete lower-degree normal forms for zero-high columns.

Resume is fail-closed.  If both files in a shard pair exist, they are fully
validated and reused.  If neither exists, the pair is written atomically once.
A lone file, stale partial, overwrite attempt, hash drift, or contract drift
aborts.

The default direction-keyed row-map contract is

```text
91b2d66c8c9893779f0fe3e440b2a1d48700b957fceea264a03bc340c2dbdc9c
```

Extension caches are separate immutable manifests that bind this same
contract hash.  This lets the compact charged novel-tree block—or the broader
6,507-column schedule—be appended after the natural basis without regenerating
or overwriting it.

The frozen post-census compact extension descriptors are the following 32
combined-union columns (ordered-list SHA-256
`b3c64d69bb69efbde44b8d903ecbfc94f6def25525972592e1cf3cc2efbf779c`):

```text
13831 13921 14293 14295 14300 14305 14444 14558
14559 14580 14881 15160 15163 15165 15181 15609
15782 16031 16247 16656 16666 17140 17362 17384
17581 18558 19321 19418 21886 21901 21927 22161
```

They are explicitly post-census: G-0068 does not mix them into its smoke or
base-family rank.  A follow-on extension cache must bind the identical row-map
contract and append them only after the natural zero/nonzero-high partition is
complete.

## Reproduction and safety latch

The self-test checks the raw-family partition, the three exact zero-high
witnesses and charges, direct versus streamed sketching, FLINT rank controls,
the one-sided deficiency boundary, and a write/reload/no-overwrite cache
roundtrip:

```bash
.venv/bin/python -B artifacts/math/G-0068/single_edge_degree5_kernel_gate.py \
  --self-test
```

The preflight independently regenerates the complete row census/hash and
reports memory planning:

```bash
.venv/bin/python -B artifacts/math/G-0068/single_edge_degree5_kernel_gate.py \
  --preflight-only --sketch-buckets 16384 --minimum-available-gib 20
```

The committed smoke artifact uses only six columns: one nonzero-high same
control, the three zero-high witnesses, and the first/last cross controls.  It
does two independent semantic passes and does not create the large cache:

```bash
.venv/bin/python -B artifacts/math/G-0068/single_edge_degree5_kernel_gate.py \
  --smoke --workers 4 --sketch-buckets 16384 --progress-every 0 \
  --output artifacts/math/G-0068/single_edge_degree5_kernel_gate_smoke_v1.json.gz
```

The frozen full run was launched only after EXP-0008 was committed.  It
requires an explicit `--full`, always persists its resumable cache, and refuses
`--no-write`:

```bash
.venv/bin/python -B artifacts/math/G-0068/single_edge_degree5_kernel_gate.py \
  --full --workers 8 --sketch-buckets 16384 --shard-columns 128 \
  --minimum-available-gib 20 --progress-every 100 \
  --cache-dir artifacts/math/G-0068/single_edge_degree5_sketch_cache_v1 \
  --output artifacts/math/G-0068/single_edge_degree5_kernel_gate_v1.json.gz
```

The frozen output path now exists and is immutable, so the command fails closed
rather than overwriting the report.  A replay must use a fresh direct-child
output path while reusing and validating the existing cache.

## Executed smoke result

The six-column smoke completed in 37.73 seconds with
`SMOKE_PASS_NO_THEOREM`.  Its three frozen zero-high columns replayed as exact
zeros; the remaining three-column block had sketch rank three.  The spawned
stream and independent direct second pass agreed on all 5,065 nonzero rows in
their complete sample union, including a coefficient-`+1` mutation control.

The full-run planning report for a `16,384 x 11,542` `uint32` sketch was 0.704
GiB for the persisted matrix and 10.45 GiB conservative peak under the current
Python-to-FLINT bridge.  This was a planning estimate, not a memory bound.

Frozen hashes:

```text
single_edge_degree5_kernel_gate.py
  80b467fe65835a3d36c5adde9a87bb8191b38f69734718784db38f0b356a7f61
single_edge_degree5_kernel_gate_smoke_v1.json.gz
  acd480159ca760b29914c48691b3a3899a972db6e25a038f563a7e911189065b
```

## Executed full result

The complete semantic census finished in 2,646.79 seconds.  It regenerated all
11,542 genuine-mass-five columns, partitioned exactly 526 zero-high columns and
11,016 nonzero-high columns, and then ranked the frozen deterministic sketch of
the nonzero-high block:

```text
nonzero-high columns          11,016
sketch rank mod 1,000,003      6,626
displayed sketch deficiency    4,390
result                         INCONCLUSIVE_PENDING_COMPLETE_ROW_KERNEL_REPLAY
```

This is not a 4,390-dimensional kernel of the complete matrix.  Left sketching
can lower rank, so the deficiency is only a trigger for a second map or exact
complete-row kernel replay.  It proves neither a construction nor an
obstruction.

The zero-high block is exact rather than sketch-inferred.  All 526 columns are
same-family.  Their ordered subject-index digest is
`b7be6bac98d5600cd4901ec3234ef3182504237ffda4f336da164cef380ab441`.
An independent alternating-cycle structure verifier produced the same ordered
class list and matched all 526 complete semantic-column digests; no cross-family
zero-high column exists in this pinned family.

Frozen output hashes:

```text
single_edge_degree5_kernel_gate_v1.json.gz
  08c6d3e180abe3c41be00a1db70c9829b736db68c8c7285fe7eecb8568ec1d35
single_edge_degree5_sketch_cache_v1/manifest.json.gz
  c4ec8058ef1e27d6eeaab70724cd5e28d9ae3125c6f669e144eb3f4be1690433
zero_high_structure_verifier_v1.json.gz
  fb909ed5f675b6b937e26e5929033513e3da6f3294e0df8e934b91dcd4ebe444
```

The immediate constructive gate is therefore the joint exact lower-degree
quotient of all 526 zero-high columns against the rank-1,288 S1 basis.  That
test is logically independent of whether the 4,390 sketch deficiency survives
complete-row replay: any exact relation with nonzero Boolean charge can be
lifted and compiled immediately.

## Claim boundary

The full artifact proves the exact 526/11,016 zero/nonzero-high partition, but
its deficient sketch characterizes no additional kernel.  The emitted
zero-high columns remain potentially constructive and require an exact
lower-degree quotient test.  A two-prime no-gain result there would still be
modular evidence only; retirement requires an exact rational dual/row-span
certificate or an exact-`Q` kernel basis whose entire target/charge pairing is
zero.

Nothing here covers the other active-11 mass-five atoms, higher signed masses,
asymmetric atoms, or unrestricted two-hidden-layer ReLU networks.
