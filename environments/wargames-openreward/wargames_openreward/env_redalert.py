from __future__ import annotations

from dataclasses import replace
from typing import Any

from wargames.core.control.tools import CUA_TOOL_SPECS
from wargames.evaluation.splits import TaskCatalog
from wargames.evaluation.task import TaskSpec
from wargames.games.redalert import GAME
from wargames_openreward.variants import WARGAMES_REDALERT_VARIANTS


class WarGamesRedAlert:
    env_id = "Layerbrain/WarGamesRedAlert"

    @classmethod
    def list_splits(cls) -> list[dict[str, str]]:
        return [
            {"name": "debug", "type": "debug"},
            {"name": "train", "type": "train"},
            {"name": "validation", "type": "validation"},
            {"name": "test", "type": "test"},
            {"name": "curriculum", "type": "train"},
        ]

    @classmethod
    def list_variants(cls) -> list[dict[str, str]]:
        return [{"name": name} for name in WARGAMES_REDALERT_VARIANTS]

    @classmethod
    def list_tasks(cls, split: str) -> list[dict[str, Any]]:
        _ = GAME
        return [task.to_mapping() for task in TaskCatalog.load("scenarios").tasks(game="redalert", split=split)]

    @classmethod
    def list_tools(cls) -> list[str]:
        return [tool.name for tool in CUA_TOOL_SPECS]

    @staticmethod
    def task_for_variant(task: TaskSpec, variant: str) -> TaskSpec:
        profile = WARGAMES_REDALERT_VARIANTS[variant]["reward_profile"]
        return replace(task, reward_profile=profile)
