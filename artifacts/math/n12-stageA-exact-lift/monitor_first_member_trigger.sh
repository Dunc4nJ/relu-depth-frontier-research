#!/usr/bin/env bash
set -euo pipefail

cd /data/projects/relu-depth-frontier-research
stage_dir=artifacts/math/n12-stageA
arm_state_dir="$stage_dir/arm-monitor-multibox-state"
lift_dir=artifacts/math/n12-stageA-exact-lift
trigger_dir="$lift_dir/trigger-watch"
thread_id=relu-depth-frontier-research-hhs
poll_seconds=${HHS_POLL_SECONDS:-15}
once=${HHS_ONCE:-0}

mkdir -p "$trigger_dir"
printf '%s\n' "$$" > "$trigger_dir/watcher.pid"

send_mail() {
  local subject=$1
  local body=$2
  /home/ubuntu/.local/bin/am mail send \
    --project /data/projects/relu-depth-frontier-research \
    --from NavyTiger --to AmberBluff --thread-id "$thread_id" \
    --subject "$subject" --body "$body" --json
}

while true; do
  mapfile -t receipts < <(
    find "$arm_state_dir" -maxdepth 1 -type f -name '*.mailed' \
      -printf '%T@ %f\n' 2>/dev/null | sort -n
  )
  for stamped in "${receipts[@]}"; do
    receipt=${stamped#* }
    label=${receipt%.mailed}
    pivot_report="$stage_dir/$label.json"
    [[ -f "$pivot_report" ]] || continue
    read -r verdict rank_a rank_augmented <<<"$(
      python3 - "$pivot_report" <<'PY'
import json
import sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
s = d["sketches"][0]
print(s["verdict"], s["rank_a"], s["rank_augmented"])
PY
    )"
    [[ "$verdict" == MEMBER && "$rank_a" == "$rank_augmented" ]] || continue

    if ! mkdir "$trigger_dir/launch.lock" 2>/dev/null; then
      echo HHS_TRIGGER_ALREADY_CLAIMED
      exit 0
    fi
    date -u +%Y-%m-%dT%H:%M:%SZ > "$trigger_dir/launch.start_utc.txt"
    set +e
    RAM_AGREEMENT_CONFIRMED=1 \
      "$lift_dir/launch_a100_member_lift.sh" "$pivot_report" \
      > "$trigger_dir/launch.stdout.log" 2> "$trigger_dir/launch.stderr.log"
    launch_code=$?
    set -e
    printf '%s\n' "$launch_code" > "$trigger_dir/launch.exit_code"
    if (( launch_code != 0 )); then
      send_mail "[$thread_id] A100 launch failed" \
        "Verified MEMBER arm $label ($rank_a/$rank_augmented), but the guarded A100 launcher exited $launch_code/1. No lift verdict; inspect $trigger_dir/launch.stderr.log."
      exit "$launch_code"
    fi

    run_dir=$(awk -F= '$1 == "run_dir" {print $2}' "$trigger_dir/launch.stdout.log")
    lift_pid=$(awk -F= '$1 == "LIFT_PID" {print $2}' "$trigger_dir/launch.stdout.log")
    [[ -n "$run_dir" && -n "$lift_pid" ]] || {
      send_mail "[$thread_id] A100 launch receipt malformed" \
        "The guarded launcher returned 0/1 for $label but omitted run_dir or LIFT_PID; inspect $trigger_dir/launch.stdout.log."
      exit 65
    }
    printf '%s\n' "$pivot_report" > "$trigger_dir/selected_pivot.txt"
    printf '%s\n' "$run_dir" > "$trigger_dir/run_dir.txt"
    printf '%s\n' "$lift_pid" > "$trigger_dir/remote_lift.pid"

    nohup bash "$lift_dir/monitor_a100_member_lift.sh" "$run_dir" \
      > "$trigger_dir/completion-monitor.supervisor.log" 2>&1 < /dev/null &
    completion_pid=$!
    printf '%s\n' "$completion_pid" > "$trigger_dir/completion-monitor.supervisor.pid"
    date -u +%Y-%m-%dT%H:%M:%SZ > "$trigger_dir/launch.end_utc.txt"
    send_mail "[$thread_id] A100 exact lift launched" \
      "First locally reverified MEMBER receipt: $label, rank $rank_a/$rank_augmented. A100 remote PID $lift_pid; local completion watcher PID $completion_pid; 16 threads / 64 GiB reservation; run $run_dir. Verdict rule unchanged."
    echo HHS_FIRST_MEMBER_TRIGGERED
    exit 0
  done

  if [[ "$once" == 1 ]]; then
    echo HHS_NO_VERIFIED_MEMBER_RECEIPT
    exit 75
  fi
  sleep "$poll_seconds"
done
