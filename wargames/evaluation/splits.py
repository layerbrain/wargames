from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from wargames.evaluation.profile import profile_registry
from wargames.evaluation.profile_loader import load_yaml, resolve_scenarios_root
from wargames.evaluation.task import SPLITS, SplitName, TaskSpec


@dataclass(frozen=True)
class TaskCatalog:
    tasks_by_id: dict[str, TaskSpec]

    @classmethod
    def load(cls, root: str | Path = "scenarios") -> "TaskCatalog":
        root_path = resolve_scenarios_root(root)
        tasks: list[TaskSpec] = []
        for game_dir in sorted(path for path in root_path.iterdir() if path.is_dir()) if root_path.exists() else ():
            tasks_dir = game_dir / "tasks"
            if not tasks_dir.exists():
                continue
            for split in SPLITS:
                split_dir = tasks_dir / split
                for path in sorted(split_dir.glob("*.yaml")) if split_dir.exists() else ():
                    data = load_yaml(path)
                    raw_tasks = data.get("tasks", (data,))
                    if isinstance(raw_tasks, dict):
                        raw_tasks = (raw_tasks,)
                    for raw_task in raw_tasks:
                        if not isinstance(raw_task, dict):
                            raise ValueError(f"{path}: tasks must be mappings")
                        raw_task = {"game": game_dir.name, **raw_task}
                        tasks.append(TaskSpec.from_mapping(raw_task, split=split))
        return cls.from_tasks(tasks)

    @classmethod
    def from_tasks(cls, tasks: Iterable[TaskSpec]) -> "TaskCatalog":
        by_id: dict[str, TaskSpec] = {}
        seen_pairs: dict[tuple[str, str, int], SplitName] = {}
        for task in tasks:
            if task.id in by_id:
                raise ValueError(f"duplicate task id: {task.id}")
            pair = (task.game, task.mission_id, task.seed)
            previous_split = seen_pairs.get(pair)
            if previous_split is not None and previous_split != task.split:
                raise ValueError(
                    f"task {task.game}/{task.mission_id}/{task.seed} appears in both "
                    f"{previous_split} and {task.split}"
                )
            if task.split == "test":
                try:
                    profile = profile_registry.get(task.game, task.reward_profile)
                except KeyError:
                    profile = None
                if profile is not None and profile.train_only:
                    raise ValueError(f"test task {task.id} cannot use train-only profile {profile.id}")
            seen_pairs[pair] = task.split
            by_id[task.id] = task
        return cls(by_id)

    def get(self, id: str) -> TaskSpec:
        try:
            return self.tasks_by_id[id]
        except KeyError as exc:
            raise KeyError(f"unknown task: {id}") from exc

    def tasks(self, *, game: str | None = None, split: str | None = None) -> tuple[TaskSpec, ...]:
        tasks = self.tasks_by_id.values()
        if game is not None:
            tasks = [task for task in tasks if task.game == game]
        if split is not None:
            tasks = [task for task in tasks if task.split == split]
        return tuple(sorted(tasks, key=lambda task: task.id))
