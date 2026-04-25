#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 /path/to/OpenRA" >&2
  exit 2
fi

openra_root="$1"
src_dir="$openra_root/OpenRA.Mods.Common/Traits/World/WarGames"
mkdir -p "$src_dir"
cp "$(dirname "$0")/WarGamesStateExport.cs" "$src_dir/WarGamesStateExport.cs"

python3 - "$openra_root/OpenRA.Game/Map/Map.cs" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
text = text.replace("CryptoUtil.SHA1Hash([])", "CryptoUtil.SHA1Hash(Array.Empty<byte>())")
path.write_text(text)
PY

if [[ -f "$(dirname "$0")/rules_patch.yaml" ]]; then
	mkdir -p "$openra_root/mods/ra/rules"
	cp "$(dirname "$0")/rules_patch.yaml" "$openra_root/mods/ra/rules/wargames-state-export.yaml"
fi

python3 - "$openra_root/mods/ra/mod.yaml" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
entry = "\tra|rules/wargames-state-export.yaml"
if entry not in text:
    anchor = "\tra|rules/world.yaml\n"
    if anchor not in text:
        raise SystemExit("could not find ra|rules/world.yaml in mod.yaml")
    text = text.replace(anchor, anchor + entry + "\n", 1)
    path.write_text(text)
PY

make -C "$openra_root" all
