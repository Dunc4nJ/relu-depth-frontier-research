# G-0113e panel-solver preparation freeze

Frozen before writing the evaluator input or accessing a fresh G-0113 panel
column value.

- preregistration SHA-256:
  `f2536d5d311570f5e676647bf5707e23bc00964547c80e2310f8f475e4c463b9`
- preparation producer SHA-256:
  `b2fba700e1fd8055eae91204b59ff529103c138522ee14edb62fc436c5a1ec4a`

Invocation from the repository root:

```bash
source scripts/activate-toolchain.sh
/usr/bin/time -v python artifacts/math/G-0113/prepare_panel_solver.py \
  --input artifacts/math/G-0113/panel_solver_input_v1.json \
  --receipt artifacts/math/G-0113/panel_solver_preparation_v1.json
```
