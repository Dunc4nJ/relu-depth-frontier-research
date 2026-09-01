#!/usr/bin/env bash
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
g++ -std=c++20 -O3 -DNDEBUG -Wall -Wextra -Wpedantic \
  "$here/rank_rectangular_flint.cpp" \
  $(pkg-config --cflags --libs flint openssl) \
  -o "$here/rank_rectangular_flint"
