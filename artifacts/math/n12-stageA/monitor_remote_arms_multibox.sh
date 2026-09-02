#!/usr/bin/env bash
set -euo pipefail

# Observe the four fixed EXP-0037 arms across two boxes. This watcher never
# launches or signals a remote process; it verifies, rsyncs, and mails results.
cd /data/projects/relu-depth-frontier-research
out_dir="artifacts/math/n12-stageA"
remote_out="/workspace/relu/$out_dir"
state_dir="$out_dir/arm-monitor-multibox-state"
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
ports=(15464 15464 29562 29562)
boxes=(h100-nvl h100-nvl h100-pcie h100-pcie)
remote="root@ssh1.vast.ai"

mkdir -p "$state_dir"
printf '%s\n' "$$" > "$out_dir/arm-monitor-multibox.supervisor.pid"

send_mail() {
  local subject="$1"
  local body="$2"
  /home/ubuntu/.local/bin/am mail send \
    --project /data/projects/relu-depth-frontier-research \
    --from NavyTiger --to AmberBluff --thread-id "$thread_id" \
    --subject "$subject" --body "$body" --json
}

remote_complete() {
  local index="$1"
  local label="${labels[$index]}"
  ssh -p "${ports[$index]}" "$remote" \
    "test -f '$remote_out/$label.json' && grep -q 'STREAMRANK_EXIT=0' '$remote_out/$label.supervisor.log'"
}

remote_started() {
  local index="$1"
  local label="${labels[$index]}"
  ssh -p "${ports[$index]}" "$remote" \
    "test -f '$remote_out/$label.wrapper.pid' || test -f '$remote_out/$label.supervisor.log'"
}

remote_alive() {
  local index="$1"
  local label="${labels[$index]}"
  ssh -p "${ports[$index]}" "$remote" \
    "test -f '$remote_out/$label.wrapper.pid' && kill -0 \"\$(cat '$remote_out/$label.wrapper.pid')\""
}

copy_arm_files() {
  local index="$1"
  local label="${labels[$index]}"
  local suffix
  for suffix in json stdout.log stderr.log supervisor.log telemetry.csv wrapper.pid; do
    rsync -az -e "ssh -p ${ports[$index]}" \
      "$remote:$remote_out/$label.$suffix" "$out_dir/"
  done
}

while true; do
  completed=0
  for index in 0 1 2 3; do
    label="${labels[$index]}"
    prime="${primes[$index]}"
    seed="${seeds[$index]}"
    box="${boxes[$index]}"
    receipt="$state_dir/$label.mailed"
    if remote_complete "$index"; then
      completed=$((completed + 1))
      if [[ ! -e "$receipt" ]]; then
        copy_arm_files "$index"
        if ! summary="$(python3 "$out_dir/verify_outputs.py" --one-arm "$prime" "$seed")"; then
          send_mail "[$thread_id] Arm verification failed" \
            "Copied $box p=$prime, seed=$seed, but the fail-closed verifier rejected it; no rank/verdict is reported."
          exit 1
        fi
        read -r rank augmented verdict pivot <<<"$(python3 -c \
          'import json,sys; d=json.load(sys.stdin); print(d["rank_a"], d["rank_augmented"], d["verdict"], d["pivot_columns_u64_le_sha256"])' \
          <<<"$summary")"
        send_mail "[$thread_id] Arm p${prime} s${seed}" \
          "$box: 148,629/148,629 columns; rank $rank/$augmented; $verdict; pivot SHA $pivot; binary $binary_sha."
        printf '%s\n' "$summary" > "$receipt"
        printf 'VERIFIED_ARM box=%s prime=%s seed=%s rank=%s augmented=%s verdict=%s pivot_sha256=%s\n' \
          "$box" "$prime" "$seed" "$rank" "$augmented" "$verdict" "$pivot"
      fi
    elif remote_started "$index" && ! remote_alive "$index"; then
      rsync -az -e "ssh -p ${ports[$index]}" \
        "$remote:$remote_out/$label.supervisor.log" "$out_dir/" || true
      send_mail "[$thread_id] Arm stopped" \
        "$box arm p=$prime, seed=$seed stopped before a verified result; inspect the preserved supervisor log."
      exit 1
    fi
  done
  if (( completed == 4 )); then
    break
  fi
  sleep 60
done

python3 "$out_dir/verify_outputs.py" --write-report "$out_dir/verification.json"
aggregate="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["aggregate_modular_sketch_verdict"])' "$out_dir/verification.json")"
send_mail "[$thread_id] Four arms verified" \
  "4/4 arms independently verified and rsynced; aggregate finite modular-sketch verdict $aggregate. Cross-box scheduling changes no verdict rule."
echo MONITOR_COMPLETE
