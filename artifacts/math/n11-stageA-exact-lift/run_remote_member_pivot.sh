#!/usr/bin/env bash
set -euo pipefail

if (( $# < 1 || $# > 2 )); then
  echo "usage: $0 PIVOT_REPORT.json [RUN_DIR]" >&2
  exit 64
fi

repo_root=${MAX11_REPO_ROOT:-/workspace/relu}
cd "$repo_root"
if [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
fi

pivot_report=$1
pivot_stem=${pivot_report##*/}
pivot_stem=${pivot_stem%.json}
run_dir=${2:-artifacts/math/n11-stageA-exact-lift/member-$pivot_stem}
threads=${MAX11_THREADS:-16}
prime=${MAX11_PRIME:-65521}
max_steps=${MAX11_MAX_STEPS:-40000}
reconstruct_every=${MAX11_RECONSTRUCT_EVERY:-50}
batch_size=${MAX11_GATHER_BATCH_SIZE:-1024}
sketch_index=${MAX11_SKETCH_INDEX:-0}
colgen=${MAX11_COLGEN_BINARY:-tools/colgen/target/release/max11-colgen}
lift_binary=${MAX11_LIFT_BINARY:-artifacts/math/n11-stageA-exact-lift/max11-lift-large-a50338c3}

export OPENBLAS_NUM_THREADS=$threads
export OMP_NUM_THREADS=$threads
export RAYON_NUM_THREADS=$threads

[[ -f "$pivot_report" ]] || { echo "missing pivot report: $pivot_report" >&2; exit 66; }
[[ -x "$colgen" ]] || { echo "missing colgen binary: $colgen" >&2; exit 66; }
[[ -x "$lift_binary" ]] || { echo "missing lift binary: $lift_binary" >&2; exit 66; }
[[ ! -e "$run_dir" ]] || { echo "refusing to overwrite run directory: $run_dir" >&2; exit 73; }

universe=$(python3 - "$pivot_report" "$sketch_index" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
if report.get("schema") != "max11-streamrank-pivots-v1":
    raise SystemExit("unexpected pivot report schema")
sketch = report["sketches"][int(sys.argv[2])]
if sketch.get("verdict") != "MEMBER" or sketch.get("rank_a") != sketch.get("rank_augmented"):
    raise SystemExit("pivot report is not an equal-rank MEMBER result")
print(report["input"])
PY
)
[[ -f "$universe" ]] || { echo "missing source universe: $universe" >&2; exit 66; }

mkdir -p "$run_dir"
exec > >(tee -a "$run_dir/pipeline.log") 2>&1
echo "PIPELINE_START $(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'pivot_report=%s\nrun_dir=%s\nthreads=%s\nprime=%s\nmax_steps=%s\nreconstruct_every=%s\n' \
  "$pivot_report" "$run_dir" "$threads" "$prime" "$max_steps" "$reconstruct_every"
sha256sum "$pivot_report" "$universe" "$colgen" "$lift_binary"

echo "PIPELINE_PHASE gather-plan"
python3 tools/exactlift/prepare_pivot_batches.py \
  --pivot-report "$pivot_report" \
  --output-dir "$run_dir/gather" \
  --batch-size "$batch_size" \
  --sketch-index "$sketch_index" \
  > "$run_dir/gather-plan.stdout.json"

batch_dir="$run_dir/batches"
mkdir "$batch_dir"
echo "PIPELINE_PHASE gather-exact-columns"
while IFS=$'\t' read -r batch order_file include_five_l; do
  output=$(printf '%s/batch-%03d.mcolgen1' "$batch_dir" "$batch")
  extra=()
  if [[ "$include_five_l" == true ]]; then
    extra=(--include-five-l true)
  fi
  "$colgen" emit-universe \
    --universe "$universe" \
    --threads "$threads" \
    --output "$output" \
    --format binary \
    --order-file "$order_file" \
    "${extra[@]}"
  sha256sum "$output"
done < <(python3 - "$run_dir/gather/gather_plan.json" <<'PY'
import json
import sys

plan = json.load(open(sys.argv[1], encoding="utf-8"))
for batch in plan["batches"]:
    print(batch["batch"], batch["order_file"], str(batch["include_five_l"]).lower(), sep="\t")
PY
)
sha256sum "$batch_dir"/*.mcolgen1 > "$run_dir/exact_batches.sha256"

problem="$run_dir/member_sketch_problem.eliftq02"
build_report="$run_dir/member_sketch_build_report.json"
echo "PIPELINE_PHASE build-exact-sketch-minor"
"$lift_binary" build-sketch-member \
  --pivot-report "$pivot_report" \
  --sketch-index "$sketch_index" \
  --batch-dir "$batch_dir" \
  --output "$problem" \
  --report "$build_report" \
  > "$run_dir/build.stdout.json" \
  2> >(tee "$run_dir/build.stderr.log" >&2)
sha256sum "$problem" "$build_report"

solver_report="$run_dir/member_big_solver_report.json"
support_report="$run_dir/modular_support_p${prime}.json"
echo "PIPELINE_PHASE dense-lu-modular-support-and-dixon"
"$lift_binary" solve-big \
  --input "$problem" \
  --prime "$prime" \
  --lu-block 128 \
  --row-tile 256 \
  --threads "$threads" \
  --max-steps "$max_steps" \
  --reconstruct-every "$reconstruct_every" \
  --modular-support-output "$support_report" \
  --output "$solver_report" \
  > "$run_dir/solve.stdout.json" \
  2> >(tee "$run_dir/solve.stderr.log" >&2)

witness="$run_dir/member_exact_witness.json"
lift_report="$run_dir/member_exact_lift_report.json"
upstream="$run_dir/member_upstream.json"
echo "PIPELINE_PHASE finalize"
python3 tools/exactlift/sketch_member_lift.py \
  --build-report "$build_report" \
  --solver-report "$solver_report" \
  --pivot-report "$pivot_report" \
  --witness "$witness" \
  --report "$lift_report" \
  > "$run_dir/finalize.stdout.json"
python3 tools/exactlift/universe_to_upstream.py \
  --universe "$universe" \
  --witness "$witness" \
  --output "$upstream" \
  > "$run_dir/upstream_translation_report.json"

echo "PIPELINE_PHASE complete"
sha256sum "$support_report" "$solver_report" "$witness" "$lift_report" "$upstream" \
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
    "combined_rows_verified_numerator",
    "combined_rows_verified_denominator",
    "witness_sha256",
)
print(json.dumps({key: report[key] for key in keys}, indent=2, sort_keys=True))
PY
echo "PIPELINE_DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)"
