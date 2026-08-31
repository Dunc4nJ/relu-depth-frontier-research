# G-0113e frozen 301-row all-record scan

> **Superseded / invalid execution source.**  Clean-room review found the
> boundary-agreement mismatch documented in
> `PANEL_SOLVER_ABORTED_RUN_2026-08-31.md`.  The source hash below was stopped
> before any checkpoint or output and must not be used for a scientific claim.

Frozen after the G-0116 accelerator passed its official exactness/performance
gate and before the 163,740-record scan was started.

## Source and transitive bindings

```text
89ee08b1b6def2a07b351e6f5a7ba6a8d8819f94d8127fbd9169beb9fdf7e8f8  src/main.rs
1c35b9457dc2f7376b2aedfdc158ceef4c6a3368201d5bdb0b983e4f865e5e3c  src/lib.rs
006968bbf4f428e4fa492d06b61b43d64b25e5febcc0751ec81c07d90a399994  src/rank.rs
b89e54aa1bcd20118083b52141851d7932949368724d81d561d5cba4a2234eba  Cargo.toml
9b894dc043760a1f9bf8e27a598a0e72169302638ae08f4d992e0a31ad130d14  Cargo.lock
875b0046e24f32d9649fe0d9c5295dfbd75678fea46df96f6d9f287c6a987bfd  ../G-0116/src/main.rs
94d54b1a64340ff49d6bbdf35cc429e71a25628ba6764b16039d15c258176310  ../G-0116/cycle_cut_panel_benchmark_v1.json
093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8  panel_solver_input_v1.json
0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c  ../G-0111/dual_rows_v1.json
```

The scanner includes the frozen G-0116 source as a Rust module, verifies its
source and official report hashes at runtime, and calls its exact
`signed_edges`, `cycle_cut_histogram`, and `panel_vector` functions.  The outer
record order is sequential.  Only the evaluator's fixed-colour assignments use
Rayon, through an explicit 12-thread global pool.

For every record, the scanner hashes all 301 little-endian `i128` entries,
hashes the individual vector, feeds it independently to both frozen-prime
left-annihilator oracles, and discards it unless it grows either basis or is an
official exact-vector control.  Rank arithmetic may stop naturally at nullity
zero, but evaluation and both ordered hash streams continue through record
163,739.  Progress is emitted every 5,000 records and at the slice boundary.

## Pre-run controls and resource observation

- `cargo test --release`: 2 passed, 0 failed;
- `cargo clippy --release --all-targets -- -D warnings`: passed;
- G-0116 official gate: exact histogram/exhaustive agreement, exact all-301
  vector agreement, exact assignment census, branch-swap preservation, sign
  mutant rejection, and frozen high-active median speedup `22.33x`;
- separate 12-thread resource rerun: every exact control hash still matched,
  maximum RSS `64,840 KiB`; its timing-only high-active median was a noisy
  `8.265x`, below the official performance threshold.  This observation is
  recorded as timing variability and does not replace the frozen official
  semantic/performance gate.

## Official command

Run from repository root under `/usr/bin/time -v`:

```text
artifacts/math/G-0113/target/release/g0113-panel-solver \
  artifacts/math/G-0113/panel_solver_input_v1.json \
  artifacts/math/G-0111/dual_rows_v1.json \
  artifacts/math/G-0116/cycle_cut_panel_benchmark_v1.json \
  artifacts/math/G-0113/panel_scan_v1.json \
  artifacts/math/G-0113/panel_retained_columns_v1.json
```

The output remains a finite 301-row gate.  It cannot by itself establish a
global CPWL identity, a characteristic-zero separator, a completeness theorem,
or MAX11.
