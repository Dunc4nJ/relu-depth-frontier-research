#!/usr/bin/env bash
set -euo pipefail

campaign_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
source "$campaign_root/scripts/activate-toolchain.sh" >/dev/null
python "$campaign_root/scripts/verify-toolchain.py"
cvc5_cli_output="$({
  cat <<'EOF'
(set-logic QF_LRA)
(declare-fun x () Real)
(assert (= x (/ 1 3)))
(check-sat)
(push 1)
(assert (< x 0))
(check-sat)
EOF
} | cvc5 --incremental --lang smt2)"
if [[ "$cvc5_cli_output" != $'sat\nunsat' ]]; then
  printf 'cvc5-cli-known-answer: FAIL\n%s\n' "$cvc5_cli_output" >&2
  exit 1
fi
printf 'cvc5-cli-known-answer: PASS\n'
(
  cd "$campaign_root/formalization"
  lake build
)
printf 'lean-mathlib-smoke: PASS\n'
