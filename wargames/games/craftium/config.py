from __future__ import annotations

import os
from dataclasses import dataclass

from wargames.core.config import WarGamesConfig


@dataclass(frozen=True)
class CraftiumConfig(WarGamesConfig):
    root: str | None = None
    missions_dir: str = "scenarios/craftium/missions"
    run_dir_prefix: str = "/tmp/wargames/craftium-runs"
    enable_voxel_obs: bool = True
    wait_step_ms: int = 100
    max_wait_steps: int = 30
    step_timeout: float = 120.0

    @classmethod
    def from_env(cls) -> "CraftiumConfig":
        base = WarGamesConfig.from_env_prefix("LAYERBRAIN_WARGAMES_").__dict__
        if "LAYERBRAIN_WARGAMES_STEP_TIMEOUT" not in os.environ:
            base["step_timeout"] = cls().step_timeout
        game_values: dict[str, object] = {}
        mapping = {
            "root": "LAYERBRAIN_WARGAMES_CRAFTIUM_ROOT",
            "missions_dir": "LAYERBRAIN_WARGAMES_CRAFTIUM_MISSIONS_DIR",
            "run_dir_prefix": "LAYERBRAIN_WARGAMES_CRAFTIUM_RUN_DIR_PREFIX",
            "enable_voxel_obs": "LAYERBRAIN_WARGAMES_CRAFTIUM_ENABLE_VOXEL_OBS",
            "wait_step_ms": "LAYERBRAIN_WARGAMES_CRAFTIUM_WAIT_STEP_MS",
            "max_wait_steps": "LAYERBRAIN_WARGAMES_CRAFTIUM_MAX_WAIT_STEPS",
        }
        for key, env_name in mapping.items():
            value = os.getenv(env_name)
            if value is None:
                continue
            if key == "enable_voxel_obs":
                game_values[key] = value.lower() in {"1", "true", "yes", "on"}
            elif key in {"wait_step_ms", "max_wait_steps"}:
                game_values[key] = int(value)
            else:
                game_values[key] = value
        return cls(**base, **game_values)
