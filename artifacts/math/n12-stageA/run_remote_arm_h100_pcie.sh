#!/usr/bin/env bash
set -euo pipefail

# H100 PCIe scheduling wrapper for the two p=1,000,033 arms. Mathematical
# parameters match EXP-0037; only colgen threads and the box-local GPU gate vary.
if [[ "$#" -ne 3 ]]; then
  echo "usage: $0 PRIME SEED LABEL" >&2
  exit 2
fi
prime="$1"
seed="$2"
label="$3"
if [[ "$prime" != 1000033 ]]; then
  echo "H100 PCIe wrapper accepts only prime 1000033" >&2
  exit 2
fi
case "$seed" in 2026090201|2026090202) ;; *) echo "unregistered seed" >&2; exit 2;; esac
expected_label="n12-stageA-m128000-p${prime}-s${seed}-cuda"
if [[ "$label" != "$expected_label" ]]; then
  echo "label mismatch: expected $expected_label" >&2
  exit 2
fi

cd /workspace/relu
export PATH="/root/.cargo/bin:$PATH"
export OPENBLAS_CORETYPE=HASWELL
export OPENBLAS_VERBOSE=2
binary="tools/streamrank/target/release/max11-streamrank"
universe="artifacts/math/n12-universe/loopless_signed_degree5_universe_n12_v1.json.gz"
order="artifacts/math/n12-universe/stage_a_order_n12_v1.json"
out_dir="artifacts/math/n12-stageA"
output="$out_dir/$label.json"
stdout_log="$out_dir/$label.stdout.log"
stderr_log="$out_dir/$label.stderr.log"
telemetry="$out_dir/$label.telemetry.csv"
gate="$out_dir/$label.external-gate.txt"
gpu_total_mib=81559
gpu_abort_mib=75000

mkdir -p "$out_dir"
for path in "$output" "$stdout_log" "$stderr_log" "$telemetry" "$gate"; do
  if [[ -e "$path" ]]; then
    echo "REFUSAL: output path exists: $path" >&2
    exit 17
  fi
done

printf '%s  %s\n' \
  cdf835b269d25a37f110d72f16865e6f511d5154b5caf7808dd2eb1d82bc85c3 "$binary" \
  f98352ea4d1517f0b88aba0b38d34be0edb0b845aac3eaa724f3bd1f8f83f640 "$universe" \
  691cb0368545f8834c98e891bbb771476e547ce9e140887c9791710a8786a7c1 "$order" \
  | sha256sum -c -
observed_gpu_total="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n1 | tr -d ' ')"
if [[ "$observed_gpu_total" != "$gpu_total_mib" ]]; then
  echo "GPU total mismatch: expected $gpu_total_mib MiB, got $observed_gpu_total MiB" >&2
  exit 19
fi

date -u +%Y-%m-%dT%H:%M:%SZ
echo "OPENBLAS_CORETYPE=$OPENBLAS_CORETYPE OPENBLAS_VERBOSE=$OPENBLAS_VERBOSE"
echo "SCHEDULING_THREADS=12 GPU_ABORT=${gpu_abort_mib}/${gpu_total_mib} MiB"
sha256sum "$binary" "$universe" "$order"
printf 'timestamp_utc,gpu_used_mib,gpu_total_mib,gpu_util_percent,process_rss_kib\n' >"$telemetry"

"$binary" run-universe \
  --backend cuda \
  --input "$universe" --order-file "$order" \
  --n 12 --branch-edges 5 \
  --modulus "$prime" --buckets 128000 --seeds "$seed" \
  --batch-size 1024 --gemm-block 8192 --rank-panel 64 --threads 12 \
  --include-five-l true \
  --abort-rank-above 100000 --abort-rss-kib-above 230686720 \
  --output "$output" >"$stdout_log" 2>"$stderr_log" &
child=$!
echo "STREAMRANK_PID=$child"

external_abort=0
while kill -0 "$child" 2>/dev/null; do
  gpu_line="$(nvidia-smi --query-gpu=timestamp,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits | head -n1)"
  rss="$(ps -o rss= -p "$child" | tr -d ' ' || true)"
  rss="${rss:-0}"
  printf '%s,%s\n' "$gpu_line" "$rss" >>"$telemetry"
  gpu_used="$(printf '%s\n' "$gpu_line" | cut -d, -f2 | tr -d ' ')"
  if [[ "$gpu_used" =~ ^[0-9]+$ ]] && (( gpu_used >= gpu_abort_mib )); then
    printf 'GPU_ABORT used=%s/%s MiB threshold=%s MiB\n' \
      "$gpu_used" "$gpu_total_mib" "$gpu_abort_mib" | tee "$gate"
    kill -TERM "$child" 2>/dev/null || true
    external_abort=1
    break
  fi
  if (( rss >= 230686720 )); then
    printf 'RSS_ABORT used=%s KiB threshold=230686720 KiB\n' "$rss" | tee "$gate"
    kill -TERM "$child" 2>/dev/null || true
    external_abort=1
    break
  fi
  sleep 15
done

set +e
wait "$child"
child_status=$?
set -e
date -u +%Y-%m-%dT%H:%M:%SZ
echo "STREAMRANK_EXIT=$child_status EXTERNAL_ABORT=$external_abort"
sha256sum "$stdout_log" "$stderr_log" "$telemetry"
if [[ -f "$output" ]]; then
  sha256sum "$output"
fi
if (( external_abort != 0 )); then
  exit 70
fi
exit "$child_status"
