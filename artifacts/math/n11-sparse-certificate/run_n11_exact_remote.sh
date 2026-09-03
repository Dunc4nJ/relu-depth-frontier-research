#!/usr/bin/env bash
set -euo pipefail

cd /workspace/relu
root=artifacts/math/n11-sparse-certificate
base=artifacts/math/n11-stageA/sub/F2-forestpair-m64000-p1000003-s1-cuda.json
export PYTHONPATH=tools/exactlift:$root

python3 "$root/select_exact_support.py" \
  --matrix-dir "$root/n11-f2-sketch-matrix" \
  --l1-report "$root/n11-l1.json" \
  --prime 1000003 \
  --base-pivot-report "$base" \
  --output "$root/n11-l1-pivots.json" \
  --report "$root/n11-support-selection.json" \
  > "$root/n11-support-selection.stdout.json"

MAX11_THREADS=16 \
MAX11_PRIME=65521 \
MAX11_MAX_STEPS=4000 \
MAX11_RECONSTRUCT_EVERY=50 \
  bash artifacts/math/n11-stageA-exact-lift/run_remote_member_pivot.sh \
    "$root/n11-l1-pivots.json" \
    "$root/n11-exact-lift"

sha256sum \
  "$root/n11-l1-pivots.json" \
  "$root/n11-support-selection.json" \
  "$root/n11-exact-lift/member_exact_witness.json" \
  "$root/n11-exact-lift/member_exact_lift_report.json" \
  "$root/n11-exact-lift/member_upstream.json" \
  > "$root/n11-exact-result.sha256"
echo N11_EXACT_DONE
