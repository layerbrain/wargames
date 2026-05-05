from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wargames.core.missions.catalog import resolve_mission_catalog_path
from wargames.core.missions.spec import MissionDifficulty, MissionSpec

CRAFTIUM_DIFFICULTIES: tuple[MissionDifficulty, ...] = ("easy", "normal", "hard")

_GYM_TASKS = (
    {
        "slug": "room",
        "env_id": "Craftium/Room-v0",
        "title": "Room Navigation",
        "tags": ("voxel", "navigation"),
        "actions": ("forward", "mouse x+", "mouse x-"),
        "ticks": 1_000,
    },
    {
        "slug": "small-room",
        "env_id": "Craftium/SmallRoom-v0",
        "title": "Small Room Navigation",
        "tags": ("voxel", "navigation"),
        "actions": ("forward", "mouse x+", "mouse x-"),
        "ticks": 500,
    },
    {
        "slug": "chop-tree",
        "env_id": "Craftium/ChopTree-v0",
        "title": "Chop Tree",
        "tags": ("voxel", "survival", "resource-gathering"),
        "actions": ("forward", "jump", "dig", "mouse x+", "mouse x-", "mouse y+", "mouse y-"),
        "ticks": 2_000,
    },
    {
        "slug": "speleo",
        "env_id": "Craftium/Speleo-v0",
        "title": "Speleo Cave Navigation",
        "tags": ("voxel", "cave", "navigation"),
        "actions": ("forward", "jump", "mouse x+", "mouse x-", "mouse y+", "mouse y-"),
        "ticks": 500,
    },
    {
        "slug": "spiders-attack",
        "env_id": "Craftium/SpidersAttack-v0",
        "title": "Spiders Attack",
        "tags": ("voxel", "combat", "survival"),
        "actions": (
            "forward",
            "left",
            "right",
            "jump",
            "dig",
            "mouse x+",
            "mouse x-",
            "mouse y+",
            "mouse y-",
        ),
        "ticks": 4_000,
    },
    {
        "slug": "proc-dungeons",
        "env_id": "Craftium/ProcDungeons-v0",
        "title": "Procedural Dungeon",
        "tags": ("voxel", "combat", "exploration"),
        "actions": (
            "forward",
            "left",
            "right",
            "jump",
            "dig",
            "mouse x+",
            "mouse x-",
            "mouse y+",
            "mouse y-",
        ),
        "ticks": 4_000,
    },
    {
        "slug": "open-world",
        "env_id": "Craftium/OpenWorld-v0",
        "title": "Open World",
        "tags": ("voxel", "survival", "crafting", "open-world"),
        "actions": (
            "forward",
            "backward",
            "left",
            "right",
            "jump",
            "sneak",
            "dig",
            "place",
            "slot_1",
            "slot_2",
            "slot_3",
            "slot_4",
            "slot_5",
            "mouse x+",
            "mouse x-",
            "mouse y+",
            "mouse y-",
        ),
        "ticks": 10_000,
    },
)

_CRL_SEQUENCES = (
    {
        "slug": "sequence0-25",
        "sequence_name": "sequence0_25",
        "title": "Continual Dungeon Sequence 0",
        "tags": ("voxel", "combat", "exploration", "continual-rl"),
        "actions": (
            "forward",
            "left",
            "right",
            "jump",
            "dig",
            "mouse x+",
            "mouse x-",
            "mouse y+",
            "mouse y-",
        ),
        "ticks": 4_000,
        "default_count": 25,
    },
)

_TIME_LIMIT_SCALE = {"easy": 1.5, "normal": 1.0, "hard": 0.75}


@dataclass(frozen=True, kw_only=True)
class CraftiumMissionSpec(MissionSpec):
    env_id: str
    action_names: tuple[str, ...]
    loader: str = "gym"
    sequence_name: str | None = None
    task_id: int | None = None
    success_reward: float = 1.0


def discover(root: str | Path | None = None) -> tuple[CraftiumMissionSpec, ...]:
    source_root = Path(root).expanduser() if root else None
    missions: list[CraftiumMissionSpec] = []
    for task in _GYM_TASKS:
        base_ticks = int(task["ticks"])
        for difficulty in CRAFTIUM_DIFFICULTIES:
            scale = _TIME_LIMIT_SCALE[difficulty]
            missions.append(
                CraftiumMissionSpec(
                    id=f"craftium.{task['slug']}.{difficulty}",
                    title=f"{task['title']} ({difficulty.title()})",
                    game="craftium",
                    source="builtin",
                    difficulty=difficulty,
                    native_difficulty=str(task["env_id"]),
                    tags=tuple((*task["tags"], f"env:{task['env_id']}")),
                    time_limit_ticks=max(1, int(base_ticks * scale)),
                    env_id=str(task["env_id"]),
                    action_names=tuple(str(action) for action in task["actions"]),
                )
            )
    for sequence in _CRL_SEQUENCES:
        base_ticks = int(sequence["ticks"])
        sequence_name = str(sequence["sequence_name"])
        for task_id in range(_sequence_task_count(source_root, sequence)):
            for difficulty in CRAFTIUM_DIFFICULTIES:
                scale = _TIME_LIMIT_SCALE[difficulty]
                missions.append(
                    CraftiumMissionSpec(
                        id=(
                            f"craftium.crl.{sequence['slug']}.task-{task_id:02d}."
                            f"{difficulty}"
                        ),
                        title=(
                            f"{sequence['title']} Task {task_id:02d} "
                            f"({difficulty.title()})"
                        ),
                        game="craftium",
                        source="builtin",
                        difficulty=difficulty,
                        native_difficulty=f"{sequence_name}:{task_id}",
                        tags=tuple(
                            (
                                *sequence["tags"],
                                "env:Craftium/ProcDungeons-v0",
                                f"sequence:{sequence_name}",
                            )
                        ),
                        time_limit_ticks=max(1, int(base_ticks * scale)),
                        env_id="Craftium/ProcDungeons-v0",
                        action_names=tuple(str(action) for action in sequence["actions"]),
                        loader="crl_sequence",
                        sequence_name=sequence_name,
                        task_id=task_id,
                    )
                )
    return tuple(missions)


def extract_mission_catalog(root: str | Path | None, output_dir: str | Path) -> tuple[Path, ...]:
    missions = discover(root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*/*.json"):
        stale.unlink()
    written: list[Path] = []
    for mission in missions:
        path = out / mission.difficulty / f"{mission.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(_mission_payload(mission), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return tuple(written)


def load_mission_catalog(path: str | Path) -> tuple[CraftiumMissionSpec, ...]:
    root = resolve_mission_catalog_path(path)
    if not root.exists():
        return ()
    return tuple(
        _mission_from_payload(json.loads(file.read_text(encoding="utf-8")))
        for file in sorted(root.glob("*/*.json"))
    )


def _mission_payload(mission: CraftiumMissionSpec) -> dict[str, object]:
    return {
        "id": mission.id,
        "title": mission.title,
        "game": mission.game,
        "source": mission.source,
        "difficulty": mission.difficulty,
        "native_difficulty": mission.native_difficulty,
        "tags": list(mission.tags),
        "time_limit_ticks": mission.time_limit_ticks,
        "env_id": mission.env_id,
        "action_names": list(mission.action_names),
        "loader": mission.loader,
        "sequence_name": mission.sequence_name,
        "task_id": mission.task_id,
        "success_reward": mission.success_reward,
    }


def _mission_from_payload(data: Mapping[str, Any]) -> CraftiumMissionSpec:
    return CraftiumMissionSpec(
        id=str(data["id"]),
        title=str(data["title"]),
        game=str(data["game"]),
        source=data.get("source", "builtin"),
        difficulty=data.get("difficulty", "normal"),
        native_difficulty=str(data.get("native_difficulty", data["env_id"])),
        tags=tuple(str(tag) for tag in data.get("tags", ())),
        time_limit_ticks=int(data.get("time_limit_ticks", 1_000)),
        env_id=str(data["env_id"]),
        action_names=tuple(str(action) for action in data.get("action_names", ())),
        loader=str(data.get("loader", "gym")),
        sequence_name=None if data.get("sequence_name") is None else str(data["sequence_name"]),
        task_id=None if data.get("task_id") is None else int(data["task_id"]),
        success_reward=float(data.get("success_reward", 1.0)),
    )


def _sequence_task_count(root: Path | None, sequence: Mapping[str, object]) -> int:
    if root is not None:
        path = _sequence_file(root, str(sequence["sequence_name"]))
        if path is not None:
            return len(path.read_text(encoding="utf-8").split("="))
    return int(sequence["default_count"])


def _sequence_file(root: Path, sequence_name: str) -> Path | None:
    candidates = (
        root / "craftium" / "extra" / sequence_name,
        root / "extra" / sequence_name,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None
