#!/usr/bin/env bash
set -euo pipefail

# Durable coordinator: launch the two p=1,000,033 arms only after both
# p=1,000,003 supervisor processes have exited and their full reports pass a
# minimal frozen gate. Launch this coordinator itself under nohup.
cd /workspace/relu
out_dir="artifacts/math/n12-stageA"

p1_labels=(
  n12-stageA-m128000-p1000003-s2026090201-cuda
  n12-stageA-m128000-p1000003-s2026090202-cuda
)

while true; do
  active=0
  for label in "${p1_labels[@]}"; do
    pid_file="$out_dir/$label.supervisor.pid"
    test -f "$pid_file"
    pid="$(<"$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      active=1
    fi
  done
  if (( active == 0 )); then
    break
  fi
  date -u +%Y-%m-%dT%H:%M:%SZ
  echo "WAITING_FOR_WAVE1"
  sleep 60
done

python3 - "$out_dir/${p1_labels[0]}.json" "$out_dir/${p1_labels[1]}.json" <<'PY'
import json
import sys

for path in sys.argv[1:]:
    with open(path, encoding="utf-8") as handle:
        report = json.load(handle)
    assert report["schema"] == "max11-streamrank-pivots-v1"
    assert report["result"] == "OBSERVATION"
    assert report["source_column_count"] == 148_629
    assert report["source_columns_denominator"] == 148_629
    assert report["progress"][-1]["source_columns_processed"] == 148_629
    assert len(report["sketches"]) == 1
    sketch = report["sketches"][0]
    assert sketch["rank_a"] <= 100_000
    assert sketch["saturated"] is False
    assert sketch["verdict"] in {"MEMBER", "NON_MEMBER"}
PY

for seed in 2026090201 2026090202; do
  label="n12-stageA-m128000-p1000033-s${seed}-cuda"
  supervisor_log="$out_dir/$label.supervisor.log"
  pid_file="$out_dir/$label.supervisor.pid"
  test ! -e "$supervisor_log"
  test ! -e "$pid_file"
  nohup "$out_dir/run_remote_arm.sh" 1000033 "$seed" "$label" \
    >"$supervisor_log" 2>&1 < /dev/null &
  supervisor_pid=$!
  printf '%s\n' "$supervisor_pid" >"$pid_file"
  echo "LAUNCHED label=$label supervisor_pid=$supervisor_pid"
done
date -u +%Y-%m-%dT%H:%M:%SZ
echo WAVE2_LAUNCHED
