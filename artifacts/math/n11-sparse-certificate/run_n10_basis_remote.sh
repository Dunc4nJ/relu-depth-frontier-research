#!/usr/bin/env bash
set -euo pipefail

cd /workspace/relu
root=artifacts/math/n11-sparse-certificate

python3 "$root/subset_saved_row_basis.py" \
  --matrix-dir "$root/n10-matrix" \
  --basis artifacts/math/exact-witness-n9-n10/n10_basis_p1000003.json \
  --output-dir "$root/n10-basis-matrix" \
  > "$root/n10-basis-build.stdout.json"

python3 "$root/solve_l1.py" \
  --matrix-dir "$root/n10-basis-matrix" \
  --output "$root/n10-basis-l1.json" \
  --log "$root/n10-basis-highs.log" \
  --threads 1 \
  --reweighted-rounds 4 \
  --feasibility-tolerance 1e-8 \
  --support-threshold 1e-12 \
  --reweight-epsilon 1e-9 \
  --reweight-cap 1e6 \
  --initial-witness artifacts/math/exact-witness-n9-n10/recovered_n10_witness.json \
  > "$root/n10-basis-solve.stdout.json"

echo N10_BASIS_L1_DONE
