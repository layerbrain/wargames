from __future__ import annotations

import os
from dataclasses import dataclass

from wargames.core.config import WarGamesConfig


@dataclass(frozen=True)
class FlightGearConfig(WarGamesConfig):
    fgfs_binary: str | None = None
    fgfs_root: str | None = None
    window_size: tuple[int, int] = (1280, 720)
    telnet_port: int = 5501
    http_port: int = 5500
    missions_dir: str = "scenarios/flightgear/missions"
    step_timeout: float = 150.0

    @classmethod
    def from_env(cls) -> "FlightGearConfig":
        base = WarGamesConfig.from_env_prefix("LAYERBRAIN_WARGAMES_").__dict__
        if "LAYERBRAIN_WARGAMES_STEP_TIMEOUT" not in os.environ:
            base["step_timeout"] = cls().step_timeout
        game_values: dict[str, object] = {}
        mapping = {
            "fgfs_binary": "LAYERBRAIN_WARGAMES_FLIGHTGEAR_FGFS_BINARY",
            "fgfs_root": "LAYERBRAIN_WARGAMES_FLIGHTGEAR_ROOT",
            "window_size": "LAYERBRAIN_WARGAMES_FLIGHTGEAR_WINDOW_SIZE",
            "telnet_port": "LAYERBRAIN_WARGAMES_FLIGHTGEAR_TELNET_PORT",
            "http_port": "LAYERBRAIN_WARGAMES_FLIGHTGEAR_HTTP_PORT",
            "missions_dir": "LAYERBRAIN_WARGAMES_FLIGHTGEAR_MISSIONS_DIR",
        }
        for key, env_name in mapping.items():
            value = os.getenv(env_name)
            if value is None:
                continue
            if key == "window_size":
                width, _, height = value.replace("x", ",").partition(",")
                game_values[key] = (int(width.strip()), int(height.strip()))
            elif key in {"telnet_port", "http_port"}:
                game_values[key] = int(value)
            else:
                game_values[key] = value
        return cls(**base, **game_values)
