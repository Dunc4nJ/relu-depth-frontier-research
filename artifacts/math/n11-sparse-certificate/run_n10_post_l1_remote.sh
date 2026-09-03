#!/usr/bin/env bash
set -euo pipefail

cd /workspace/relu
root=artifacts/math/n11-sparse-certificate
lp_pid=$(cat "$root/n10-pipeline.pid")
while kill -0 "$lp_pid" 2>/dev/null; do
  sleep 30
done
test -f "$root/n10-l1.json"
bash "$root/run_n10_exact_remote.sh"
