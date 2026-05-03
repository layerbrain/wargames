from __future__ import annotations

import os
from dataclasses import dataclass

from wargames.core.config import WarGamesConfig


@dataclass(frozen=True)
class NaevConfig(WarGamesConfig):
    binary: str | None = None
    root: str | None = None
    data_dir: str | None = None
    window_size: tuple[int, int] = (1280, 720)
    missions_dir: str = "scenarios/naev/missions"
    state_interval_ms: int = 250
    step_timeout: float = 60.0

    @classmethod
    def from_env(cls) -> "NaevConfig":
        base = WarGamesConfig.from_env_prefix("LAYERBRAIN_WARGAMES_").__dict__
        if "LAYERBRAIN_WARGAMES_STEP_TIMEOUT" not in os.environ:
            base["step_timeout"] = cls().step_timeout
        game_values: dict[str, object] = {}
        mapping = {
            "binary": "LAYERBRAIN_WARGAMES_NAEV_BINARY",
            "root": "LAYERBRAIN_WARGAMES_NAEV_ROOT",
            "data_dir": "LAYERBRAIN_WARGAMES_NAEV_DATA_DIR",
            "window_size": "LAYERBRAIN_WARGAMES_NAEV_WINDOW_SIZE",
            "missions_dir": "LAYERBRAIN_WARGAMES_NAEV_MISSIONS_DIR",
            "state_interval_ms": "LAYERBRAIN_WARGAMES_NAEV_STATE_INTERVAL_MS",
        }
        for key, env_name in mapping.items():
            value = os.getenv(env_name)
            if value is None:
                continue
            if key == "window_size":
                width, _, height = value.replace("x", ",").partition(",")
                game_values[key] = (int(width.strip()), int(height.strip()))
            elif key == "state_interval_ms":
                game_values[key] = int(value)
            else:
                game_values[key] = value
        return cls(**base, **game_values)
