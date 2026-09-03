#!/usr/bin/env bash
set -euo pipefail

cd /workspace/relu
root=artifacts/math/n11-sparse-certificate
builder_pid=$(cat "$root/n11-build.pid")
while kill -0 "$builder_pid" 2>/dev/null; do
  sleep 30
done
test -f "$root/n11-f2-sketch-matrix/matrix.json"

python3 "$root/compare_pivot_sketch.py" \
  --matrix-dir "$root/n11-f2-sketch-matrix" \
  --prior-problem artifacts/math/n11-stageA-exact-lift/member-F2-forestpair-m64000-p1000003-s1-cuda/member_sketch_problem.eliftq02 \
  --output "$root/n11-pivot-sketch-parity.json" \
  > "$root/n11-pivot-sketch-parity.stdout.json"

bash "$root/run_n11_l1_remote.sh"
