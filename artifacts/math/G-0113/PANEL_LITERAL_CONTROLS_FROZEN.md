# G-0113e frozen Python literal-control replay

Frozen before reading either all-record scan output.  Producer SHA-256:

```text
70103aac4e079ba1991edeb0b75e50366b5d0e277e78a8e2b7c9e4d0c45f1e3e  verify_panel_literal_controls.py
44821eb32bfd49b8a7480e6f6d3370808739e309148d1a59e56927c0547e6df2  ../G-0109/transport_prototype.py
093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8  panel_solver_input_v1.json
0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c  ../G-0111/dual_rows_v1.json
94d54b1a64340ff49d6bbdf35cc429e71a25628ba6764b16039d15c258176310  ../G-0116/cycle_cut_panel_benchmark_v1.json
```

The replay imports the frozen G-0109 `assignment_matrix` and
`literal_record_value` semantics.  It enumerates distinct formal-colour
assignments for all 301 rows and all eight G-0116 controls, checks each complete
301-entry little-endian `i128` vector hash, reconstructs every target entry and
its frozen little-endian `i64` hash, verifies branch-swap invariance, and
requires rejection of a common-padding mutant.  It does not read modular ranks
or all-record output.

Run from repository root:

```text
.venv/bin/python artifacts/math/G-0113/verify_panel_literal_controls.py \
  artifacts/math/G-0113/panel_literal_controls_v1.json
```

This is a semantic control only; it makes no all-record membership, global
identity, completeness, or MAX11 claim.
