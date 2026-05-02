#!/usr/bin/env bash
set -euo pipefail

source_root="${1:?usage: install_supertux_probe.sh /path/to/supertux}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f "$source_root/CMakeLists.txt" || ! -f "$source_root/src/supertux/game_session.cpp" ]]; then
  echo "SuperTux source checkout not found: $source_root" >&2
  exit 1
fi

mkdir -p "$source_root/src/wargames"
cp "$repo_root/wargames/games/supertux/supertux/wargames_state_export.cpp" "$source_root/src/wargames/wargames_state_export.cpp"
cp "$repo_root/wargames/games/supertux/supertux/wargames_state_export.hpp" "$source_root/src/wargames/wargames_state_export.hpp"

python3 - "$source_root/src/supertux/game_session.cpp" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
if '#include "wargames/wargames_state_export.hpp"' not in text:
    text = text.replace(
        '#include "worldmap/worldmap.hpp"\n',
        '#include "worldmap/worldmap.hpp"\n#include "wargames/wargames_state_export.hpp"\n',
    )
if "WarGamesStateExport::get().tick(*this);" not in text:
    text = text.replace(
        "  if (m_currentsector == nullptr)\n    return;\n\n  // Update sounds.",
        "  if (m_currentsector == nullptr)\n    return;\n\n  WarGamesStateExport::get().tick(*this);\n\n  // Update sounds.",
    )
path.write_text(text, encoding="utf-8")
PY

cmake -S "$source_root" -B "$source_root/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_NETWORKING=OFF \
  -DENABLE_OPENGL=OFF \
  -DSUPERTUX_PCH=OFF \
  -DBUILD_TESTING=OFF
cmake --build "$source_root/build" --target supertux2 -j"$(getconf _NPROCESSORS_ONLN)"
