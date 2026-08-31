# G-0128 preregistration — 380-row exact-Q full-family master

## Timing, question, and claim boundary

This study is frozen on 2026-08-31 after the G-0126 complete global replay
refuted the G-0121 finite-row member and after the G-0127 coordinate-pricing
protocol was committed, but before this future file existed or any of its
coordinate values were computed or inspected:

```text
artifacts/math/G-0127/batch32_coordinate_prices_v1.json
```

Question: after retaining every one of the previous 348 exact rows and
adjoining the next 32 G-0126-selected hinge rows in their sealed receipt
order, is the fixed MAX11 target in the rational column span of **all 163,740
records** of the same frozen family?

The only admissible terminal outcomes are:

- `FULL_FAMILY_380ROW_EXACT_Q_MEMBER`: exact membership on this frozen
  380-row system; or
- `FULL_FAMILY_380ROW_EXACT_Q_NONMEMBER`: an exact integer separator on this
  frozen 380-row system that annihilates all 163,740 frozen columns and has
  nonzero target pairing.

Neither outcome is a global MAX11 identity, a family-completeness theorem, an
unrestricted two-hidden-layer lower bound, or a reason to begin Lean
formalization. A member is only a candidate for a separately preregistered
complete global replay. A nonmember is only a bounded obstruction for this
one frozen dictionary.

## Frozen continuation receipts

```text
dc77467b31c12b40eaec8b33bbe806d0c6f2ea8e2dac3f2731324deb3c1b9cac  artifacts/math/G-0123/full_family_master.py
9234415af8719ea0f46eaf7952d76cab006afe44e4d7e111813fde61e4a5032c  artifacts/math/G-0121/full_family_master_manifest_v1.json
53bc7d8894a3552c226ca64f51bf7b369ce1d7c71f532241b14271964abc1036  artifacts/math/G-0121/full_family_master_result_v1.json
28404e3832c4f98e14f54abad1c278d4d2e153bca35977783854c8f96e4030dc  artifacts/reviews/G-0123-full-family-master/AUDIT_VERDICT.md
d6dd969ae558c7e36eb420c1fa4fa2c1254875eeff073b8580809b6a50a2fadb  artifacts/math/G-0126/GLOBAL_REPLAY_PREREGISTRATION.md
a59f51ed491d50fb8d8e3e93e1a0f53dbc351a67a84fc2ae1f51bd18f74991f3  artifacts/math/G-0126/src/main.rs
14300697a23f010c349bcd2581f62ce85f1efa3b5a759c70d94b7894a8dedb6a  artifacts/math/G-0126/Cargo.toml
316421f8f8907349b9fb9b54a10ebe6bd4c3d4ddb9b44bc0294ff382f96dd45f  artifacts/math/G-0126/Cargo.lock
bd0410d861978956502e9d4c4fc1cd159565f2e170d70509abd0f3eb21b771ea  artifacts/math/G-0126/global_replay_v1.json
ddd823a8c63e42c74e07fd1cbee6a7c5fca573f10ab3deb8138674092bde0070  artifacts/math/G-0127/BATCH32_COORDINATE_PRICING_PREREGISTRATION.md
```

The G-0121 manifest's complete expected-input list remains part of the
scientific input. The G-0128 consumer must rehash and revalidate those
underlying sources and receipts rather than treating the G-0121 verdict as a
substitute for them. In particular, the 301-row signed-i128 panel cache, 11
linear coordinates, four accumulated coordinate documents, and previous
32-row exact-price receipt retain their original ordering and hashes.

The G-0126 receipt is fixed at:

```text
schema = max11-g0126-global-replay-v1
result = GLOBAL_MODULAR_RESIDUAL
selected_count = 32
selected signed-i8/u64-LE digest =
  0cd2699dec0bc5ffd7cb81c1454aac79143ae4a37c571fcb707c85a55a5c459e
exact selected residual decimal-LF digest =
  000ae45daea6c4debf91f47f3accd7877762b830c30945d31f1f1c97d3c7262b
```

The selected directions and residue pairs are consumed in the exact
serialized G-0126 order. Reordering, truncation, duplication, direction
invalidity, zero residues, changed exact residuals, or any receipt binding
drift is fatal.

## Future G-0127 receipt contract

The only accepted future coordinate receipt is:

```text
path   = artifacts/math/G-0127/batch32_coordinate_prices_v1.json
schema = max11-g0127-batch32-coordinate-prices-v1
result = EXACT_FULL_FAMILY_BATCH32_COORDINATES
```

It must bind the exact G-0126 receipt and the committed G-0127 protocol,
producer source, Cargo manifest/lockfile, running executable, panel input,
candidate, and normal-form kernel. It must reproduce the 32 G-0126 directions
and residues in receipt order, contain exactly `32 * 163740 = 5,239,680`
signed-i64 direction-major hinge entries and exactly `163740 * 11 = 1,801,140`
signed-i64 record-major/rank-minor linear entries, and pass every exact bridge
specified by G-0127.

The consumer independently recomputes every per-row digest, the aggregate
hinge digest, the linear digest, row counts, signed extrema, and nonzero
censuses. It independently recomputes the 131-term G-0121 candidate dot
product on each new row, requiring exact canonical equality to the matching
G-0126 residual, nonzero value, correct reduction modulo both ordered primes,
and the frozen decimal-LF digest above. The linear dot product must again be
zero in ranks 0 through 9 and `target_scale * 11!` in rank 10. Receipt labels
alone discharge none of these checks.

## Frozen 380-row system

Every family column has the following coordinates, in this exact order:

1. 301 cached panel entries;
2. 11 shared linear entries;
3. the four accumulated hinge rows from G-0117/G-0118;
4. all 32 previous G-0118 Batch32 rows in their existing exact receipt order;
5. all 32 new G-0126-selected rows in their exact receipt order.

Thus `301 + 11 + 4 + 32 + 32 = 380`. No previous row is discarded and no
dependency filter is run. Every new row is also kept conservatively. The
unscaled target is the frozen 301-entry panel target, then ten zeros and
`11!` in the final linear coordinate, then zero on all 68 hinge rows. No
previous candidate's denominator-cleared target scale is reused.

The manifest records all 64 Batch32 row decisions as
`KEPT_CONSERVATIVELY`, distinguishes their source receipts, and records no
discarded row or pivot-enrichment column.

## Frozen warm start and exact all-column algorithm

The initial selected columns are the 156 `selected_sequences` in the sealed
G-0121 result, which equal its 156 `support_sequences` and are sorted and
unique. Runtime must reconstruct their first 348 coordinates, verify the
G-0121 selected-basis signed-i128 digest, replay the old exact member, and
verify exact rank 156. Appending 32 coordinates cannot destroy that
independence; runtime nevertheless verifies exact rank 156 again on the full
380-row columns before any terminal decision.

Starting from that frozen warm basis, use the audited G-0123 exact
column-generation algorithm unchanged in substance:

1. construct the full 380-row matrix on the selected sequences;
2. compute exact ranks over `Q` for the matrix and its target augmentation;
3. if ranks agree, derive an exact rational member and replay every one of
   the 380 rows exactly;
4. if ranks differ, derive a primitive sign-normalized exact integer left
   separator with nonzero target pairing;
5. scan every family sequence `0..163739` in order, price the separator on
   the complete 380-coordinate column, and append the first exact nonzero
   column;
6. repeat, or emit nonmembership only after an exact zero scan over all
   163,740 columns.

Every appended column must increase exact rank by exactly one. The frozen
upper bound is `380 - 156 = 224` rank increases, so iterations are numbered
from 0 through 224 inclusive. The scan may omit zero separator coordinates
inside a dot product, but may not sample, skip, reorder, prefix-restrict, or
modular-screen family columns. Modular arithmetic may validate receipt
bridges but never decides rational membership or nonmembership.

Every iteration is serialized in the trial transcript with exact rank,
augmented rank, terminal/continuation result, separator target pairing and
free row when applicable, first violating sequence and exact price when
applicable, and exact scan census. No failed or intermediate trial is
omitted.

## Terminal certificates and normalization

On membership, compute independent pivot columns and coordinate rows, solve
exactly over `Q`, replay all 380 rows before and after denominator clearing,
remove zero terms, divide the integer coefficients and target scale by their
joint gcd, and normalize the scale positive. Emit the complete selected and
support sequences, coordinate rows, integer coefficients, primitive terms,
rank/augmented rank, and the signed-i128 digest of the full
`380 x final_rank` selected basis in row-major/column-minor order. Add one to
the first nonzero coefficient and require the mutant to fail an exact row.

On nonmembership, emit the primitive sign-normalized integer separator,
nonzero exact target pairing, exact all-163,740-column annihilation census,
rank/augmented rank, and complete transcript. Add one to its first nonzero
entry and require the mutant to break annihilation or kill the target
pairing.

## Frozen custody and hostile controls

The implementation is a minimal adaptation of audited G-0123 source SHA-256
`dc77467b...`. Before a scientific run it must provide a self-test retaining
all 15 final G-0123 hostile controls and adding controls for:

- G-0126 selected-order/residue/exact-residual mutation;
- G-0127 row truncation, row order, record order, extrema, nonzero census,
  aggregate stream, linear stream, and binding mutation;
- old/new Batch32 source-confusion or concatenation-order mutation;
- G-0121 warm-seed, basis-digest, term, coefficient, and target-scale
  mutation;
- a 348-row-only false member exposed by one of the 32 new rows;
- a `+1` member coefficient mutant and a `+1` separator mutant;
- stale source, preregistration, manifest, prior result, future receipt, or
  underlying expected-input bytes;
- cache truncation, ragged 380-row columns, path escape, duplicate manifest
  inputs, output overwrite, and serialization abort.

The scientific manifest is created only after G-0127 is sealed at:

```text
artifacts/math/G-0128/full_family_master_manifest_v2.json
```

It uses schema `max11-g0128-full-family-master-manifest-v2`, binds this
preregistration, the exact solver source, every frozen prior input, the
complete G-0126 and G-0127 receipts and their transitive scientific bindings,
the 380-row ordering, warm seed, target, and both selected residual digests.
It is written once with no-overwrite semantics.

The sole scientific result is:

```text
artifacts/math/G-0128/full_family_master_result_v2.json
```

It uses schema `max11-g0128-full-family-master-result-v2`. The solver,
manifest, cache, prior inputs, and future price receipt are rehashed before
publication. JSON is pre-serialized in memory, written to an exclusively
created same-directory temporary file, flushed and synced, and atomically
published by a no-overwrite hard link. Any failed validation or interrupted
trial leaves no final-path scientific artifact.

## Stop rule

This study stops after emitting one exact 380-row member or one exact frozen-
family nonmember. It does not run a global replay, alter the dictionary, claim
convergence from finite-row fitting, search for a preferred member, or begin
Lean. Those are separate studies whose protocols, if triggered, must be
committed before their corresponding evidence is inspected.
