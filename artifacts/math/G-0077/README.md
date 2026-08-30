# G-0077 — exact left-dual lift

G-0076 found that the target adds one modular rank on all 16,738 frozen
rows.  G-0077 is the shortest theorem-bearing discriminator: it converts the
canonical modular separation into a rational left dual and then ignores the
modular evidence during the decisive check.

An accepted certificate consists of primitive selected augmented rows,
integer numerator weights `U`, and a positive denominator weight `d`.  It
must satisfy, using exact integer arithmetic,

```text
U^T A'_R + d A'_s = 0   on all 8,107 frozen-family columns,
U^T b'_R + d b'_s != 0.
```

Here each primed row is the corresponding raw evaluation row divided by its
recorded exact positive row gcd.  This is a rational left dual of the raw
system.  A successful replay proves nonmembership only for the frozen
8,107-column construction family on the bound finite system.  It does not
prove an unrestricted two-hidden-layer ReLU lower bound.

The modular basis, modular dual, support size, and resource benchmarks are
discovery artifacts.  They have no characteristic-zero evidential force.

## Registered execution order

Use the pinned subject environment:

```text
.venv/bin/python artifacts/math/G-0077/exact_left_dual_lift.py preflight \
  --output artifacts/math/G-0077/exact_left_dual_preflight_v1.json.gz

.venv/bin/python artifacts/math/G-0077/exact_left_dual_lift.py modular \
  --preflight artifacts/math/G-0077/exact_left_dual_preflight_v1.json.gz \
  --output artifacts/math/G-0077/canonical_modular_dual_v1.json.gz

.venv/bin/python artifacts/math/G-0077/exact_left_dual_lift.py benchmark \
  --modular-report artifacts/math/G-0077/canonical_modular_dual_v1.json.gz \
  --size 4096 \
  --output artifacts/math/G-0077/dixon_benchmark_4096_v1.json.gz

.venv/bin/python artifacts/math/G-0077/exact_left_dual_lift.py exact \
  --modular-report artifacts/math/G-0077/canonical_modular_dual_v1.json.gz \
  --output artifacts/math/G-0077/exact_left_dual_v1.json.gz
```

The producer and preflight must be committed before `modular`; the modular
receipt and benchmark must be committed before `exact`.  Record their
`sha256sum` values in the experiment ledger.  Each long-running command
captures its script, preflight, report, upstream subject, and environment
hashes at entry and refuses to write if any changes before completion.

Run the full solve only if the aligned 4,096-square benchmark is below 20
minutes, peak RSS is below 12 GiB, `MemAvailable` remains at least 24 GiB,
and a conservative full extrapolation is below three hours and 24 GiB.  A
benchmark failure or resource-gate failure leaves exact status unresolved.

`artifacts/math/G-0076/cache/full-N.npy` is ignored by Git and is never an
evidentiary artifact by itself.  G-0077 loads it into an owned immutable
snapshot and requires raw SHA-256
`41498698f122d01b624cf83e48f7e36c0b56082a4062654e36a55a7c34c49095`.
If it is absent, regenerate it with the frozen G-0076 producer; do not
substitute a partial matrix.  Exact acceptance still depends on replaying the
serialized dual against all 8,107 columns of that hash-bound snapshot.

Any nonzero exact column residual, zero exact target pairing, divisor drift,
input drift, singular exact solve, or serialized-certificate mutant that
passes verification blocks promotion.  Such a run is evidence that the
registered modular lift failed, not evidence of target membership.
