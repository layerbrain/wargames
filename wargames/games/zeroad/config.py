from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from wargames.core.config import WarGamesConfig


@dataclass(frozen=True)
class ZeroADConfig(WarGamesConfig):
    binary: str | None = None
    root: str | None = None
    window_size: tuple[int, int] = (1280, 720)
    missions_dir: str = "scenarios/zeroad/missions"
    rl_host: str = "127.0.0.1"
    rl_port: int = 6000
    game_speed: float = 1.0
    step_timeout: float = 60.0

    @classmethod
    def from_env(cls) -> "ZeroADConfig":
        base = WarGamesConfig.from_env_prefix("LAYERBRAIN_WARGAMES_").__dict__
        if "LAYERBRAIN_WARGAMES_STEP_TIMEOUT" not in os.environ:
            base["step_timeout"] = cls().step_timeout
        game_values: dict[str, object] = {}
        mapping = {
            "binary": "LAYERBRAIN_WARGAMES_ZEROAD_BINARY",
            "root": "LAYERBRAIN_WARGAMES_ZEROAD_ROOT",
            "window_size": "LAYERBRAIN_WARGAMES_ZEROAD_WINDOW_SIZE",
            "missions_dir": "LAYERBRAIN_WARGAMES_ZEROAD_MISSIONS_DIR",
            "rl_host": "LAYERBRAIN_WARGAMES_ZEROAD_RL_HOST",
            "rl_port": "LAYERBRAIN_WARGAMES_ZEROAD_RL_PORT",
            "game_speed": "LAYERBRAIN_WARGAMES_ZEROAD_GAME_SPEED",
        }
        for key, env_name in mapping.items():
            value = os.getenv(env_name)
            if value is None:
                continue
            if key == "window_size":
                width, _, height = value.replace("x", ",").partition(",")
                game_values[key] = (int(width.strip()), int(height.strip()))
            elif key == "rl_port":
                game_values[key] = int(value)
            elif key == "game_speed":
                game_values[key] = float(value)
            else:
                game_values[key] = value
        install = _cached_install_manifest()
        if "binary" not in game_values:
            binary = install.get("binary")
            if isinstance(binary, str) and binary:
                game_values["binary"] = binary
        if "root" not in game_values:
            root = install.get("root")
            if isinstance(root, str) and root:
                game_values["root"] = root
        return cls(**base, **game_values)


def _cached_install_manifest() -> dict[str, object]:
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if not cache_dir:
        return {}
    manifest = Path(cache_dir).expanduser() / "games" / "zeroad" / "install.json"
    if not manifest.exists():
        return {}
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}
