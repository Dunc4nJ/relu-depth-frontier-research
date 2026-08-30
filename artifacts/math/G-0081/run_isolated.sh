#!/usr/bin/busybox sh
set -eu

launcher=$(/usr/bin/busybox readlink -f -- "$0")
here=$(/usr/bin/busybox dirname -- "$launcher")
root=$(/usr/bin/busybox readlink -f -- "$here/../../..")

exec /usr/bin/busybox env -i \
  PATH=/usr/bin:/bin \
  LANG=C \
  LC_ALL=C \
  "$root/.toolchains/g0081-venv/bin/python" -I -S -B \
  "$here/full_dictionary_schur.py" "$@"
