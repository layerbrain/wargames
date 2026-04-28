from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from pathlib import Path

from wargames.core.errors import GameNotInstalled
from wargames.games.supertuxkart.config import SuperTuxKartConfig
from wargames.games.supertuxkart.missions import SuperTuxKartMissionSpec


def locate_supertuxkart(config: SuperTuxKartConfig) -> str:
    candidates = [
        config.binary,
        os.getenv("SUPERTUXKART_BINARY"),
        _cache_binary(),
        str(Path(config.root) / "bin" / "supertuxkart") if config.root else None,
        shutil.which("supertuxkart"),
        "/usr/games/supertuxkart",
        "/usr/bin/supertuxkart",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise GameNotInstalled("SuperTuxKart binary was not found in its Docker runtime")


def supertuxkart_environment(
    config: SuperTuxKartConfig, *, state_path: str, display: str | None = None
) -> Mapping[str, str]:
    env: dict[str, str] = {
        "IRR_DEVICE_TYPE": "x11",
        "LIBGL_ALWAYS_SOFTWARE": "1",
        "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS": "0",
        "SUPERTUXKART_DATADIR": config.root or "/usr/share/games/supertuxkart",
    }
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if cache_dir:
        root = Path(cache_dir).expanduser() / "games" / "supertuxkart"
        env["HOME"] = str(root / "home")
        env["XDG_CACHE_HOME"] = str(root / "xdg-cache")
        env["XDG_CONFIG_HOME"] = str(root / "xdg-config")
        env["XDG_DATA_HOME"] = str(root / "xdg-data")
    if display:
        env["DISPLAY"] = display
    env["WARGAMES_STK_STATE_PATH"] = state_path
    env["WARGAMES_STK_STATE_INTERVAL_TICKS"] = str(config.state_interval_ticks)
    return env


def _cache_binary() -> str | None:
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if not cache_dir:
        return None
    return str(
        Path(cache_dir)
        / "games"
        / "supertuxkart"
        / "stk-code"
        / "cmake_build"
        / "bin"
        / "supertuxkart"
    )


def bootstrap_supertuxkart(config: SuperTuxKartConfig) -> None:
    binary = Path(locate_supertuxkart(config))
    if not binary.exists():
        raise GameNotInstalled(f"SuperTuxKart binary was not found: {binary}")


def supertuxkart_command(
    binary: str, mission: SuperTuxKartMissionSpec, config: SuperTuxKartConfig, *, seed: int
) -> list[str]:
    width, height = config.window_size
    command = [
        binary,
        "--race-now",
        f"--track={mission.track}",
        f"--laps={mission.laps}",
        f"--numkarts={mission.num_karts}",
        f"--kart={mission.kart}",
        "--mode=0",
        f"--difficulty={mission.native_difficulty or '1'}",
        f"--screensize={width}x{height}",
        "--windowed",
        "--unlock-all",
        "--disable-addon-karts",
        "--disable-addon-tracks",
        "--disable-glow",
        "--disable-bloom",
        "--disable-light-shaft",
        "--disable-motion-blur",
        "--disable-mlaa",
        "--disable-ssao",
        "--disable-hd-textures",
        "--render-driver=gl",
        f"--seed={seed}",
    ]
    if mission.reverse:
        command.append("--reverse")
    return command
