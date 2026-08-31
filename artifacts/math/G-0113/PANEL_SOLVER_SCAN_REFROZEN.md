# G-0113e corrected and re-frozen 301-row all-record scan

Re-frozen after clean-room review of the first source, before restarting the
163,740-record scan from record zero.

## Correction

The superseded source checked p1/p2 agreement only after the union.  The
corrected source records agreement separately at the DISJOINT and union
boundaries and defines each global agreement flag as the conjunction of its
two boundary-specific flags.  Thus a stage disagreement cannot be hidden by a
later agreement.  The result is `MODULAR_DISAGREEMENT` if either global
conjunction fails.

The interrupted invocation and absence of partial outputs are recorded in
`PANEL_SOLVER_ABORTED_RUN_2026-08-31.md`, SHA-256
`227d11cc78f8c981a76f9479396128df0fca4c899f212868db14d4765737c4c1`.

## Corrected frozen bindings

```text
8be4583119a49d63ef41ab4c86d2f9eb1ee473c99578047c8c62bdcaa01ed47f  src/main.rs
1c35b9457dc2f7376b2aedfdc158ceef4c6a3368201d5bdb0b983e4f865e5e3c  src/lib.rs
006968bbf4f428e4fa492d06b61b43d64b25e5febcc0751ec81c07d90a399994  src/rank.rs
b89e54aa1bcd20118083b52141851d7932949368724d81d561d5cba4a2234eba  Cargo.toml
9b894dc043760a1f9bf8e27a598a0e72169302638ae08f4d992e0a31ad130d14  Cargo.lock
875b0046e24f32d9649fe0d9c5295dfbd75678fea46df96f6d9f287c6a987bfd  ../G-0116/src/main.rs
94d54b1a64340ff49d6bbdf35cc429e71a25628ba6764b16039d15c258176310  ../G-0116/cycle_cut_panel_benchmark_v1.json
093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8  panel_solver_input_v1.json
0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c  ../G-0111/dual_rows_v1.json
```

## Corrected controls

- `cargo test --release`: 4 passed, 0 failed, including the planted
  stage-disagree/final-agree case and the both-boundaries-agree case;
- `cargo clippy --release --all-targets -- -D warnings`: passed;
- all prior exact evaluator, vector-hash, 12-thread, scan-order, progress,
  output-exclusivity, and finite-panel claim-boundary controls remain intact.

Restart with the same official command recorded in the superseded freeze note.
The corrected run must begin from record zero and create both outputs only at
the end of a complete scan.
