# G-0116 frozen execution

Frozen after the implementation passed the preregistered semantic controls and
performance gate on a temporary output, and before the retained official run.

```text
875b0046e24f32d9649fe0d9c5295dfbd75678fea46df96f6d9f287c6a987bfd  src/main.rs
059f85043b4ba0d0572f1f500508470a6962a905539f43a1c2d3efd5aad2fa6b  Cargo.toml
3c84c4d2a6e38b015f112f37a3b64a3bd340c3ba4047ba94ca3d6b618b214900  Cargo.lock
093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8  ../G-0113/panel_solver_input_v1.json
0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c  ../G-0111/dual_rows_v1.json
```

Run from repository root:

```bash
cargo test --release --manifest-path artifacts/math/G-0116/Cargo.toml
artifacts/math/G-0116/target/release/g0116-cycle-cut-panel-benchmark \
  artifacts/math/G-0113/panel_solver_input_v1.json \
  artifacts/math/G-0111/dual_rows_v1.json \
  artifacts/math/G-0116/cycle_cut_panel_benchmark_v1.json
```
