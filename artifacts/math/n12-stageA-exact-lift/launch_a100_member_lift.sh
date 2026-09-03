#!/usr/bin/env bash
set -euo pipefail

if (( $# != 1 )); then
  echo "usage: RAM_AGREEMENT_CONFIRMED=1 $0 PIVOT_REPORT.json" >&2
  exit 64
fi
if [[ ${RAM_AGREEMENT_CONFIRMED:-0} != 1 ]]; then
  echo "refusing launch without RAM_AGREEMENT_CONFIRMED=1" >&2
  exit 77
fi

cd /data/projects/relu-depth-frontier-research
pivot_report=$1
remote="root@ssh5.vast.ai"
port=29562
remote_root=/workspace/relu
stage_dir=artifacts/math/n12-stageA
lift_dir=artifacts/math/n12-stageA-exact-lift
universe=artifacts/math/n12-universe/loopless_signed_degree5_universe_n12_v1.json.gz
colgen=tools/colgen/target/release/max11-colgen
lift_binary=artifacts/math/n11-stageA-exact-lift/max11-lift-large-a50338c3
runner=artifacts/math/n11-stageA-exact-lift/run_remote_member_pivot.sh
wrapper=$lift_dir/run_a100_triggered_member.sh
helper=tools/exactlift/prepare_pivot_batches.py
min_available_bytes=${HHS_MIN_AVAILABLE_BYTES:-68719476736}

read -r prime seed rank_a rank_augmented verdict input_sha pivot_sha <<<"$(
  python3 - "$pivot_report" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
if report.get("schema") != "max11-streamrank-pivots-v1":
    raise SystemExit("unexpected pivot-report schema")
if report.get("n") != 12 or report.get("branch_edge_occurrences") != 5:
    raise SystemExit("pivot report is not the n=12, k=5 experiment")
sketches = report.get("sketches", [])
if len(sketches) != 1:
    raise SystemExit("expected exactly one preregistered sketch")
sketch = sketches[0]
if sketch.get("verdict") != "MEMBER" or sketch.get("rank_a") != sketch.get("rank_augmented"):
    raise SystemExit("pivot report is not an equal-rank MEMBER result")
carrier = report.get("five_l_carrier", {})
if carrier.get("source_index") != 787523:
    raise SystemExit("unexpected n=12 5L carrier index")
print(
    report["modulus"], sketch["sketch"]["seed"], sketch["rank_a"],
    sketch["rank_augmented"], sketch["verdict"], report["input_sha256"],
    sketch["pivot_columns_u64_le_sha256"],
)
PY
)"

expected_report="$stage_dir/n12-stageA-m128000-p${prime}-s${seed}-cuda.json"
[[ "$pivot_report" == "$expected_report" ]] || {
  echo "pivot path does not name a preregistered arm: $pivot_report" >&2
  exit 65
}
[[ "$input_sha" == f98352ea4d1517f0b88aba0b38d34be0edb0b845aac3eaa724f3bd1f8f83f640 ]] || {
  echo "unexpected n=12 universe SHA-256: $input_sha" >&2
  exit 65
}

python3 "$stage_dir/verify_outputs.py" --one-arm "$prime" "$seed" >/dev/null

pivot_stem=${pivot_report##*/}
pivot_stem=${pivot_stem%.json}
run_dir="$lift_dir/member-$pivot_stem"
for path in "$universe" "$runner" "$wrapper" "$helper"; do
  [[ -e "$path" ]] || { echo "missing launch input: $path" >&2; exit 66; }
done

rsync -azR -e "ssh -p $port -o BatchMode=yes -o ConnectTimeout=20" \
  "$pivot_report" "$universe" "$runner" "$wrapper" "$helper" \
  "$remote:$remote_root/"

local_hashes=$(sha256sum "$pivot_report" "$universe" "$runner" "$wrapper" "$helper")
remote_hashes=$(ssh -p "$port" -o BatchMode=yes -o ConnectTimeout=20 "$remote" \
  "cd '$remote_root'; sha256sum '$pivot_report' '$universe' '$runner' '$wrapper' '$helper'")
[[ "$local_hashes" == "$remote_hashes" ]] || {
  echo "local/A100 launch-input hashes differ" >&2
  diff -u <(printf '%s\n' "$local_hashes") <(printf '%s\n' "$remote_hashes") >&2 || true
  exit 65
}
ssh -p "$port" -o BatchMode=yes -o ConnectTimeout=20 "$remote" \
  "cd '$remote_root'; printf '%s  %s\n' \
    1b1982a266617ccd419d4874abc596f917bf0396acbafac4d7aa67d3054bb2b1 '$colgen' \
    a50338c305b8855a4540a8f55c4d21b1b388428223b0f4e3b7c80280c30f0429 '$lift_binary' \
    | sha256sum -c -"

available_bytes=$(ssh -p "$port" -o BatchMode=yes -o ConnectTimeout=20 "$remote" \
  "free -b | awk '/^Mem:/ {print \$7}'")
[[ "$available_bytes" =~ ^[0-9]+$ ]] || { echo "invalid A100 RAM reading" >&2; exit 69; }
if (( available_bytes < min_available_bytes )); then
  echo "A100 available RAM $available_bytes is below required $min_available_bytes bytes" >&2
  exit 75
fi

launch_line=$(ssh -p "$port" -o BatchMode=yes -o ConnectTimeout=20 "$remote" \
  "cd '$remote_root';
   if pgrep -af '[r]un_remote_member_pivot.sh' >/dev/null; then
     echo 'another exact-lift runner is active' >&2; exit 75;
   fi;
   test ! -e '$run_dir'; test ! -e '${run_dir}.wrapper.exit_code';
   nohup env HHS_THREADS=16 bash '$wrapper' '$pivot_report' '$run_dir' \
     > '${run_dir}.supervisor.log' 2>&1 < /dev/null &
   lift_pid=\$!;
   printf '%s\n' \"\$lift_pid\" > '${run_dir}.supervisor.pid';
   echo LIFT_PID=\$lift_pid")

printf '%s\n' \
  "HHS_LIFT_LAUNCHED" \
  "pivot_report=$pivot_report" \
  "pivot_report_sha256=$(sha256sum "$pivot_report" | cut -d' ' -f1)" \
  "rank=$rank_a/$rank_augmented" \
  "verdict=$verdict" \
  "pivot_sha256=$pivot_sha" \
  "available_bytes=$available_bytes" \
  "$launch_line" \
  "run_dir=$run_dir"
