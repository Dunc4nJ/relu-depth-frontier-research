#!/usr/bin/env bash
set -euo pipefail

# Launch this whole script with nohup from /workspace/relu. It builds one
# CUDA-feature binary, then exercises both its CPU and CUDA backends.
cd /workspace/relu
export PATH="/root/.cargo/bin:$PATH"
export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
export CARGO_BUILD_JOBS=60

out_dir="artifacts/math/n12-stageA/controls"
binary="tools/streamrank/target/release/max11-streamrank"
n9="handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz"
n10="handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz"
mkdir -p "$out_dir"

if find "$out_dir" -maxdepth 1 -name '*.json' -print -quit | grep -q .; then
  echo "REFUSAL: control JSON already exists in $out_dir" >&2
  exit 17
fi

date -u +%Y-%m-%dT%H:%M:%SZ
nvidia-smi
cargo --version
rustc --version
nvcc --version

printf '%s  %s\n' \
  729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991 "$n9" \
  bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18 "$n10" \
  | sha256sum -c -

printf '%s  %s\n' \
  c40f96776f86f4a18949914204a37392453f12ea3b1a5a6138853ee767ea7603 tools/streamrank/src/main.rs \
  7d0139fa7c1b6c26c65884b27f3687e0242a08f39ce3d154767b266e47c3d387 tools/streamrank/src/lib.rs \
  3bcea1727b56d0ca4ad502bf9f40af90204044f42a48dbd0f5c3d42651b3a6b6 tools/streamrank/src/cuda.rs \
  22a311c57bc6fb59acce18011fcb104e4a793c05f490b7967c199fa43ce80341 tools/streamrank/src/cuda_backend.cu \
  5ccb78c208ca1778d81beaf8b5e18a6fd91c62fb5ec14c2a25efdeb2102f5880 tools/streamrank/build.rs \
  e6065d00916457a90b8549a2e7afda8b5364af80e4e9f52213263cbac9a46c80 tools/streamrank/Cargo.toml \
  81f6618d57c09fb1694f0b97a4e493853193f48249ddde5a7b612e795a850eb5 tools/colgen/src/lib.rs \
  c7a40f0381e2085888470a101e74fdfabcf4cf0e113c811729214edb4a9cce6b tools/colgen/src/main.rs \
  | sha256sum -c -

cargo test --release --features cuda --manifest-path tools/streamrank/Cargo.toml
cargo build --release --features cuda --manifest-path tools/streamrank/Cargo.toml
sha256sum "$binary" | tee "$out_dir/binary.sha256"

run_control() {
  local backend="$1"
  local system="$2"
  local prime="$3"
  local output="$out_dir/${backend}-${system}-p${prime}.json"
  local input n filter buckets columns rank aug verdict batch
  if [[ "$system" == n10 ]]; then
    input="$n10"; n=10; filter=all; buckets=6498; columns=12248
    rank=2166; aug=2166; verdict=MEMBER; batch=1024
  else
    input="$n9"; n=9; filter=union-trees; buckets=1080; columns=739
    rank=360; aug=361; verdict=NON_MEMBER; batch=256
  fi
  "$binary" run-saved \
    --backend "$backend" \
    --input "$input" \
    --n "$n" --branch-edges 4 --filter "$filter" \
    --modulus "$prime" --buckets "$buckets" \
    --seeds 2026090201,2026090202 \
    --batch-size "$batch" --gemm-block 1024 --rank-panel 64 --threads 60 \
    --expected-columns "$columns" --expected-rank "$rank" \
    --expected-aug-rank "$aug" --expected-verdict "$verdict" \
    --output "$output" \
    >"$output.stdout.log" 2>"$output.stderr.log"
  sha256sum "$output"
}

for backend in cpu cuda; do
  for prime in 1000003 1000033; do
    run_control "$backend" n10 "$prime"
    run_control "$backend" n9 "$prime"
  done
done

# Potency control: a deliberately wrong expected rank must write CONTROL_FAIL
# and return nonzero. Accepting it is fatal to this harness.
mutant="$out_dir/cuda-n9-p1000003-mutant-expected-rank359.json"
set +e
"$binary" run-saved \
  --backend cuda --input "$n9" --n 9 --branch-edges 4 \
  --filter union-trees --modulus 1000003 --buckets 1080 \
  --seeds 2026090201 --batch-size 256 --gemm-block 1024 \
  --rank-panel 64 --threads 60 --expected-columns 739 \
  --expected-rank 359 --expected-aug-rank 361 \
  --expected-verdict NON_MEMBER --output "$mutant" \
  >"$mutant.stdout.log" 2>"$mutant.stderr.log"
mutant_status=$?
set -e
if [[ "$mutant_status" -eq 0 ]]; then
  echo "MUTANT_ACCEPTED: wrong n=9 expected rank returned zero" >&2
  exit 18
fi
python3 - "$mutant" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
assert report["result"] == "CONTROL_FAIL"
assert report["expected"]["exact_match"] is False
assert [s["rank_a"] for s in report["sketches"]] == [360]
PY

date -u +%Y-%m-%dT%H:%M:%SZ
sha256sum "$out_dir"/*.json
echo CONTROL_SUITE_COMPLETE

