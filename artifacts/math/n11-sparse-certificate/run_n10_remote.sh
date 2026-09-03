#!/usr/bin/env bash
set -euo pipefail

cd /workspace/relu
root=artifacts/math/n11-sparse-certificate
system=handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz

python3 "$root/build_saved_csc.py" \
  --system "$system" \
  --output-dir "$root/n10-matrix" \
  > "$root/n10-build.stdout.json"

python3 "$root/solve_l1.py" \
  --matrix-dir "$root/n10-matrix" \
  --output "$root/n10-l1.json" \
  --log "$root/n10-highs.log" \
  --threads 1 \
  --reweighted-rounds 4 \
  --feasibility-tolerance 1e-8 \
  --support-threshold 1e-12 \
  --reweight-epsilon 1e-9 \
  --reweight-cap 1e6 \
  > "$root/n10-solve.stdout.json"

sha256sum \
  "$root/n10-matrix/matrix.json" \
  "$root/n10-l1.json" \
  > "$root/n10-result.sha256"
echo N10_L1_DONE
