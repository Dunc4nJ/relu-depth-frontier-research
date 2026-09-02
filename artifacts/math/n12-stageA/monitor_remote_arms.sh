#!/usr/bin/env bash
set -euo pipefail

# Durable local two-slot watcher. It never changes an arm's mathematical
# parameters: it only fills one of two 60-thread scheduling slots after a
# completed arm frees it, then verifies, copies, and mails each receipt.
cd /data/projects/relu-depth-frontier-research
remote="root@ssh1.vast.ai"
port=15464
out_dir="artifacts/math/n12-stageA"
remote_out="/workspace/relu/$out_dir"
state_dir="$out_dir/arm-monitor-state"
binary_sha="cdf835b269d25a37f110d72f16865e6f511d5154b5caf7808dd2eb1d82bc85c3"
thread_id="relu-depth-frontier-research-max11-root-gmp.16"
labels=(
  n12-stageA-m128000-p1000003-s2026090201-cuda
  n12-stageA-m128000-p1000003-s2026090202-cuda
  n12-stageA-m128000-p1000033-s2026090201-cuda
  n12-stageA-m128000-p1000033-s2026090202-cuda
)
primes=(1000003 1000003 1000033 1000033)
seeds=(2026090201 2026090202 2026090201 2026090202)

mkdir -p "$state_dir"
printf '%s\n' "$$" > "$out_dir/arm-monitor-concurrent.supervisor.pid"

send_mail() {
  local subject="$1"
  local body="$2"
  /home/ubuntu/.local/bin/am mail send \
    --project /data/projects/relu-depth-frontier-research \
    --from NavyTiger --to AmberBluff --thread-id "$thread_id" \
    --subject "$subject" --body "$body" --json
}

remote_complete() {
  local label="$1"
  ssh -p "$port" "$remote" \
    "test -f '$remote_out/$label.json' && grep -q 'STREAMRANK_EXIT=0' '$remote_out/$label.supervisor.log'"
}

remote_started() {
  local label="$1"
  ssh -p "$port" "$remote" \
    "test -f '$remote_out/$label.wrapper.pid' || test -f '$remote_out/$label.supervisor.log'"
}

remote_alive() {
  local label="$1"
  ssh -p "$port" "$remote" \
    "test -f '$remote_out/$label.wrapper.pid' && kill -0 \"\$(cat '$remote_out/$label.wrapper.pid')\""
}

copy_arm_files() {
  local label="$1"
  local suffix
  for suffix in json stdout.log stderr.log supervisor.log telemetry.csv wrapper.pid; do
    rsync -az -e "ssh -p $port" \
      "$remote:$remote_out/$label.$suffix" "$out_dir/"
  done
}

launch_arm() {
  local index="$1"
  local label="${labels[$index]}"
  local prime="${primes[$index]}"
  local seed="${seeds[$index]}"
  local pids gpu_used
  gpu_used="$(ssh -p "$port" "$remote" \
    "nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -n1")"
  gpu_used="${gpu_used//[[:space:]]/}"
  if (( gpu_used >= 90000 )); then
    send_mail "[$thread_id] Scheduler gate" \
      "Refused to launch p=$prime, seed=$seed: aggregate GPU use $gpu_used/95,830 MiB."
    exit 70
  fi
  pids="$(ssh -p "$port" "$remote" "set -euo pipefail; cd /workspace/relu; \
    label='$label'; supervisor='$remote_out/$label.supervisor.log'; \
    wrapper_pid_file='$remote_out/$label.wrapper.pid'; \
    test ! -e \"\$supervisor\"; test ! -e \"\$wrapper_pid_file\"; \
    nohup bash artifacts/math/n12-stageA/run_remote_arm.sh '$prime' '$seed' \"\$label\" \
      > \"\$supervisor\" 2>&1 < /dev/null & wrapper_pid=\$!; \
    printf '%s\\n' \"\$wrapper_pid\" > \"\$wrapper_pid_file\"; sleep 3; \
    reducer_pid=\$(pgrep -P \"\$wrapper_pid\" -f 'max11-streamrank run-universe' | head -n1); \
    test -n \"\$reducer_pid\"; printf '%s %s\\n' \"\$wrapper_pid\" \"\$reducer_pid\"")"
  send_mail "[$thread_id] Concurrent arm launched" \
    "p=$prime, seed=$seed wrapper/reducer PIDs $pids; two-slot/120-thread cap; verdict rule unchanged."
  printf 'LAUNCHED_ARM prime=%s seed=%s pids=%s\n' "$prime" "$seed" "$pids"
}

while true; do
  completed=0
  active=0
  for index in 0 1 2 3; do
    label="${labels[$index]}"
    prime="${primes[$index]}"
    seed="${seeds[$index]}"
    receipt="$state_dir/$label.mailed"
    if remote_complete "$label"; then
      completed=$((completed + 1))
      if [[ ! -e "$receipt" ]]; then
        copy_arm_files "$label"
        if ! summary="$(python3 "$out_dir/verify_outputs.py" --one-arm "$prime" "$seed")"; then
          send_mail "[$thread_id] Arm verification failed" \
            "Copied p=$prime, seed=$seed, but the fail-closed verifier rejected it; no rank/verdict is reported."
          exit 1
        fi
        read -r rank augmented verdict pivot <<<"$(python3 -c \
          'import json,sys; d=json.load(sys.stdin); print(d["rank_a"], d["rank_augmented"], d["verdict"], d["pivot_columns_u64_le_sha256"])' \
          <<<"$summary")"
        send_mail "[$thread_id] Arm p${prime} s${seed}" \
          "148,629/148,629 columns; rank $rank/$augmented; $verdict; pivot SHA $pivot; binary $binary_sha."
        printf '%s\n' "$summary" > "$receipt"
        printf 'VERIFIED_ARM prime=%s seed=%s rank=%s augmented=%s verdict=%s pivot_sha256=%s\n' \
          "$prime" "$seed" "$rank" "$augmented" "$verdict" "$pivot"
      fi
    elif remote_alive "$label"; then
      active=$((active + 1))
    elif remote_started "$label"; then
      rsync -az -e "ssh -p $port" \
        "$remote:$remote_out/$label.supervisor.log" "$out_dir/" || true
      send_mail "[$thread_id] Arm stopped" \
        "Arm p=$prime, seed=$seed stopped before a verified result; inspect the preserved supervisor log."
      exit 1
    fi
  done

  if (( completed == 4 )); then
    break
  fi
  while (( active < 2 )); do
    next_index=-1
    for index in 0 1 2 3; do
      if ! remote_started "${labels[$index]}"; then
        next_index="$index"
        break
      fi
    done
    if (( next_index < 0 )); then
      break
    fi
    launch_arm "$next_index"
    active=$((active + 1))
  done
  sleep 60
done

python3 "$out_dir/verify_outputs.py" --write-report "$out_dir/verification.json"
aggregate="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["aggregate_modular_sketch_verdict"])' "$out_dir/verification.json")"
send_mail "[$thread_id] Four arms verified" \
  "4/4 arms independently verified and rsynced; aggregate finite modular-sketch verdict $aggregate. Scheduling amendment changes no verdict rule."
echo MONITOR_COMPLETE
