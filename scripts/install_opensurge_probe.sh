#!/usr/bin/env bash
set -euo pipefail

source_root="${1:?usage: install_opensurge_probe.sh /path/to/opensurge}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
deps_root="${WARGAMES_OPENSURGE_DEPS_ROOT:-$(dirname "$source_root")/deps}"
surgescript_root="$deps_root/surgescript"
surgescript_prefix="$deps_root/surgescript-prefix"

if [[ ! -f "$source_root/CMakeLists.txt" || ! -f "$source_root/src/scenes/level.c" ]]; then
  echo "Open Surge source checkout not found: $source_root" >&2
  exit 1
fi

if [[ ! -f "$surgescript_prefix/include/surgescript.h" || ! -f "$surgescript_prefix/lib/libsurgescript-static.a" ]]; then
  mkdir -p "$deps_root"
  if [[ ! -d "$surgescript_root/.git" ]]; then
    git clone --depth 1 --branch v0.6.1 https://github.com/alemart/surgescript.git "$surgescript_root"
  fi
  cmake -S "$surgescript_root" -B "$surgescript_root/build" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$surgescript_prefix" \
    -DWANT_SHARED=OFF \
    -DWANT_STATIC=ON \
    -DWANT_EXECUTABLE=OFF
  cmake --build "$surgescript_root/build" -j"$(getconf _NPROCESSORS_ONLN)"
  cmake --install "$surgescript_root/build"
fi

mkdir -p "$source_root/src/wargames"
cp "$repo_root/wargames/games/opensurge/opensurge/wargames_state_export.c" "$source_root/src/wargames/wargames_state_export.c"
cp "$repo_root/wargames/games/opensurge/opensurge/wargames_state_export.h" "$source_root/src/wargames/wargames_state_export.h"

python3 - "$source_root/src/misc/cmake/srcs.cmake" "$source_root/src/scenes/level.c" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

srcs = Path(sys.argv[1])
level = Path(sys.argv[2])

text = srcs.read_text(encoding="utf-8")
if "src/wargames/wargames_state_export.c" not in text:
    text = text.replace(
        "  src/scenes/level.c\n",
        "  src/scenes/level.c\n  src/wargames/wargames_state_export.c\n",
    )
    srcs.write_text(text, encoding="utf-8")

text = level.read_text(encoding="utf-8")
if '#include "../wargames/wargames_state_export.h"' not in text:
    text = text.replace(
        '#include "../scenes/editorpal.h"\n',
        '#include "../scenes/editorpal.h"\n#include "../wargames/wargames_state_export.h"\n',
    )
if "Wargames_StateExport_Tick();" not in text:
    text = text.replace(
        "    /* release major entities */\n",
        "    Wargames_StateExport_Tick();\n\n    /* release major entities */\n",
    )
level.write_text(text, encoding="utf-8")
PY

cmake -S "$source_root" -B "$source_root/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DGAME_RUNINPLACE=ON \
  -DWANT_PLAYMOD=OFF \
  -DWANT_BETTER_GAMEPAD=OFF \
  -DSURGESCRIPT_STATIC=ON \
  -DSURGESCRIPT_INCLUDE_PATH="$surgescript_prefix/include" \
  -DSURGESCRIPT_LIBRARY_PATH="$surgescript_prefix/lib"
cmake --build "$source_root/build" --target opensurge -j"$(getconf _NPROCESSORS_ONLN)"
