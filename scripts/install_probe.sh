#!/usr/bin/env bash
set -euo pipefail

openra_root="${1:-${LAYERBRAIN_WARGAMES_REDALERT_OPENRA_ROOT:-}}"
if [[ -z "$openra_root" ]]; then
  echo "usage: scripts/install_probe.sh /path/to/OpenRA" >&2
  exit 2
fi

"$(dirname "$0")/../wargames/games/redalert/openra/build.sh" "$openra_root"
