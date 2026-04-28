#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 /path/to/stk-code" >&2
  exit 2
fi

stk_root="$1"
if [[ ! -f "$stk_root/CMakeLists.txt" || ! -f "$stk_root/src/main_loop.cpp" ]]; then
  echo "not a SuperTuxKart source checkout: $stk_root" >&2
  exit 2
fi

src_dir="$stk_root/src/wargames"
mkdir -p "$src_dir"
cp "$(dirname "$0")/wargames_state_export.hpp" "$src_dir/wargames_state_export.hpp"
cp "$(dirname "$0")/wargames_state_export.cpp" "$src_dir/wargames_state_export.cpp"

python3 - "$stk_root/src/main_loop.cpp" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
include = '#include "wargames/wargames_state_export.hpp"\n'
if include not in text:
    anchor = '#include "race/history.hpp"\n'
    if anchor not in text:
        raise SystemExit("could not find race/history.hpp include in main_loop.cpp")
    text = text.replace(anchor, anchor + include, 1)

call = "WarGamesStateExport::get().tick();"
lines = [line for line in text.splitlines(keepends=True) if call not in line]
patched: list[str] = []
inserted = 0
for line in lines:
    patched.append(line)
    if "World::getWorld()->updateTime(1);" not in line:
        continue
    indent = line[: len(line) - len(line.lstrip())]
    patched.append(f"{indent}{call}\n")
    inserted += 1
if inserted == 0:
    raise SystemExit("could not find race time update hook in main_loop.cpp")
text = "".join(patched)

path.write_text(text)
PY

python3 - "$stk_root/lib/graphics_engine/include/vk_mem_alloc.h" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
if not path.exists():
    raise SystemExit("could not find vk_mem_alloc.h")
text = path.read_text()
lines = text.splitlines(keepends=True)
patched: list[str] = []
inserted = False
for index, line in enumerate(lines):
    patched.append(line)
    if line.strip() != "#include <mutex>":
        continue
    next_line = lines[index + 1] if index + 1 < len(lines) else ""
    if next_line.strip() == "#include <cstdio>":
        continue
    indent = line[: len(line) - len(line.lstrip())]
    patched.append(f"{indent}#include <cstdio>\n")
    inserted = True
if not inserted and not any(line.strip() == "#include <cstdio>" for line in lines):
    raise SystemExit("could not patch vk_mem_alloc.h cstdio include")
text = "".join(patched)
path.write_text(text)
PY

python3 - "$stk_root/lib/graphics_engine/src" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1])
if not src.exists():
    raise SystemExit("could not find graphics_engine src directory")
for path in src.glob("*.cpp"):
    text = path.read_text()
    if "std::runtime_error" not in text or "#include <stdexcept>" in text:
        continue
    lines = text.splitlines(keepends=True)
    insert_at = 0
    for index, line in enumerate(lines):
        if line.startswith("#include "):
            insert_at = index + 1
    lines.insert(insert_at, "#include <stdexcept>\n")
    path.write_text("".join(lines))
PY

cmake -S "$stk_root" -B "$stk_root/cmake_build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_RECORDER=off \
  -DCHECK_ASSETS=off \
  -DNO_SHADERC=on
cmake --build "$stk_root/cmake_build" --parallel "${WARGAMES_BUILD_JOBS:-$(nproc)}"
