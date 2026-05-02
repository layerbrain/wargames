from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from wargames.core.errors import GameNotInstalled, ProbeNotInstalled
from wargames.games.mindustry.config import MindustryConfig
from wargames.games.mindustry.missions import MindustryMissionSpec


def locate_client_jar(config: MindustryConfig) -> str:
    candidates = [
        config.client_jar,
        os.getenv("MINDUSTRY_CLIENT_JAR"),
        _cache_client_jar(),
        str(Path(config.root) / "Mindustry.jar") if config.root else None,
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise GameNotInstalled("Mindustry.jar was not found in its Docker runtime")


def locate_server_jar(config: MindustryConfig) -> str:
    candidates = [
        config.server_jar,
        os.getenv("MINDUSTRY_SERVER_JAR"),
        _cache_server_jar(),
        str(Path(config.root) / "server-release.jar") if config.root else None,
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise GameNotInstalled("Mindustry server-release.jar was not found in its Docker runtime")


def locate_root(config: MindustryConfig) -> Path:
    if config.root:
        return Path(config.root).expanduser()
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if cache_dir:
        return Path(cache_dir).expanduser() / "games" / "mindustry"
    return Path("/tmp/wargames/games/mindustry")


def locate_plugin(config: MindustryConfig) -> Path:
    plugin = _mod_dir(config) / "wargames-mindustry-state.jar"
    if plugin.exists():
        return plugin
    raise ProbeNotInstalled(
        "Mindustry must be installed with the WarGames state plugin. "
        "Run `wargames install --game mindustry` inside the WarGames runtime."
    )


def mindustry_environment(
    config: MindustryConfig,
    *,
    state_path: str,
    mission: MindustryMissionSpec,
    display: str | None = None,
) -> Mapping[str, str]:
    root = locate_root(config)
    env = {
        "LIBGL_ALWAYS_SOFTWARE": "1",
        "MESA_GL_VERSION_OVERRIDE": "3.3",
        "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS": "0",
        "WARGAMES_MINDUSTRY_STATE_PATH": state_path,
        "WARGAMES_MINDUSTRY_STATE_INTERVAL_TICKS": str(config.state_interval_ticks),
        "WARGAMES_MINDUSTRY_AUTO_MAP": mission.map_name,
        "WARGAMES_MINDUSTRY_AUTO_MODE": mission.mode,
        "WARGAMES_MINDUSTRY_WIN_WAVE": str(mission.win_wave),
        "HOME": str(root / "home"),
        "XDG_DATA_HOME": str(root / "home" / ".local" / "share"),
        "XDG_CONFIG_HOME": str(root / "home" / ".config"),
        "XDG_CACHE_HOME": str(root / "home" / ".cache"),
    }
    if display:
        env["DISPLAY"] = display
    return env


def bootstrap_mindustry(config: MindustryConfig) -> None:
    client = Path(locate_client_jar(config))
    if not client.exists():
        raise GameNotInstalled(f"Mindustry client jar was not found: {client}")
    server = Path(locate_server_jar(config))
    if not server.exists():
        raise GameNotInstalled(f"Mindustry server jar was not found: {server}")
    locate_plugin(config)


def mindustry_command(client_jar: str, mission: MindustryMissionSpec) -> list[str]:
    del mission
    return ["java", "-Djava.awt.headless=false", "-jar", client_jar]


def _cache_server_jar() -> str | None:
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if not cache_dir:
        return None
    return str(Path(cache_dir) / "games" / "mindustry" / "server-release.jar")


def _cache_client_jar() -> str | None:
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if not cache_dir:
        return None
    return str(Path(cache_dir) / "games" / "mindustry" / "Mindustry.jar")


def _mod_dir(config: MindustryConfig) -> Path:
    return locate_root(config) / "home" / ".local" / "share" / "Mindustry" / "mods"
