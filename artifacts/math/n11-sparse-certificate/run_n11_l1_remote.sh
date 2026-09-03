#!/usr/bin/env bash
set -euo pipefail

cd /workspace/relu
root=artifacts/math/n11-sparse-certificate

python3 "$root/solve_l1.py" \
  --matrix-dir "$root/n11-f2-sketch-matrix" \
  --output "$root/n11-l1.json" \
  --log "$root/n11-highs.log" \
  --threads 1 \
  --reweighted-rounds 4 \
  --feasibility-tolerance 1e-8 \
  --support-threshold 1e-12 \
  --reweight-epsilon 1e-9 \
  --reweight-cap 1e6 \
  > "$root/n11-solve.stdout.json"

sha256sum \
  "$root/n11-f2-sketch-matrix/matrix.json" \
  "$root/n11-l1.json" \
  > "$root/n11-l1-result.sha256"
echo N11_L1_DONE
