#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
  toolchain_script="${BASH_SOURCE[0]}"
elif [[ -n "${ZSH_VERSION:-}" ]]; then
  toolchain_script="${(%):-%N}"
else
  toolchain_script="$0"
fi
campaign_root="$(cd "$(dirname "$toolchain_script")/.." && pwd -P)"
export ELAN_HOME="$campaign_root/.toolchains/elan"
export VIRTUAL_ENV="$campaign_root/.venv"
export CVC5_HOME="$campaign_root/.toolchains/cvc5-1.3.4/cvc5-Linux-x86_64-static"
export PATH="$VIRTUAL_ENV/bin:$ELAN_HOME/bin:$CVC5_HOME/bin:$PATH"

printf 'Campaign toolchain active: %s\n' "$campaign_root"
python --version
lean --version
