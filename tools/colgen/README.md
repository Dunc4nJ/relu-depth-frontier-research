# `max11-colgen`

Exact sparse-column generation for the loopless signed-`W` atom family used by
the MAX11 campaign.  The crate is an engineering dependency for later modular
rank work; it does not decide membership in the span.

## Normal-form convention

For a loopless signed record `W = B - A`, an ordering
`pi = (v_0,...,v_{n-1})` has raw back-degree word

```text
w_r(pi) = sum_{t<r} W[v_r,v_t].
```

Let `d` be `w/gcd(w)` oriented so its first nonzero entry is positive.  Every
ordering contributes `gcd(w)` to the retained primitive hinge `d`, unless all
proper prefix sums of `d` are nonnegative (then the hinge vanishes on the
sorted cone).  When the first nonzero entry of `w` is negative, the word `w`
is also folded into the linear part by `ReLU(-z) = ReLU(z) - z`.  With `k`
loopless occurrences in each uncancelled branch, the fixed base is

```text
ell_r(base) = 2*k*r*(n-2)!.
```

This is exactly the convention map to
`handoff/2026-09-02-amberbluff/probes/loopless_probe_par.py`: Python chooses
the lexicographically smaller of the two branch words as its linear summand.
For `W=B-A`, that smaller word is `A` when the first nonzero entry of `w` is
positive, and `B=A+w` otherwise.  The saved Python hinge orientation, gcd
normalization, and ordered-cone pruning therefore agree coefficient for
coefficient.

The generator rejects loops deliberately.  The signed record type and base
calculation are isolated so the G-0040 diagonal increment and loop/nonloop
padding convention can be added without changing the column and stream APIs.

## Build and checks

```bash
cargo build --release
cargo test --release
cargo clippy --all-targets --all-features -- -D warnings
```

Full saved-system validation:

```bash
target/release/max11-colgen validate-templates \
  --input ../../handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
  --n 9 --branch-edges 4 --threads 3 --output n9-validation.json
```

Add `--bruteforce` at `n <= 7` to compare the subset dynamic program with
literal enumeration of all `n!` orderings for every input template.  Add
`--mutate-one-sign` to plant an invalid one-occurrence sign flip; the command
must fail rather than write a report.

The G-0028 scalar-price control recomputes a complete exact sparse column for
each of the 13,419 registered records, dots it with both frozen modular duals,
and checks the two complete little-endian residue-vector hashes:

```bash
target/release/max11-colgen validate-prices \
  --universe ../../artifacts/math/G-0028/g0025_registered_loopless_signed_records_v1.json.gz \
  --dual ../../artifacts/math/G-0028/g0025_rank_one_sparse_modular_dual_v1.json \
  --expected-report ../../artifacts/math/G-0028/g0025_registered_delta_replay_v1.json \
  --threads 6 --output g0028-validation.json
```

## Streaming commands

`benchmark` draws a deterministic without-replacement SplitMix64 sample and
reports every mean/extrapolation with its sample denominator. `scan-universe`
computes the exact support union and total nonzero count for its stated range.
`emit-universe` writes exact integers or residues modulo one named modulus in
ordered batches, so memory is bounded by a small multiple of the largest
column rather than the whole matrix.

```bash
target/release/max11-colgen benchmark \
  --universe ../../artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --sample-size 1000 --seed 20260902 --threads 6 --output benchmark.json

target/release/max11-colgen scan-universe \
  --universe ../../artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --threads 6 --output support-scan.json

target/release/max11-colgen emit-universe \
  --universe ../../artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --threads 6 --start 0 --limit 1000 --format binary --modulus 1000003 \
  --output columns-p1000003.bin
```

`emit-universe` also accepts a duplicate-free `--order-file INDICES.json` in
place of `--start`/`--limit` and preserves those original source indices in
that order. For the G-0027 exact lift, `--include-five-l true` appends source
index 754,017 with eleven linear coefficients 18,144,000 and no hinges. The
CLI accepts up to 16 threads for the authorized remote compute path; shared
host runs remain operationally capped by the campaign instructions.

JSONL has one object per record with `record_index`, optional `modulus`, the
linear vector, and sorted `{direction, coefficient}` hinge entries.  Compact
binary is little-endian:

```text
magic[8]="MCOLGEN1"
n:u16, branch_edges:u16, modulus:u64 (0 means exact), record_count:u64
repeat record_count:
  record_index:u64
  linear[n]:i64
  hinge_count:u64
  repeat hinge_count: direction[n]:i16, coefficient:i64
```

All multiplicities, factorials, linear corrections, bases, and output
coefficients use checked arithmetic.  Inputs outside the supported `2 <= n <=
16` or loopless balanced signed-record contract fail closed.

## Boundary

Column equality is global algebra on the registered symmetrized atom, but the
family is finite and restricted.  A successful rational combination verified
on every complete normal-form row would settle MAX11 existence; this generator
alone provides no combination.  A negative rank result in this family would
be only a bounded null and would not establish an unrestricted two-hidden-layer
lower bound.
