#!/bin/sh
set -eu

if [ "$#" -ne 3 ]; then
    echo "usage: $0 PRIME SEED TAG" >&2
    exit 64
fi

prime=$1
seed=$2
tag=$3
case "$prime" in
    1000003|1000033) ;;
    *) echo "unregistered prime: $prime" >&2; exit 64 ;;
esac
case "$seed" in
    2026090201|2026090202) ;;
    *) echo "unregistered seed: $seed" >&2; exit 64 ;;
esac

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
cd "$repo_root"
binary=target/release/max11-streamrank
universe=artifacts/math/n11-degree4-loops/loop_inclusive_signed_degree4_n11_v1.json.gz
output="artifacts/math/n11-degree4-loops/${tag}.json"
test -x "$binary"
test -f "$universe"
test ! -e "$output"

gpu_used_mib=$(
    nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits |
        tr -d ' '
)
if [ "$gpu_used_mib" -ge 60000 ]; then
    echo "SOU_GPU_GATE_REFUSED used_mib=$gpu_used_mib limit_mib=60000" >&2
    exit 42
fi
echo "SOU_PREFLIGHT gpu_used_mib=$gpu_used_mib limit_mib=60000 binary_sha256=$(sha256sum "$binary" | cut -d' ' -f1) universe_sha256=$(sha256sum "$universe" | cut -d' ' -f1)" >&2

exec "$binary" run-universe \
    --backend cuda \
    --input "$universe" \
    --n 11 \
    --branch-edges 4 \
    --modulus "$prime" \
    --buckets 32768 \
    --seeds "$seed" \
    --batch-size 1024 \
    --gemm-block 8192 \
    --rank-panel 64 \
    --threads 4 \
    --loop-inclusive true \
    --include-linear-carrier true \
    --abort-rank-above 10922 \
    --abort-rss-kib-above 25165824 \
    --expected-columns 137505 \
    --output "$output"
