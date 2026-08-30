# G-0078 — adaptive sparse exact left-dual lift

G-0077's committed modular receipt has a canonical dual supported on only 229
of 6,876 basis rows.  G-0078 freezes those support positions, selects a
canonical 229-column nonsingular subsystem, solves the resulting transpose
system exactly over Q, and replays the serialized integer dual against all
8,107 frozen-family columns and the target.

The modular support is only a search heuristic.  Exact success is definitive
for the frozen finite family because it produces a rational left dual.  Exact
failure is inconclusive because a coefficient that is zero modulo 1,000,003
may be nonzero over Q; failure returns to the full G-0077 lift.

Registered order:

```text
.venv/bin/python artifacts/math/G-0078/sparse_exact_left_dual.py preflight \
  --output artifacts/math/G-0078/sparse_exact_preflight_v1.json.gz

.venv/bin/python artifacts/math/G-0078/sparse_exact_left_dual.py exact \
  --output artifacts/math/G-0078/sparse_exact_left_dual_v1.json.gz
```

The producer, preflight, and EXP preregistration must be committed and pushed
before the exact command.  The decisive acceptance path is the same
production verifier frozen in G-0077: it recomputes primitive augmented-row
gcds from the immutable full-matrix snapshot, checks every A column with
exact integer arithmetic, requires a nonzero exact target pairing, and
rejects a one-unit serialized-certificate mutation.
