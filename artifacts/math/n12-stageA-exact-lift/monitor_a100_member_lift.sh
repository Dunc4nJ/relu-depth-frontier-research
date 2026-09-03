#!/usr/bin/env bash
set -euo pipefail

if (( $# != 1 )); then
  echo "usage: $0 RUN_DIR" >&2
  exit 64
fi

cd /data/projects/relu-depth-frontier-research
run_dir=$1
remote="root@ssh5.vast.ai"
port=29562
remote_root=/workspace/relu
thread_id=relu-depth-frontier-research-hhs
poll_seconds=${HHS_POLL_SECONDS:-60}
once=${HHS_ONCE:-0}
expected_universe_sha=f98352ea4d1517f0b88aba0b38d34be0edb0b845aac3eaa724f3bd1f8f83f640
wrapper_prefix="${run_dir}.wrapper"
supervisor_prefix="${run_dir}.supervisor"

send_mail() {
  local recipient=$1
  local subject=$2
  local body=$3
  /home/ubuntu/.local/bin/am mail send \
    --project /data/projects/relu-depth-frontier-research \
    --from NavyTiger --to "$recipient" --thread-id "$thread_id" \
    --subject "$subject" --body "$body" --json
}

copy_if_present() {
  local remote_path=$1
  local local_path=$2
  if ssh -n -p "$port" -o BatchMode=yes -o ConnectTimeout=20 "$remote" \
    "test -f '$remote_root/$remote_path'"; then
    rsync -az -e "ssh -p $port -o BatchMode=yes -o ConnectTimeout=20" \
      "$remote:$remote_root/$remote_path" "$local_path"
  fi
}

while true; do
  if ssh -n -p "$port" -o BatchMode=yes -o ConnectTimeout=20 "$remote" \
    "test -f '$remote_root/${wrapper_prefix}.exit_code'"; then
    mkdir -p "$run_dir"
    for suffix in supervisor.log supervisor.pid wrapper.start_utc.txt wrapper.end_utc.txt wrapper.exit_code; do
      copy_if_present "${run_dir}.${suffix}" "${run_dir}.${suffix}"
    done
    exit_code=$(<"${wrapper_prefix}.exit_code")
    if [[ "$exit_code" != 0 ]]; then
      send_mail AmberBluff "[$thread_id] A100 exact lift failed" \
        "A100 wrapper exited $exit_code/1 before a verified n=12 exact result. Preserved supervisor log: ${supervisor_prefix}.log."
      exit 1
    fi

    required=(
      member_sketch_build_report.json
      member_big_solver_report.json
      member_exact_witness.json
      member_exact_lift_report.json
      member_upstream.json
      upstream_translation_report.json
    )
    optional=(
      gather-plan.stdout.json
      exact_batches.sha256
      build.stdout.json
      build.stderr.log
      solve.stdout.json
      solve.stderr.log
      finalize.stdout.json
      modular_support_p65521.json
      pipeline.log
    )
    for file in "${required[@]}"; do
      ssh -n -p "$port" -o BatchMode=yes -o ConnectTimeout=20 "$remote" \
        "test -f '$remote_root/$run_dir/$file'" || {
          send_mail AmberBluff "[$thread_id] A100 exact lift incomplete" \
            "Wrapper reported 0/1, but required output $run_dir/$file is missing; no exact verdict reported."
          exit 1
        }
      copy_if_present "$run_dir/$file" "$run_dir/$file"
    done
    for file in "${optional[@]}"; do
      copy_if_present "$run_dir/$file" "$run_dir/$file"
    done

    python3 artifacts/math/n12-stageA-exact-lift/verify_member_lift_outputs.py \
      --run-dir "$run_dir" --expected-n 12 \
      --expected-universe-sha256 "$expected_universe_sha" \
      --output "$run_dir/verification.json" \
      > "$run_dir/verification.stdout.json"

    read -r rank support real_rows combined_rows denominator_lcm witness_sha upstream_sha <<<"$(
      python3 - "$run_dir/verification.json" <<'PY'
import json
import sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print(
    d["pivot_columns_denominator"], d["recovered_support_numerator"],
    d["real_rows_verified_denominator"], d["combined_rows_verified_denominator"],
    d["coefficient_denominator_lcm"], d["witness_sha256"], d["upstream_sha256"],
)
PY
    )"
    if [[ ! -e "$run_dir/handoff.mailed" ]]; then
      send_mail AmberBluff "[$thread_id] A100 exact lift PASS" \
        "n=12 finite exact lift PASS: real rows $real_rows/$real_rows; combined rows $combined_rows/$combined_rows; support $support/$rank pivots; denominator LCM $denominator_lcm; witness SHA $witness_sha; upstream SHA $upstream_sha. Independent verify11 remains pending."
      send_mail IndigoCarp "[$thread_id] n=12 upstream handoff" \
        "Please run independent verify11 at n=12 on $run_dir/member_upstream.json (SHA-256 $upstream_sha). Custody verifier passed $real_rows/$real_rows real and $combined_rows/$combined_rows combined rows; witness SHA $witness_sha. This is a finite n=12 identity only."
      date -u +%Y-%m-%dT%H:%M:%SZ > "$run_dir/handoff.mailed"
    fi
    echo HHS_A100_LIFT_VERIFIED_AND_HANDED_OFF
    exit 0
  fi

  if ssh -n -p "$port" -o BatchMode=yes -o ConnectTimeout=20 "$remote" \
    "test -f '$remote_root/${supervisor_prefix}.pid'"; then
    remote_pid=$(ssh -n -p "$port" -o BatchMode=yes -o ConnectTimeout=20 "$remote" \
      "cat '$remote_root/${supervisor_prefix}.pid'")
    if ! ssh -n -p "$port" -o BatchMode=yes -o ConnectTimeout=20 "$remote" \
      "kill -0 '$remote_pid' 2>/dev/null"; then
      copy_if_present "${supervisor_prefix}.log" "${supervisor_prefix}.log"
      send_mail AmberBluff "[$thread_id] A100 exact lift stopped" \
        "A100 PID $remote_pid stopped without an exit receipt; no exact verdict reported. Preserved ${supervisor_prefix}.log."
      exit 1
    fi
  elif [[ "$once" == 1 ]]; then
    echo HHS_A100_LIFT_NOT_LAUNCHED
    exit 75
  fi

  if [[ "$once" == 1 ]]; then
    echo HHS_A100_LIFT_STILL_RUNNING
    exit 75
  fi
  sleep "$poll_seconds"
done
