from __future__ import annotations

import json
import os
import shutil
from collections.abc import Mapping
from pathlib import Path

from wargames.core.errors import GameNotInstalled
from wargames.games.naev.config import NaevConfig
from wargames.games.naev.missions import NaevMissionSpec


def locate_naev(config: NaevConfig) -> str:
    candidates = [
        config.binary,
        os.getenv("NAEV_BINARY"),
        shutil.which("naev"),
        "/usr/games/naev",
        "/usr/bin/naev",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise GameNotInstalled("Naev binary was not found in its Docker runtime")


def locate_runtime_root(config: NaevConfig) -> Path:
    if config.root:
        return Path(config.root).expanduser()
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if cache_dir:
        return Path(cache_dir).expanduser() / "games" / "naev"
    return Path("/tmp/wargames/games/naev")


def locate_data_dir(config: NaevConfig, mission: NaevMissionSpec | None = None) -> str:
    candidates = [
        mission.data_dir if mission is not None else None,
        config.data_dir,
        str(locate_runtime_root(config) / "dat"),
        "/usr/share/naev/dat",
    ]
    for candidate in candidates:
        if candidate and _is_data_dir(Path(candidate).expanduser()):
            return str(Path(candidate).expanduser())
    raise GameNotInstalled("Naev data directory was not found in its Docker runtime")


def prepare_data_dir(config: NaevConfig, mission: NaevMissionSpec | None = None) -> str:
    data_dir = Path(locate_data_dir(config, mission)).expanduser()
    if config.data_dir or (mission is not None and mission.data_dir):
        return str(data_dir)
    target = locate_runtime_root(config) / "dat"
    if data_dir.resolve() == target.resolve():
        return str(target)
    if not _is_data_dir(target):
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(data_dir, target, dirs_exist_ok=True)
    return str(target)


def bootstrap_naev(config: NaevConfig) -> None:
    Path(locate_naev(config))
    prepare_data_dir(config)


def install_state_exporter(data_dir: str | Path, mission: NaevMissionSpec) -> None:
    root = Path(data_dir)
    if not _is_data_dir(root):
        raise GameNotInstalled(f"Naev data directory is missing start.xml/events: {root}")
    events = root / "events"
    events.mkdir(parents=True, exist_ok=True)
    exporter = events / "wargames_state.lua"
    exporter.write_text(_state_exporter_lua(), encoding="utf-8")

    start = events / "start.lua"
    backup = events / "start.lua.wargames-original"
    if start.exists() and not backup.exists():
        shutil.copy2(start, backup)
    start.write_text(_start_lua(mission), encoding="utf-8")


def naev_environment(
    config: NaevConfig,
    *,
    display: str | None = None,
    audio_path: str | None = None,
) -> Mapping[str, str]:
    root = locate_runtime_root(config)
    env: dict[str, str] = {
        "LIBGL_ALWAYS_SOFTWARE": "1",
        "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS": "0",
        "SDL_AUDIODRIVER": "alsa",
        "ALSOFT_DRIVERS": "alsa",
        "ALSA_CONFIG_PATH": _alsa_config(audio_path),
        "HOME": str(root / "home"),
        "XDG_CACHE_HOME": str(root / "xdg-cache"),
        "XDG_CONFIG_HOME": str(root / "xdg-config"),
        "XDG_DATA_HOME": str(root / "xdg-data"),
    }
    for value in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME"):
        Path(env[value]).mkdir(parents=True, exist_ok=True)
    if display:
        env["DISPLAY"] = display
    return env


def naev_command(binary: str, data_dir: str, config: NaevConfig) -> list[str]:
    width, height = config.window_size
    user_dir = locate_runtime_root(config) / "home" / "naev-user"
    shutil.rmtree(user_dir, ignore_errors=True)
    user_dir.mkdir(parents=True, exist_ok=True)
    return [
        binary,
        "-W",
        str(width),
        "-H",
        str(height),
        "-F",
        "60",
        "-d",
        str(user_dir),
        data_dir,
    ]


def _is_data_dir(path: Path) -> bool:
    return (path / "start.xml").exists() and (path / "events").is_dir()


def _alsa_config(audio_path: str | None) -> str:
    suffix = Path(audio_path).stem if audio_path else "null"
    path = Path("/tmp/wargames") / "asound" / f"naev-{suffix}.conf"
    path.parent.mkdir(parents=True, exist_ok=True)
    if audio_path is None:
        path.write_text(
            "\n".join(
                [
                    "pcm.!default { type null }",
                    "ctl.!default { type hw card 0 }",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return str(path)

    Path(audio_path).parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "pcm.wargames_sink { type null }",
                "pcm.wargames_capture {",
                "  type file",
                "  slave.pcm wargames_sink",
                f"  file \"{audio_path}\"",
                "  format raw",
                "}",
                "pcm.!default {",
                "  type plug",
                "  slave {",
                "    pcm wargames_capture",
                "    rate 48000",
                "    channels 2",
                "    format S16_LE",
                "  }",
                "}",
                "ctl.!default { type hw card 0 }",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return str(path)


def _start_lua(mission: NaevMissionSpec) -> str:
    mission_name = json.dumps(mission.mission_name)
    landing_setup = _landing_setup_lua(mission)
    return f"""--[[
<?xml version="1.0" encoding="utf8"?>
<event name="start_event">
 <location>none</location>
</event>
--]]

-- WarGames generated Naev start event.
function name ()
   return "WarGames"
end

function create ()
   player.pilot():rename(name())
   player.pilot():addOutfit("Laser Cannon MK1", 2)
   jump.setKnown("Hakoi", "Eneguoz")
   player.addOutfit("GUI - Brushed")
   player.addOutfit("GUI - Slim")
   player.addOutfit("GUI - Slimv2")
   player.addOutfit("GUI - Legacy")
   wargames_state_start()
{landing_setup}
   hook.timer(1000, "wargames_start_mission")
end

function wargames_start_mission ()
   local ok, accepted = naev.missionStart({mission_name})
   print("WARGAMES_MISSION_START " .. tostring(ok) .. " " .. tostring(accepted))
end
{_inline_state_exporter_lua()}
"""


def _landing_setup_lua(mission: NaevMissionSpec) -> str:
    if mission.native_location.lower() not in {"bar", "computer"}:
        return ""
    return """   local wargames_spob = spob.get("Bolero")
   if wargames_spob then
      player.land(wargames_spob)
   end"""


def _inline_state_exporter_lua() -> str:
    return """
local wargames_state = {
   tick = 0,
   completed_count = 0,
   failed_count = 0,
   last_completed = "",
   last_failed = "",
}

local function wargames_esc (value)
   local text = tostring(value or "")
   text = text:gsub("\\\\", "\\\\\\\\"):gsub('"', '\\\\"'):gsub("\\n", "\\\\n"):gsub("\\r", "\\\\r")
   return '"' .. text .. '"'
end

local function wargames_num (value)
   value = tonumber(value)
   if value == nil or value ~= value or value == math.huge or value == -math.huge then
      return "null"
   end
   return tostring(value)
end

local function wargames_bool (value)
   if value then
      return "true"
   end
   return "false"
end

local function wargames_safe (fn, default)
   local ok, value = pcall(fn)
   if ok then
      return value
   end
   return default
end

local function wargames_vx (value)
   if value == nil then
      return nil
   end
   local ok, result = pcall(function () return value:x() end)
   if ok and type(result) == "number" then
      return result
   end
   ok, result = pcall(function () return value.x end)
   if ok and type(result) == "number" then
      return result
   end
   ok, result = pcall(function () return value[1] end)
   if ok and type(result) == "number" then
      return result
   end
   return nil
end

local function wargames_vy (value)
   if value == nil then
      return nil
   end
   local ok, result = pcall(function () return value:y() end)
   if ok and type(result) == "number" then
      return result
   end
   ok, result = pcall(function () return value.y end)
   if ok and type(result) == "number" then
      return result
   end
   ok, result = pcall(function () return value[2] end)
   if ok and type(result) == "number" then
      return result
   end
   return nil
end

local function wargames_vmod (value)
   if value == nil then
      return nil
   end
   local ok, result = pcall(function () return value:mod() end)
   if ok and type(result) == "number" then
      return result
   end
   local x, y = wargames_vx(value), wargames_vy(value)
   if x ~= nil and y ~= nil then
      return math.sqrt(x * x + y * y)
   end
   return nil
end

function wargames_mission_done (mission)
   wargames_state.completed_count = wargames_state.completed_count + 1
   wargames_state.last_completed = wargames_safe(function () return mission:name() end, "")
   wargames_emit_state()
end

function wargames_state_start ()
   if hook.mission_done then
      hook.mission_done("wargames_mission_done")
   end
   hook.land("wargames_emit_state")
   hook.takeoff("wargames_emit_state")
   hook.enter("wargames_emit_state")
   hook.jumpin("wargames_emit_state")
   hook.jumpout("wargames_emit_state")
   hook.timer(250, "wargames_timer_emit")
   wargames_emit_state()
end

function wargames_timer_emit ()
   wargames_emit_state()
   hook.timer(250, "wargames_timer_emit")
end

function wargames_emit_state ()
   wargames_state.tick = wargames_state.tick + 1
   local pilot = wargames_safe(function () return player.pilot() end, nil)
   local position = pilot and wargames_safe(function () return pilot:pos() end, nil) or nil
   local velocity = pilot and wargames_safe(function () return pilot:vel() end, nil) or nil
   local target = pilot and wargames_safe(function () return pilot:target() end, nil) or nil
   local armour, shield, stress, disabled = nil, nil, nil, false
   if pilot then
      local ok, a, s, st, d = pcall(function () return pilot:health() end)
      if ok then
         armour, shield, stress, disabled = a, s, st, d
      end
   end
   local target_name = target and wargames_safe(function () return target:name() end, "") or ""
   local target_distance = nil
   if pilot and target then
      target_distance = wargames_safe(function () return pilot:pos():dist(target:pos()) end, nil)
   end
   local current_system = wargames_safe(function () return system.cur():name() end, "")
   local landed = wargames_safe(function () return player.isLanded() end, false)
   local jumps = wargames_safe(function () return player.jumps() end, 0)
   local credits = wargames_safe(function () return player.credits() end, 0)
   local wealth = wargames_safe(function () return player.wealth() end, credits)
   local fuel = pilot and wargames_safe(function () return pilot:fuel() end, nil) or nil
   local energy = pilot and wargames_safe(function () return pilot:energy() end, nil) or nil
   local direction = pilot and wargames_safe(function () return pilot:dir() end, nil) or nil
   local ship = pilot and wargames_safe(function () return pilot:ship():name() end, "") or ""

   print("WARGAMES_STATE " ..
      "{"
      .. '"tick":' .. tostring(wargames_state.tick)
      .. ',"mission":{'
      .. '"name":' .. wargames_esc(wargames_state.last_completed)
      .. ',"finished":' .. wargames_bool(wargames_state.completed_count > 0)
      .. ',"failed":' .. wargames_bool(wargames_state.failed_count > 0)
      .. ',"completed_count":' .. tostring(wargames_state.completed_count)
      .. ',"failed_count":' .. tostring(wargames_state.failed_count)
      .. ',"last_completed":' .. wargames_esc(wargames_state.last_completed)
      .. ',"last_failed":' .. wargames_esc(wargames_state.last_failed)
      .. '},"player":{'
      .. '"name":' .. wargames_esc(wargames_safe(function () return player.name() end, ""))
      .. ',"ship":' .. wargames_esc(ship)
      .. ',"system":' .. wargames_esc(current_system)
      .. ',"landed":' .. wargames_bool(landed)
      .. ',"x":' .. wargames_num(wargames_vx(position))
      .. ',"y":' .. wargames_num(wargames_vy(position))
      .. ',"vx":' .. wargames_num(wargames_vx(velocity))
      .. ',"vy":' .. wargames_num(wargames_vy(velocity))
      .. ',"speed":' .. wargames_num(wargames_vmod(velocity))
      .. ',"direction":' .. wargames_num(direction)
      .. ',"credits":' .. wargames_num(credits)
      .. ',"wealth":' .. wargames_num(wealth)
      .. ',"fuel":' .. wargames_num(fuel)
      .. ',"jumps":' .. tostring(tonumber(jumps) or 0)
      .. ',"armour":' .. wargames_num(armour)
      .. ',"shield":' .. wargames_num(shield)
      .. ',"stress":' .. wargames_num(stress)
      .. ',"disabled":' .. wargames_bool(disabled)
      .. ',"energy":' .. wargames_num(energy)
      .. ',"target":' .. wargames_esc(target_name)
      .. ',"target_distance":' .. wargames_num(target_distance)
      .. '},"navigation":{'
      .. '"system":' .. wargames_esc(current_system)
      .. ',"landed":' .. wargames_bool(landed)
      .. ',"jumps_available":' .. tostring(tonumber(jumps) or 0)
      .. ',"autonav":' .. wargames_bool(wargames_safe(function () return player.autonav() end, false))
      .. "}}")
end
"""


def _state_exporter_lua() -> str:
    return """--[[
<?xml version="1.0" encoding="utf8"?>
<event name="WarGames State Export">
 <trigger>none</trigger>
</event>
--]]

local state = {
   tick = 0,
   completed_count = 0,
   failed_count = 0,
   last_completed = "",
   last_failed = "",
}

local function esc (value)
   local text = tostring(value or "")
   text = text:gsub("\\\\", "\\\\\\\\"):gsub('"', '\\\\"'):gsub("\\n", "\\\\n"):gsub("\\r", "\\\\r")
   return '"' .. text .. '"'
end

local function num (value)
   value = tonumber(value)
   if value == nil or value ~= value or value == math.huge or value == -math.huge then
      return "null"
   end
   return tostring(value)
end

local function bool (value)
   if value then
      return "true"
   end
   return "false"
end

local function safe (fn, default)
   local ok, value = pcall(fn)
   if ok then
      return value
   end
   return default
end

local function vx (value)
   if value == nil then
      return nil
   end
   local ok, result = pcall(function () return value:x() end)
   if ok and type(result) == "number" then
      return result
   end
   ok, result = pcall(function () return value.x end)
   if ok and type(result) == "number" then
      return result
   end
   ok, result = pcall(function () return value[1] end)
   if ok and type(result) == "number" then
      return result
   end
   return nil
end

local function vy (value)
   if value == nil then
      return nil
   end
   local ok, result = pcall(function () return value:y() end)
   if ok and type(result) == "number" then
      return result
   end
   ok, result = pcall(function () return value.y end)
   if ok and type(result) == "number" then
      return result
   end
   ok, result = pcall(function () return value[2] end)
   if ok and type(result) == "number" then
      return result
   end
   return nil
end

local function vmod (value)
   if value == nil then
      return nil
   end
   local ok, result = pcall(function () return value:mod() end)
   if ok and type(result) == "number" then
      return result
   end
   local x, y = vx(value), vy(value)
   if x ~= nil and y ~= nil then
      return math.sqrt(x * x + y * y)
   end
   return nil
end

local function mission_done (mission)
   state.completed_count = state.completed_count + 1
   state.last_completed = safe(function () return mission:name() end, "")
   emit()
end

function create ()
   if hook.mission_done then
      hook.mission_done("mission_done")
   end
   hook.land("emit")
   hook.takeoff("emit")
   hook.enter("emit")
   hook.jumpin("emit")
   hook.jumpout("emit")
   hook.timer(250, "timer_emit")
   emit()
end

function timer_emit ()
   emit()
   hook.timer(250, "timer_emit")
end

function emit ()
   state.tick = state.tick + 1
   local pilot = safe(function () return player.pilot() end, nil)
   local position = pilot and safe(function () return pilot:pos() end, nil) or nil
   local velocity = pilot and safe(function () return pilot:vel() end, nil) or nil
   local target = pilot and safe(function () return pilot:target() end, nil) or nil

   local armour, shield, stress, disabled = nil, nil, nil, false
   if pilot then
      local ok, a, s, st, d = pcall(function () return pilot:health() end)
      if ok then
         armour, shield, stress, disabled = a, s, st, d
      end
   end

   local target_name = target and safe(function () return target:name() end, "") or ""
   local target_distance = nil
   if pilot and target then
      target_distance = safe(function () return pilot:pos():dist(target:pos()) end, nil)
   end

   local system = safe(function () return system.cur():name() end, "")
   local landed = safe(function () return player.isLanded() end, false)
   local jumps = safe(function () return player.jumps() end, 0)
   local credits = safe(function () return player.credits() end, 0)
   local wealth = safe(function () return player.wealth() end, credits)
   local fuel = pilot and safe(function () return pilot:fuel() end, nil) or nil
   local energy = pilot and safe(function () return pilot:energy() end, nil) or nil
   local direction = pilot and safe(function () return pilot:dir() end, nil) or nil
   local ship = pilot and safe(function () return pilot:ship():name() end, "") or ""

   print("WARGAMES_STATE " ..
      "{"
      .. '"tick":' .. tostring(state.tick)
      .. ',"mission":{'
      .. '"name":' .. esc(state.last_completed)
      .. ',"finished":' .. bool(state.completed_count > 0)
      .. ',"failed":' .. bool(state.failed_count > 0)
      .. ',"completed_count":' .. tostring(state.completed_count)
      .. ',"failed_count":' .. tostring(state.failed_count)
      .. ',"last_completed":' .. esc(state.last_completed)
      .. ',"last_failed":' .. esc(state.last_failed)
      .. '},"player":{'
      .. '"name":' .. esc(safe(function () return player.name() end, ""))
      .. ',"ship":' .. esc(ship)
      .. ',"system":' .. esc(system)
      .. ',"landed":' .. bool(landed)
      .. ',"x":' .. num(vx(position))
      .. ',"y":' .. num(vy(position))
      .. ',"vx":' .. num(vx(velocity))
      .. ',"vy":' .. num(vy(velocity))
      .. ',"speed":' .. num(vmod(velocity))
      .. ',"direction":' .. num(direction)
      .. ',"credits":' .. num(credits)
      .. ',"wealth":' .. num(wealth)
      .. ',"fuel":' .. num(fuel)
      .. ',"jumps":' .. tostring(tonumber(jumps) or 0)
      .. ',"armour":' .. num(armour)
      .. ',"shield":' .. num(shield)
      .. ',"stress":' .. num(stress)
      .. ',"disabled":' .. bool(disabled)
      .. ',"energy":' .. num(energy)
      .. ',"target":' .. esc(target_name)
      .. ',"target_distance":' .. num(target_distance)
      .. '},"navigation":{'
      .. '"system":' .. esc(system)
      .. ',"landed":' .. bool(landed)
      .. ',"jumps_available":' .. tostring(tonumber(jumps) or 0)
      .. ',"autonav":' .. bool(safe(function () return player.autonav() end, false))
      .. "}}")
end
"""
