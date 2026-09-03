#!/usr/bin/env bash
set -euo pipefail

cd /workspace/relu
fixture_dir="artifacts/math/n12-stageA-exact-lift/preflight"
out_dir="artifacts/math/n12-stageA-exact-lift/preflight-a100-v1"
fixture="$fixture_dir/tiny_member_fixture_n12.json"
static_order="$fixture_dir/tiny_order_n12.json"
universe="artifacts/math/n12-universe/loopless_signed_degree5_universe_n12_v1.json.gz"
colgen="tools/colgen/target/release/max11-colgen"
lift="artifacts/math/n11-stageA-exact-lift/max11-lift-large-a50338c3"

test ! -e "$out_dir"
mkdir -p "$out_dir/batches" "$out_dir/mutant-batches"
date -u +%Y-%m-%dT%H:%M:%SZ > "$out_dir/start_utc.txt"
{
  nproc
  free -h
  nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader,nounits
} > "$out_dir/environment.txt"
sha256sum "$fixture" "$static_order" "$universe" "$colgen" "$lift" \
  tools/exactlift/prepare_pivot_batches.py \
  artifacts/math/n11-stageA-exact-lift/run_remote_member_pivot.sh \
  > "$out_dir/inputs.sha256"

python3 tools/exactlift/prepare_pivot_batches.py \
  --pivot-report "$fixture" --output-dir "$out_dir/gather" --batch-size 1 \
  > "$out_dir/gather-plan.stdout.json"
cmp "$static_order" "$out_dir/gather/orders/order-000.json"

"$colgen" emit-universe \
  --universe "$universe" --threads 2 --format binary \
  --order-file "$out_dir/gather/orders/order-000.json" \
  --output "$out_dir/batches/batch-000.mcolgen1" \
  > "$out_dir/colgen.stdout.log" 2> "$out_dir/colgen.stderr.log"
"$colgen" emit-universe \
  --universe "$universe" --threads 2 --format binary \
  --order-file "$static_order" \
  --output "$out_dir/direct-tiny-n12.mcolgen1" \
  > "$out_dir/colgen-direct.stdout.log" 2> "$out_dir/colgen-direct.stderr.log"
cmp "$out_dir/batches/batch-000.mcolgen1" "$out_dir/direct-tiny-n12.mcolgen1"

"$lift" build-sketch-member \
  --pivot-report "$fixture" --sketch-index 0 \
  --batch-dir "$out_dir/batches" \
  --output "$out_dir/tiny-n12.eliftq02" \
  --report "$out_dir/tiny-n12-build.json" \
  > "$out_dir/build.stdout.json" 2> "$out_dir/build.stderr.log"

cp "$out_dir/batches/batch-000.mcolgen1" \
  "$out_dir/mutant-batches/batch-000.mcolgen1"
python3 - "$out_dir/mutant-batches/batch-000.mcolgen1" <<'PY'
import struct
import sys

path = sys.argv[1]
with open(path, "r+b") as handle:
    header = handle.read(28)
    magic, n, branch_edges, modulus, count = struct.unpack("<8sHHQQ", header)
    assert (magic, n, branch_edges, modulus, count) == (b"MCOLGEN1", 12, 5, 0, 1)
    handle.seek(8)
    handle.write(struct.pack("<H", 11))
PY

set +e
"$lift" build-sketch-member \
  --pivot-report "$fixture" --sketch-index 0 \
  --batch-dir "$out_dir/mutant-batches" \
  --output "$out_dir/mutant.eliftq02" \
  --report "$out_dir/mutant-build.json" \
  > "$out_dir/mutant.stdout.log" 2> "$out_dir/mutant.stderr.log"
mutant_status=$?
set -e
printf '%s\n' "$mutant_status" > "$out_dir/mutant.exit_code"
if (( mutant_status == 0 )); then
  echo "dimension mutant was accepted" >&2
  exit 1
fi
grep -q "incompatible dimensions/modulus" "$out_dir/mutant.stderr.log"

date -u +%Y-%m-%dT%H:%M:%SZ > "$out_dir/end_utc.txt"
sha256sum "$out_dir/batches/batch-000.mcolgen1" \
  "$out_dir/direct-tiny-n12.mcolgen1" \
  "$out_dir/mutant-batches/batch-000.mcolgen1" \
  "$out_dir/tiny-n12.eliftq02" "$out_dir/tiny-n12-build.json" \
  > "$out_dir/outputs.sha256"
echo N12_EXACT_LIFT_PREFLIGHT_COMPLETE
