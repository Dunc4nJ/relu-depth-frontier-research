#!/usr/bin/env bash
set -euo pipefail

cd /workspace/relu
export OPENBLAS_NUM_THREADS=16
export RAYON_NUM_THREADS=16

run_dir=artifacts/math/n11-stageA-exact-lift/run3-sketch-minor
pivot_report=artifacts/math/n11-stageA/stageA-s5-beta-le1-plus5L-m64000-p1000003-s1-cuda.json
batch_dir=artifacts/math/n11-stageA-exact-lift/run1/batches
binary=tools/exactlift/lift_large_rs/target/release/max11-lift-large
problem="$run_dir/stageA_sketch_problem.eliftq02"
build_report="$run_dir/stageA_sketch_build_report.json"
solver_report="$run_dir/stageA_sketch_solver_report.json"
witness="$run_dir/stageA_sketch_exact_witness.json"
lift_report="$run_dir/stageA_sketch_exact_lift_report.json"
upstream="$run_dir/stageA_sketch_upstream.json"

mkdir -p "$run_dir"
date -u +%Y-%m-%dT%H:%M:%SZ
sha256sum "$pivot_report" "$binary"

"$binary" build-sketch-member \
  --pivot-report "$pivot_report" \
  --sketch-index 0 \
  --batch-dir "$batch_dir" \
  --output "$problem" \
  --report "$build_report" \
  >"$run_dir/build.stdout.json" \
  2>"$run_dir/build.stderr.log"

date -u +%Y-%m-%dT%H:%M:%SZ
sha256sum "$problem" "$build_report"

"$binary" solve \
  --input "$problem" \
  --prime 65521 \
  --lu-block 128 \
  --row-tile 256 \
  --threads 16 \
  --max-steps 8 \
  --reconstruct-every 1 \
  --candidate-support-limit 21222 \
  --crt-primes 65519,65497,65479,65449,65447,65437 \
  --output "$solver_report" \
  >"$run_dir/solve.stdout.json" \
  2>"$run_dir/solve.stderr.log"

python tools/exactlift/sketch_member_lift.py \
  --build-report "$build_report" \
  --solver-report "$solver_report" \
  --pivot-report "$pivot_report" \
  --witness "$witness" \
  --report "$lift_report" \
  >"$run_dir/finalize.stdout.json"

python tools/exactlift/universe_to_upstream.py \
  --universe artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz \
  --witness "$witness" \
  --output "$upstream" \
  >"$run_dir/upstream_translation_report.json"

date -u +%Y-%m-%dT%H:%M:%SZ
sha256sum "$build_report" "$solver_report" "$witness" "$lift_report" "$upstream" \
  "$run_dir/upstream_translation_report.json"
python3 - "$lift_report" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
keys = (
    "verdict",
    "recovered_support_numerator",
    "recovered_support_denominator",
    "coefficient_denominator_lcm",
    "coefficient_denominator_factorization",
    "real_rows_verified_numerator",
    "real_rows_verified_denominator",
    "linear_rows_verified_numerator",
    "linear_rows_verified_denominator",
    "union_hinge_rows_verified_numerator",
    "union_hinge_rows_verified_denominator",
    "combined_rows_verified_numerator",
    "combined_rows_verified_denominator",
    "witness_sha256",
)
print(json.dumps({key: report[key] for key in keys}, indent=2, sort_keys=True))
PY
