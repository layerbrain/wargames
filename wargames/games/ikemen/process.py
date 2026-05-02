from __future__ import annotations

import json
import os
import shutil
from collections.abc import Mapping
from pathlib import Path

from wargames.core.errors import GameNotInstalled, ProbeNotInstalled
from wargames.games.ikemen.config import IkemenConfig
from wargames.games.ikemen.missions import IkemenMissionSpec


def locate_ikemen(config: IkemenConfig) -> str:
    candidates = [
        config.binary,
        os.getenv("IKEMEN_BINARY"),
        _cache_binary(),
        str(Path(config.root) / "Ikemen_GO_Linux") if config.root else None,
        str(Path(config.root) / "Ikemen_GO") if config.root else None,
        shutil.which("Ikemen_GO_Linux"),
        shutil.which("Ikemen_GO"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise GameNotInstalled("IKEMEN GO binary was not found in its Docker runtime")


def locate_root(config: IkemenConfig) -> Path:
    if config.root:
        return Path(config.root).expanduser()
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if cache_dir:
        return Path(cache_dir).expanduser() / "games" / "ikemen"
    return Path("/tmp/wargames/games/ikemen")


def exporter_path() -> Path:
    return Path(__file__).resolve().parent / "lua" / "wargames_state_export.lua"


def ikemen_environment(
    config: IkemenConfig, *, state_path: str, display: str | None = None
) -> Mapping[str, str]:
    root = locate_root(config)
    env = {
        "ALSOFT_DRIVERS": "null",
        "LIBGL_ALWAYS_SOFTWARE": "1",
        "MESA_GL_VERSION_OVERRIDE": "3.3",
        "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS": "0",
        "WARGAMES_IKEMEN_STATE_PATH": state_path,
        "WARGAMES_IKEMEN_STATE_INTERVAL_TICKS": str(config.state_interval_ticks),
        "WARGAMES_IKEMEN_EXPORTER_PATH": str(exporter_path()),
        "HOME": str(root / "home"),
        "XDG_DATA_HOME": str(root / "home" / ".local" / "share"),
        "XDG_CONFIG_HOME": str(root / "home" / ".config"),
        "XDG_CACHE_HOME": str(root / "home" / ".cache"),
    }
    if display:
        env["DISPLAY"] = display
    return env


def bootstrap_ikemen(config: IkemenConfig) -> None:
    binary = Path(locate_ikemen(config))
    if not binary.exists():
        raise GameNotInstalled(f"IKEMEN GO binary was not found: {binary}")
    root = locate_root(config)
    required = (root / "data" / "system.def", root / "chars" / "kfm", root / "stages")
    for path in required:
        if not path.exists():
            raise GameNotInstalled(f"IKEMEN GO runtime content is missing: {path}")
    if not exporter_path().exists():
        raise ProbeNotInstalled("IKEMEN GO WarGames Lua state exporter is missing")


def ikemen_command(
    binary: str, mission: IkemenMissionSpec, config: IkemenConfig, *, config_path: Path
) -> list[str]:
    del config
    return [
        binary,
        "-config",
        str(config_path),
        "-windowed",
        "-nosound",
        "-p1",
        mission.p1,
        "-p2",
        mission.p2,
        "-p2.ai",
        str(mission.ai_level),
        "-p1.ai",
        "0",
        "-p1.life",
        "1000",
        "-p2.life",
        "1000",
        "-s",
        mission.stage,
        "-rounds",
        str(mission.rounds),
        "-time",
        str(mission.round_time),
        "-ailevel",
        str(mission.ai_level),
    ]


def write_config(config_path: Path, config: IkemenConfig) -> Path:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = config.window_size
    payload = {
        "CommonLua": [
            "if wargames_state_export == nil then "
            "dofile(os.getenv('WARGAMES_IKEMEN_EXPORTER_PATH')) end; "
            "loop(); wargames_state_export()"
        ],
        "Fullscreen": False,
        "GameWidth": width,
        "GameHeight": height,
        "WindowTitle": "Ikemen GO",
        "VolumeMaster": 0,
        "VolumeBgm": 0,
        "VolumeSfx": 0,
    }
    config_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return config_path


def _cache_binary() -> str | None:
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if not cache_dir:
        return None
    return str(Path(cache_dir) / "games" / "ikemen" / "Ikemen_GO_Linux")
