from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wargames.core.missions.spec import MissionDifficulty, MissionSpec

MINDUSTRY_DIFFICULTIES: tuple[MissionDifficulty, ...] = ("easy", "normal", "hard")

_MAPS = (
    ("veins", "Veins"),
    ("fork", "Fork"),
    ("fortress", "Fortress"),
    ("islands", "Islands"),
    ("labyrinth", "Labyrinth"),
    ("maze", "Maze"),
    ("ravine", "Ravine"),
    ("shattered", "Shattered"),
    ("triad", "Triad"),
)

_DIFFICULTY_SETTINGS = {
    "easy": {"win_wave": 10, "ticks": 18_000},
    "normal": {"win_wave": 20, "ticks": 36_000},
    "hard": {"win_wave": 40, "ticks": 72_000},
}


@dataclass(frozen=True, kw_only=True)
class MindustryMissionSpec(MissionSpec):
    map_name: str
    mode: str = "survival"
    win_wave: int = 20


def discover(root: str | Path | None = None) -> tuple[MindustryMissionSpec, ...]:
    del root
    missions: list[MindustryMissionSpec] = []
    for slug, map_name in _MAPS:
        for difficulty in MINDUSTRY_DIFFICULTIES:
            settings = _DIFFICULTY_SETTINGS[difficulty]
            missions.append(
                MindustryMissionSpec(
                    id=f"mindustry.survival.{slug}.{difficulty}",
                    title=f"{map_name} Survival ({difficulty.title()})",
                    game="mindustry",
                    source="builtin",
                    difficulty=difficulty,
                    native_difficulty=difficulty,
                    tags=("factory", "tower-defense", "survival", f"win-wave:{settings['win_wave']}"),
                    time_limit_ticks=int(settings["ticks"]),
                    map_name=map_name,
                    mode="survival",
                    win_wave=int(settings["win_wave"]),
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


def load_mission_catalog(path: str | Path) -> tuple[MindustryMissionSpec, ...]:
    root = Path(path)
    if not root.exists():
        return ()
    return tuple(
        _mission_from_payload(json.loads(file.read_text(encoding="utf-8")))
        for file in sorted(root.glob("*/*.json"))
    )


def _mission_payload(mission: MindustryMissionSpec) -> dict[str, object]:
    return {
        "id": mission.id,
        "title": mission.title,
        "game": mission.game,
        "source": mission.source,
        "difficulty": mission.difficulty,
        "native_difficulty": mission.native_difficulty,
        "tags": list(mission.tags),
        "time_limit_ticks": mission.time_limit_ticks,
        "map_name": mission.map_name,
        "mode": mission.mode,
        "win_wave": mission.win_wave,
    }


def _mission_from_payload(data: Mapping[str, Any]) -> MindustryMissionSpec:
    return MindustryMissionSpec(
        id=str(data["id"]),
        title=str(data["title"]),
        game=str(data["game"]),
        source=data.get("source", "builtin"),
        difficulty=data.get("difficulty", "normal"),
        native_difficulty=str(data.get("native_difficulty", data.get("difficulty", "normal"))),
        tags=tuple(str(tag) for tag in data.get("tags", ())),
        time_limit_ticks=int(data.get("time_limit_ticks", 36_000)),
        map_name=str(data["map_name"]),
        mode=str(data.get("mode", "survival")),
        win_wave=int(data.get("win_wave", 20)),
    )


def slug_map_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
