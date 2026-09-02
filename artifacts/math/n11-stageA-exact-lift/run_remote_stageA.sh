#!/usr/bin/env bash
set -euo pipefail

cd /workspace/relu
export OPENBLAS_NUM_THREADS=16
export OMP_NUM_THREADS=16
export RAYON_NUM_THREADS=16

run_dir=artifacts/math/n11-stageA-exact-lift/run1
universe=artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz
pivot_report=artifacts/math/n11-stageA/stageA-s5-beta-le1-plus5L-m64000-p1000003-s1-cuda.json
colgen=tools/colgen/target/release/max11-colgen
lift_binary=tools/exactlift/lift_large_rs/target/release/max11-lift-large

mkdir -p "$run_dir/batches"
date --iso-8601=seconds
echo "GATHER_START rank=21222 batches=21 threads=16"
for order in "$run_dir"/orders/order-*.json; do
  base=${order##*/}
  stem=${base%.json}
  output="$run_dir/batches/${stem/order/batch}.mcolgen1"
  extra=()
  if [[ "$base" == order-020.json ]]; then
    extra=(--include-five-l true)
  fi
  "$colgen" emit-universe \
    --universe "$universe" \
    --threads 16 \
    --output "$output" \
    --format binary \
    --order-file "$order" \
    "${extra[@]}"
  sha256sum "$output"
done
sha256sum "$run_dir"/batches/*.mcolgen1 > "$run_dir/exact_batches.sha256"
date --iso-8601=seconds
echo "GATHER_DONE"

batch_args=()
for batch in "$run_dir"/batches/batch-*.mcolgen1; do
  batch_args+=(--batch "$batch")
done
echo "LIFT_START rank=21222 threads=16"
python3 tools/exactlift/lift_large.py \
  --pivot-report "$pivot_report" \
  "${batch_args[@]}" \
  --binary "$lift_binary" \
  --prime 65521 \
  --lu-block 128 \
  --row-tile 256 \
  --threads 16 \
  --max-steps 6 \
  --reconstruct-every 1 \
  --candidate-support-limit 21222 \
  --crt-primes 65519,65497,65479,65449,65447,65437 \
  --precondition-seed 20260902 \
  --keep-problem "$run_dir/stageA_problem.eliftq01" \
  --selected-rows-output "$run_dir/stageA_selected_rows.json" \
  --output "$run_dir/stageA_exact_witness.json" \
  --report "$run_dir/stageA_exact_lift_report.json"
date --iso-8601=seconds
echo "LIFT_DONE"
