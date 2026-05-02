from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from pathlib import Path

from wargames.core.errors import GameNotInstalled
from wargames.games.supertux.config import SuperTuxConfig
from wargames.games.supertux.missions import SuperTuxMissionSpec


def locate_supertux(config: SuperTuxConfig) -> str:
    candidates = [
        config.binary,
        os.getenv("SUPERTUX2_BINARY"),
        _cache_binary(),
        str(Path(config.root) / "build" / "supertux2") if config.root else None,
        str(Path(config.root) / "cmake_build" / "supertux2") if config.root else None,
        str(Path(config.root) / "supertux2") if config.root else None,
        str(Path(config.root) / "bin" / "supertux2") if config.root else None,
        shutil.which("supertux2"),
        "/usr/games/supertux2",
        "/usr/bin/supertux2",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise GameNotInstalled("SuperTux binary was not found in its Docker runtime")


def locate_data_dir(config: SuperTuxConfig, mission: SuperTuxMissionSpec | None = None) -> str:
    candidates = [
        mission.data_dir if mission is not None else None,
        config.data_dir,
        str(Path(config.root) / "data") if config.root else None,
        str(Path(config.root) / "share" / "games" / "supertux2") if config.root else None,
        "/usr/share/games/supertux2",
    ]
    for candidate in candidates:
        if candidate and (Path(candidate) / "levels").exists():
            return candidate
    raise GameNotInstalled("SuperTux data directory was not found in its Docker runtime")


def locate_level_file(config: SuperTuxConfig, mission: SuperTuxMissionSpec) -> str:
    raw = Path(mission.level_file)
    if raw.is_absolute() and raw.exists():
        return str(raw)
    candidate = Path(locate_data_dir(config, mission)) / raw
    if candidate.exists():
        return str(candidate)
    raise GameNotInstalled(f"SuperTux level file was not found: {mission.level_file}")


def supertux_environment(
    config: SuperTuxConfig, *, state_path: str, display: str | None = None
) -> Mapping[str, str]:
    env: dict[str, str] = {
        "LIBGL_ALWAYS_SOFTWARE": "1",
        "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS": "0",
        "WARGAMES_SUPERTUX_STATE_PATH": state_path,
        "WARGAMES_SUPERTUX_STATE_INTERVAL_TICKS": str(config.state_interval_ticks),
    }
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if cache_dir:
        root = Path(cache_dir).expanduser() / "games" / "supertux"
        env["HOME"] = str(root / "home")
        env["XDG_CACHE_HOME"] = str(root / "xdg-cache")
        env["XDG_CONFIG_HOME"] = str(root / "xdg-config")
        env["XDG_DATA_HOME"] = str(root / "xdg-data")
        env["SUPERTUX2_USER_DIR"] = str(root / "user")
    if display:
        env["DISPLAY"] = display
    return env


def bootstrap_supertux(config: SuperTuxConfig) -> None:
    binary = Path(locate_supertux(config))
    if not binary.exists():
        raise GameNotInstalled(f"SuperTux binary was not found: {binary}")
    locate_data_dir(config)


def supertux_command(
    binary: str, mission: SuperTuxMissionSpec, config: SuperTuxConfig, *, seed: int
) -> list[str]:
    width, height = config.window_size
    return [
        binary,
        "--window",
        "--geometry",
        f"{width}x{height}",
        "--renderer",
        "sdl",
        "--disable-sound",
        "--disable-music",
        "--datadir",
        locate_data_dir(config, mission),
        "--userdir",
        _user_dir(seed),
        locate_level_file(config, mission),
    ]


def _cache_binary() -> str | None:
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if not cache_dir:
        return None
    return str(Path(cache_dir) / "games" / "supertux" / "supertux" / "build" / "supertux2")


def _user_dir(seed: int) -> str:
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    root = Path(cache_dir).expanduser() if cache_dir else Path("/tmp/wargames")
    path = root / "games" / "supertux" / "userdirs" / f"seed-{seed}"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)
