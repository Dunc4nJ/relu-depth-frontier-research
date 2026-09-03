#!/usr/bin/env bash
set -uo pipefail

if (( $# != 2 )); then
  echo "usage: $0 PIVOT_REPORT.json RUN_DIR" >&2
  exit 64
fi

cd /workspace/relu
pivot_report=$1
run_dir=$2
threads=${HHS_THREADS:-16}
wrapper_prefix="${run_dir}.wrapper"

[[ -f "$pivot_report" ]] || { echo "missing pivot report: $pivot_report" >&2; exit 66; }
[[ ! -e "$run_dir" ]] || { echo "refusing to overwrite run directory: $run_dir" >&2; exit 73; }
[[ ! -e "${wrapper_prefix}.exit_code" ]] || {
  echo "refusing to overwrite wrapper receipt: ${wrapper_prefix}.exit_code" >&2
  exit 73
}

date -u +%Y-%m-%dT%H:%M:%SZ > "${wrapper_prefix}.start_utc.txt"
set +e
MAX11_REPO_ROOT=/workspace/relu \
MAX11_THREADS="$threads" \
MAX11_PRIME=65521 \
MAX11_MAX_STEPS=40000 \
MAX11_RECONSTRUCT_EVERY=50 \
MAX11_GATHER_BATCH_SIZE=1024 \
bash artifacts/math/n11-stageA-exact-lift/run_remote_member_pivot.sh \
  "$pivot_report" "$run_dir"
exit_code=$?
set -e
printf '%s\n' "$exit_code" > "${wrapper_prefix}.exit_code"
date -u +%Y-%m-%dT%H:%M:%SZ > "${wrapper_prefix}.end_utc.txt"
exit "$exit_code"
