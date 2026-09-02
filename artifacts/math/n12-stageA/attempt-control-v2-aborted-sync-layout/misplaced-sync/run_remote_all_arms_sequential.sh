#!/usr/bin/env bash
set -euo pipefail

# Launch this coordinator once with nohup from /workspace/relu. Each arm is
# awaited before the next starts, so at most one reducer owns the H100.
cd /workspace/relu
out_dir="artifacts/math/n12-stageA"
runner="$out_dir/run_remote_arm.sh"
mkdir -p "$out_dir"

for prime in 1000003 1000033; do
  for seed in 2026090201 2026090202; do
    label="n12-stageA-m128000-p${prime}-s${seed}-cuda"
    supervisor="$out_dir/$label.supervisor.log"
    if [[ -e "$supervisor" ]]; then
      echo "REFUSAL: supervisor path exists: $supervisor" >&2
      exit 17
    fi
    date -u +%Y-%m-%dT%H:%M:%SZ
    echo "ARM_START $label"
    "$runner" "$prime" "$seed" "$label" >"$supervisor" 2>&1
    python3 - "$out_dir/$label.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
item = report["sketches"][0]
print(
    "ARM_COMPLETE"
    f" rank={item['rank_a']}"
    f" augmented={item['rank_augmented']}"
    f" verdict={item['verdict']}"
    f" pivot_sha256={item['pivot_columns_u64_le_sha256']}"
)
PY
  done
done

date -u +%Y-%m-%dT%H:%M:%SZ
echo ALL_ARMS_COMPLETE
