from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from pathlib import Path

from wargames.core.errors import GameNotInstalled
from wargames.games.doom.config import DoomConfig
from wargames.games.doom.missions import DoomMissionSpec, discover_iwads


def locate_doom(config: DoomConfig) -> str:
    candidates = [
        config.binary,
        os.getenv("CHOCOLATE_DOOM_BINARY"),
        _cache_binary(),
        str(Path(config.root) / "build" / "src" / "chocolate-doom") if config.root else None,
        str(Path(config.root) / "chocolate-doom") if config.root else None,
        shutil.which("chocolate-doom"),
        "/usr/games/chocolate-doom",
        "/usr/bin/chocolate-doom",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise GameNotInstalled("Chocolate Doom binary was not found in its Docker runtime")


def locate_iwad(config: DoomConfig, mission: DoomMissionSpec | None = None) -> str:
    if mission is not None and mission.iwad and Path(mission.iwad).exists():
        return mission.iwad
    if config.iwad and Path(config.iwad).exists():
        return config.iwad
    for iwad in discover_iwads(config.root):
        return str(iwad)
    raise GameNotInstalled("Freedoom IWAD was not found in the Doom runtime")


def doom_environment(
    config: DoomConfig, *, state_path: str, display: str | None = None
) -> Mapping[str, str]:
    env: dict[str, str] = {
        "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS": "0",
        "WARGAMES_DOOM_STATE_PATH": state_path,
        "WARGAMES_DOOM_STATE_INTERVAL_TICKS": str(config.state_interval_ticks),
    }
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if cache_dir:
        root = Path(cache_dir).expanduser() / "games" / "doom"
        env["HOME"] = str(root / "home")
        env["XDG_CACHE_HOME"] = str(root / "xdg-cache")
        env["XDG_CONFIG_HOME"] = str(root / "xdg-config")
        env["XDG_DATA_HOME"] = str(root / "xdg-data")
    if display:
        env["DISPLAY"] = display
    return env


def bootstrap_doom(config: DoomConfig) -> None:
    binary = Path(locate_doom(config))
    if not binary.exists():
        raise GameNotInstalled(f"Chocolate Doom binary was not found: {binary}")
    locate_iwad(config)


def doom_command(
    binary: str, mission: DoomMissionSpec, config: DoomConfig, *, seed: int
) -> list[str]:
    width, height = config.window_size
    command = [
        binary,
        "-iwad",
        locate_iwad(config, mission),
        "-skill",
        str(mission.skill),
        "-window",
        "-geometry",
        f"{width}x{height}",
        "-nosound",
        "-nomusic",
        "-nograbmouse",
        "-novert",
        "-extraconfig",
        str(_extra_config_path(seed)),
    ]
    if mission.map.startswith("MAP"):
        command.extend(["-warp", str(mission.map_number)])
    else:
        command.extend(["-warp", str(mission.episode or 1), str(mission.map_number)])
    return command


def _cache_binary() -> str | None:
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if not cache_dir:
        return None
    return str(
        Path(cache_dir) / "games" / "doom" / "chocolate-doom" / "build" / "src" / "chocolate-doom"
    )


def _extra_config_path(seed: int) -> Path:
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    root = Path(cache_dir).expanduser() if cache_dir else Path("/tmp/wargames")
    path = root / "games" / "doom" / "extra-config" / f"seed-{seed}.cfg"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("use_libsamplerate 0\n", encoding="utf-8")
    return path
