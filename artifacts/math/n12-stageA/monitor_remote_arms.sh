#!/usr/bin/env bash
set -euo pipefail

# Durable local watcher: copy each completed remote arm, fail-closed verify it,
# then send the orchestrator the requested rank/verdict/pivot receipt.
cd /data/projects/relu-depth-frontier-research
remote="root@ssh1.vast.ai"
port=15464
out_dir="artifacts/math/n12-stageA"
remote_out="/workspace/relu/$out_dir"
coordinator_pid_file="$remote_out/all-arms-sequential.supervisor.pid"
binary_sha="cdf835b269d25a37f110d72f16865e6f511d5154b5caf7808dd2eb1d82bc85c3"
thread_id="relu-depth-frontier-research-max11-root-gmp.16"

send_mail() {
  local subject="$1"
  local body="$2"
  /home/ubuntu/.local/bin/am mail send \
    --project /data/projects/relu-depth-frontier-research \
    --from NavyTiger --to AmberBluff --thread-id "$thread_id" \
    --subject "$subject" --body "$body" --json
}

copy_arm_files() {
  local label="$1"
  local suffix
  for suffix in json stdout.log stderr.log supervisor.log telemetry.csv; do
    rsync -az -e "ssh -p $port" \
      "$remote:$remote_out/$label.$suffix" "$out_dir/"
  done
}

for prime in 1000003 1000033; do
  for seed in 2026090201 2026090202; do
    label="n12-stageA-m128000-p${prime}-s${seed}-cuda"
    while true; do
      if ssh -p "$port" "$remote" \
          "test -f '$remote_out/$label.json' && grep -q 'STREAMRANK_EXIT=0' '$remote_out/$label.supervisor.log'"; then
        break
      fi
      coordinator_pid="$(ssh -p "$port" "$remote" "cat '$coordinator_pid_file'")"
      if ! ssh -p "$port" "$remote" "kill -0 '$coordinator_pid'"; then
        rsync -az -e "ssh -p $port" \
          "$remote:$remote_out/$label.supervisor.log" "$out_dir/" || true
        send_mail "[$thread_id] Arm stopped" \
          "Coordinator stopped before a verified result for p=$prime, seed=$seed; inspect the preserved supervisor log."
        exit 1
      fi
      sleep 60
    done

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
    printf 'VERIFIED_ARM prime=%s seed=%s rank=%s augmented=%s verdict=%s pivot_sha256=%s\n' \
      "$prime" "$seed" "$rank" "$augmented" "$verdict" "$pivot"
  done
done

echo MONITOR_COMPLETE
