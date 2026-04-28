#!/usr/bin/env bash
set -euo pipefail

stk_root="${1:-${LAYERBRAIN_WARGAMES_SUPERTUXKART_SOURCE_ROOT:-}}"
if [[ -z "$stk_root" ]]; then
  echo "usage: scripts/install_supertuxkart_probe.sh /path/to/stk-code" >&2
  exit 2
fi

"$(dirname "$0")/../wargames/games/supertuxkart/stk/build.sh" "$stk_root"
