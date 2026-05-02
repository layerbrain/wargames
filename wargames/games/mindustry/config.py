from __future__ import annotations

import os
from dataclasses import dataclass

from wargames.core.config import WarGamesConfig


@dataclass(frozen=True)
class MindustryConfig(WarGamesConfig):
    client_jar: str | None = None
    server_jar: str | None = None
    root: str | None = None
    window_size: tuple[int, int] = (1280, 720)
    missions_dir: str = "scenarios/mindustry/missions"
    state_interval_ticks: int = 30
    action_settle_seconds: float = 0.25
    step_timeout: float = 60.0

    @classmethod
    def from_env(cls) -> "MindustryConfig":
        base = WarGamesConfig.from_env_prefix("LAYERBRAIN_WARGAMES_").__dict__
        if "LAYERBRAIN_WARGAMES_STEP_TIMEOUT" not in os.environ:
            base["step_timeout"] = cls().step_timeout
        game_values: dict[str, object] = {}
        mapping = {
            "client_jar": "LAYERBRAIN_WARGAMES_MINDUSTRY_CLIENT_JAR",
            "server_jar": "LAYERBRAIN_WARGAMES_MINDUSTRY_SERVER_JAR",
            "root": "LAYERBRAIN_WARGAMES_MINDUSTRY_ROOT",
            "window_size": "LAYERBRAIN_WARGAMES_MINDUSTRY_WINDOW_SIZE",
            "missions_dir": "LAYERBRAIN_WARGAMES_MINDUSTRY_MISSIONS_DIR",
            "state_interval_ticks": "LAYERBRAIN_WARGAMES_MINDUSTRY_STATE_INTERVAL_TICKS",
            "action_settle_seconds": "LAYERBRAIN_WARGAMES_MINDUSTRY_ACTION_SETTLE_SECONDS",
        }
        for key, env_name in mapping.items():
            value = os.getenv(env_name)
            if value is None:
                continue
            if key == "window_size":
                width, _, height = value.replace("x", ",").partition(",")
                game_values[key] = (int(width.strip()), int(height.strip()))
            elif key == "state_interval_ticks":
                game_values[key] = int(value)
            elif key == "action_settle_seconds":
                game_values[key] = float(value)
            else:
                game_values[key] = value
        return cls(**base, **game_values)
