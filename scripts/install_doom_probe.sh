#!/usr/bin/env bash
set -euo pipefail

source_root="${1:?usage: install_doom_probe.sh /path/to/chocolate-doom}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
doom_dir="$source_root/src/doom"

if [[ ! -f "$source_root/CMakeLists.txt" || ! -f "$doom_dir/g_game.c" ]]; then
  echo "Chocolate Doom source checkout not found: $source_root" >&2
  exit 1
fi

cp "$repo_root/wargames/games/doom/chocolate/wargames_state_export.c" "$doom_dir/wargames_state_export.c"
cp "$repo_root/wargames/games/doom/chocolate/wargames_state_export.h" "$doom_dir/wargames_state_export.h"

python3 - "$doom_dir/CMakeLists.txt" "$doom_dir/g_game.c" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

cmake = Path(sys.argv[1])
game = Path(sys.argv[2])

text = cmake.read_text(encoding="utf-8")
needle = "            g_game.c        g_game.h\n"
if "wargames_state_export.c" not in text:
    text = text.replace(
        needle,
        needle + "            wargames_state_export.c wargames_state_export.h\n",
    )
    cmake.write_text(text, encoding="utf-8")

text = game.read_text(encoding="utf-8")
if '#include "wargames_state_export.h"' not in text:
    text = text.replace('#include "statdump.h"\n', '#include "statdump.h"\n#include "wargames_state_export.h"\n')
if "Wargames_StateExport_Tick();" not in text:
    text = text.replace(
        "      case GS_DEMOSCREEN: \n\tD_PageTicker (); \n\tbreak;\n    }        \n}",
        "      case GS_DEMOSCREEN: \n\tD_PageTicker (); \n\tbreak;\n    }\n\n    Wargames_StateExport_Tick();\n}",
    )
game.write_text(text, encoding="utf-8")
PY

cmake -S "$source_root" -B "$source_root/build" \
  -DENABLE_SDL2_MIXER=OFF \
  -DENABLE_SDL2_NET=OFF \
  -DCMAKE_BUILD_TYPE=Release
cmake --build "$source_root/build" --target chocolate-doom -j"$(getconf _NPROCESSORS_ONLN)"
