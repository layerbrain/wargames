from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from wargames.evaluation.splits import TaskCatalog
from wargames.evaluation.task import RunConfig, TaskSpec
from wargames.games.redalert import GAME


@dataclass
class WarGamesPrimeEnv:
    tasks: tuple[TaskSpec, ...]
    profile_id: str
    run_config: RunConfig

    def dataset(self) -> list[dict[str, Any]]:
        return [task.to_mapping() for task in self.tasks]

    def eval_dataset(self) -> list[dict[str, Any]]:
        return self.dataset()


def load_environment(
    split: str = "train",
    game: str = "redalert",
    reward_profile: str = "standard",
    recorder_mode: str = "none",
    **kwargs: object,
) -> WarGamesPrimeEnv:
    _ = GAME
    tasks = tuple(
        task.with_reward_profile(reward_profile)
        for task in TaskCatalog.load("scenarios").tasks(game=game, split=split)
    )
    return WarGamesPrimeEnv(
        tasks=tasks,
        profile_id=reward_profile,
        run_config=RunConfig(recorder_mode=recorder_mode),
    )
