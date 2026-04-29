from __future__ import annotations

import os
from dataclasses import dataclass

from wargames.core.config import WarGamesConfig


@dataclass(frozen=True)
class FreeCivConfig(WarGamesConfig):
    server_binary: str | None = None
    client_binary: str | None = None
    root: str | None = None
    window_size: tuple[int, int] = (1280, 720)
    missions_dir: str = "scenarios/freeciv/missions"
    server_host: str = "127.0.0.1"
    server_port: int = 5556
    save_dir: str | None = None
    startup_dir: str = "/tmp/wargames/freeciv"
    action_settle_seconds: float = 0.25
    snapshot_timeout: float = 10.0
    step_timeout: float = 60.0

    @classmethod
    def from_env(cls) -> "FreeCivConfig":
        base = WarGamesConfig.from_env_prefix("LAYERBRAIN_WARGAMES_").__dict__
        if "LAYERBRAIN_WARGAMES_STEP_TIMEOUT" not in os.environ:
            base["step_timeout"] = cls().step_timeout
        game_values: dict[str, object] = {}
        mapping = {
            "server_binary": "LAYERBRAIN_WARGAMES_FREECIV_SERVER_BINARY",
            "client_binary": "LAYERBRAIN_WARGAMES_FREECIV_CLIENT_BINARY",
            "root": "LAYERBRAIN_WARGAMES_FREECIV_ROOT",
            "window_size": "LAYERBRAIN_WARGAMES_FREECIV_WINDOW_SIZE",
            "missions_dir": "LAYERBRAIN_WARGAMES_FREECIV_MISSIONS_DIR",
            "server_host": "LAYERBRAIN_WARGAMES_FREECIV_SERVER_HOST",
            "server_port": "LAYERBRAIN_WARGAMES_FREECIV_SERVER_PORT",
            "save_dir": "LAYERBRAIN_WARGAMES_FREECIV_SAVE_DIR",
            "startup_dir": "LAYERBRAIN_WARGAMES_FREECIV_STARTUP_DIR",
            "action_settle_seconds": "LAYERBRAIN_WARGAMES_FREECIV_ACTION_SETTLE_SECONDS",
            "snapshot_timeout": "LAYERBRAIN_WARGAMES_FREECIV_SNAPSHOT_TIMEOUT",
        }
        for key, env_name in mapping.items():
            value = os.getenv(env_name)
            if value is None:
                continue
            if key == "window_size":
                width, _, height = value.replace("x", ",").partition(",")
                game_values[key] = (int(width.strip()), int(height.strip()))
            elif key == "server_port":
                game_values[key] = int(value)
            elif key in {"action_settle_seconds", "snapshot_timeout"}:
                game_values[key] = float(value)
            else:
                game_values[key] = value
        return cls(**base, **game_values)
