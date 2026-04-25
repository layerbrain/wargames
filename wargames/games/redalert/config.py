from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from wargames.core.config import WarGamesConfig


@dataclass(frozen=True)
class RedAlertConfig(WarGamesConfig):
    openra_binary: str | None = None
    openra_mod: Literal["ra"] = "ra"
    openra_support_dir: str | None = None
    openra_root: str | None = None
    dotnet_root: str | None = None
    openra_window_size: tuple[int, int] = (1280, 720)
    extracted_missions_dir: str = "scenarios/redalert/missions"

    @classmethod
    def from_env(cls) -> "RedAlertConfig":
        base = WarGamesConfig.from_env_prefix("LAYERBRAIN_WARGAMES_").__dict__
        game_values: dict[str, object] = {}
        mapping = {
            "openra_binary": "LAYERBRAIN_WARGAMES_REDALERT_OPENRA_BINARY",
            "openra_mod": "LAYERBRAIN_WARGAMES_REDALERT_OPENRA_MOD",
            "openra_support_dir": "LAYERBRAIN_WARGAMES_REDALERT_OPENRA_SUPPORT_DIR",
            "openra_root": "LAYERBRAIN_WARGAMES_REDALERT_OPENRA_ROOT",
            "dotnet_root": "LAYERBRAIN_WARGAMES_REDALERT_DOTNET_ROOT",
            "openra_window_size": "LAYERBRAIN_WARGAMES_REDALERT_OPENRA_WINDOW_SIZE",
            "extracted_missions_dir": "LAYERBRAIN_WARGAMES_REDALERT_EXTRACTED_MISSIONS_DIR",
        }
        for key, env_name in mapping.items():
            value = os.getenv(env_name)
            if value is not None:
                if key == "openra_window_size":
                    width, _, height = value.replace("x", ",").partition(",")
                    game_values[key] = (int(width.strip()), int(height.strip()))
                else:
                    game_values[key] = value
        return cls(**base, **game_values)
