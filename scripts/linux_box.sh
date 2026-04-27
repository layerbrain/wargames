#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
child_pids=()

cleanup() {
  for pid in "${child_pids[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}

trap cleanup EXIT

export DISPLAY="${LAYERBRAIN_WARGAMES_XVFB_DISPLAY:-:99}"
screen="${LAYERBRAIN_WARGAMES_XVFB_SCREEN:-1280x720x24}"

install_ra_quick_content() {
  local support_dir="${LAYERBRAIN_WARGAMES_REDALERT_OPENRA_SUPPORT_DIR:-/tmp/wargames/openra-support}"
  local content_dir="$support_dir/Content/ra/v2"
  local marker="$content_dir/allies.mix"
  if [ -f "$marker" ] && [ -f "$content_dir/conquer.mix" ] && [ -f "$content_dir/expand/expand2.mix" ] && [ -f "$content_dir/cnc/desert.mix" ]; then
    return
  fi

  mkdir -p "$content_dir"
  local temp_dir archive mirrors url
  temp_dir="$(mktemp -d)"
  archive="$temp_dir/ra-quickinstall.zip"
  mirrors="$temp_dir/mirrors.txt"
  curl -fsSL https://www.openra.net/packages/ra-quickinstall-mirrors.txt -o "$mirrors"
  while IFS= read -r url; do
    url="${url%%#*}"
    url="$(printf '%s' "$url" | xargs)"
    [ -z "$url" ] && continue
    if curl -fL --retry 2 --connect-timeout 10 "$url" -o "$archive"; then
      break
    fi
  done < "$mirrors"
  [ -s "$archive" ] || { echo "failed to download OpenRA Red Alert quickinstall package" >&2; exit 1; }

  unzip -q "$archive" -d "$temp_dir/extracted"
  local required=(
    allies.mix conquer.mix hires.mix interior.mix local.mix lores.mix russian.mix snow.mix sounds.mix speech.mix temperat.mix
    expand/chrotnk1.aud expand/expand2.mix expand/fixit1.aud expand/hires1.mix expand/jburn1.aud expand/jchrge1.aud
    expand/jcrisp1.aud expand/jdance1.aud expand/jjuice1.aud expand/jjump1.aud expand/jlight1.aud expand/jpower1.aud
    expand/jshock1.aud expand/jyes1.aud expand/lores1.mix expand/madchrg2.aud expand/madexplo.aud expand/mboss1.aud
    expand/mhear1.aud expand/mhotdig1.aud expand/mhowdy1.aud expand/mhuh1.aud expand/mlaff1.aud expand/mrise1.aud
    expand/mwrench1.aud expand/myeehaw1.aud expand/myes1.aud cnc/desert.mix
  )
  local path source target
  for path in "${required[@]}"; do
    source="$temp_dir/extracted/$path"
    target="$content_dir/$path"
    [ -f "$source" ] || { echo "missing $path in OpenRA quickinstall package" >&2; exit 1; }
    mkdir -p "$(dirname "$target")"
    cp "$source" "$target"
  done
  rm -rf "$temp_dir"
}

if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
  Xvfb "$DISPLAY" -screen 0 "$screen" -ac +extension XTEST +extension RANDR >/tmp/wargames-xvfb.log 2>&1 &
  child_pids+=("$!")
  for _ in $(seq 1 50); do
    xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 && break
    sleep 0.1
  done
fi

resolution="${screen%x*}"
width="${resolution%x*}"
height="${resolution#*x}"
xdotool mousemove "$((width / 2))" "$((height / 2))" >/dev/null 2>&1 || true

if [ -n "${LAYERBRAIN_WARGAMES_HOST_STREAM_URL:-}" ]; then
  ffmpeg \
    -hide_banner \
    -loglevel warning \
    -f x11grab \
    -draw_mouse 1 \
    -framerate "${LAYERBRAIN_WARGAMES_STREAM_FPS:-30}" \
    -video_size "$resolution" \
    -i "$DISPLAY" \
    -codec:v mpeg1video \
    -q:v 2 \
    -bf 0 \
    -f mpegts \
    "$LAYERBRAIN_WARGAMES_HOST_STREAM_URL" >/tmp/wargames-stream.log 2>&1 &
  child_pids+=("$!")
fi

if [ "${LAYERBRAIN_WARGAMES_BOOTSTRAP_OPENRA:-1}" = "1" ] && [ -n "${LAYERBRAIN_WARGAMES_REDALERT_OPENRA_ROOT:-}" ]; then
  openra_root="$LAYERBRAIN_WARGAMES_REDALERT_OPENRA_ROOT"
  if [ -f "$openra_root/Makefile" ] && [ -x "$openra_root/launch-game.sh" ]; then
    platform="linux-x64"
    if [ "$(uname -m)" = "aarch64" ]; then
      platform="linux-arm64"
    fi
    probe_source="$openra_root/OpenRA.Mods.Common/Traits/World/WarGames/WarGamesStateExport.cs"
    probe_rules="$openra_root/mods/ra/rules/wargames-state-export.yaml"
    probe_assembly="$openra_root/bin/OpenRA.Mods.Common.dll"
    if ! file "$openra_root/bin/OpenRA" 2>/dev/null | grep -q 'ELF' \
      || [ ! -f "$probe_source" ] \
      || [ ! -f "$probe_rules" ] \
      || [ ! -f "$probe_assembly" ]; then
      TARGETPLATFORM="$platform" "$script_dir/install_probe.sh" "$openra_root"
    fi
  fi
fi

if [ "${LAYERBRAIN_WARGAMES_BOOTSTRAP_RA_CONTENT:-1}" = "1" ] \
  && [[ " $* " != *" --game flightgear "* ]] \
  && [[ " $* " != *" --game supertuxkart "* ]]; then
  install_ra_quick_content
fi

if [ "$#" -eq 0 ]; then
  exec bash
fi

exec "$@"
