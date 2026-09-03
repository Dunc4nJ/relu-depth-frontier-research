#!/usr/bin/env bash
set -euo pipefail

cd /workspace/relu
root=artifacts/math/n11-sparse-certificate
system=handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz
export PYTHONPATH=tools/exactlift:$root

python3 "$root/select_exact_support.py" \
  --matrix-dir "$root/n10-matrix" \
  --l1-report "$root/n10-l1.json" \
  --prime 1000003 \
  --output "$root/n10-l1-pivots.json" \
  --report "$root/n10-support-selection.json" \
  > "$root/n10-support-selection.stdout.json"

python3 tools/exactlift/support_lift.py \
  --pivot-report "$root/n10-l1-pivots.json" \
  --system "$system" \
  --output "$root/n10-exact-witness.json" \
  --report "$root/n10-exact-lift-report.json" \
  --upstream-output "$root/n10-upstream.json" \
  > "$root/n10-exact-lift.stdout.json"

python3 tools/exactlift/exactlift.py mutate-witness \
  --witness "$root/n10-exact-witness.json" \
  --output "$root/n10-mutated-witness.json" \
  --delta 1 \
  > "$root/n10-mutated-witness.stdout.json"
set +e
python3 tools/exactlift/exactlift.py verify \
  --system "$system" \
  --witness "$root/n10-mutated-witness.json" \
  --report "$root/n10-mutated-verification.json" \
  > "$root/n10-mutated-verification.stdout.json"
mutated_status=$?
set -e
if [[ $mutated_status -ne 1 ]]; then
  echo "negative control returned $mutated_status instead of expected exact FAIL exit 1" >&2
  exit 1
fi

sha256sum \
  "$root/n10-l1-pivots.json" \
  "$root/n10-support-selection.json" \
  "$root/n10-exact-witness.json" \
  "$root/n10-exact-lift-report.json" \
  "$root/n10-upstream.json" \
  "$root/n10-mutated-verification.json" \
  > "$root/n10-exact-result.sha256"
echo N10_EXACT_DONE
