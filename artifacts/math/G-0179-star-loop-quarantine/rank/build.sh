#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
source_path="$script_dir/rank_i128_flint.cpp"
output_path=${1:-"$script_dir/rank_signed_le_flint"}

if [[ -e "$output_path" ]]; then
  echo "refusing to overwrite $output_path" >&2
  exit 1
fi

g++ \
  -std=c++20 \
  -O3 \
  -march=native \
  -Wall \
  -Wextra \
  -Wpedantic \
  "$source_path" \
  -o "$output_path" \
  -lflint \
  -lgmp \
  -lmpfr \
  -lcrypto

sha256sum "$source_path" "$output_path"
ldd "$output_path"
