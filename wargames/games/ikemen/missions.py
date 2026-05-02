from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wargames.core.missions.spec import MissionDifficulty, MissionSpec

IKEMEN_DIFFICULTIES: tuple[MissionDifficulty, ...] = ("easy", "normal", "hard")

_OPPONENTS = (
    ("kfm", "Kung Fu Man", "kfm"),
    ("kfmz", "Kung Fu Man Z", "kfmZ"),
    ("kfm720", "Kung Fu Man 720", "kfm720"),
)

_DIFFICULTY_SETTINGS = {
    "easy": {"ai_level": 2, "rounds": 1, "time": 99, "ticks": 7_200},
    "normal": {"ai_level": 5, "rounds": 1, "time": 99, "ticks": 7_200},
    "hard": {"ai_level": 8, "rounds": 2, "time": 99, "ticks": 14_400},
}


@dataclass(frozen=True, kw_only=True)
class IkemenMissionSpec(MissionSpec):
    p1: str = "kfm"
    p2: str = "kfm"
    stage: str = "stages/stage1.def"
    ai_level: int = 5
    rounds: int = 1
    round_time: int = 99


def discover(root: str | Path | None = None) -> tuple[IkemenMissionSpec, ...]:
    del root
    missions: list[IkemenMissionSpec] = []
    for slug, title, character in _OPPONENTS:
        for difficulty in IKEMEN_DIFFICULTIES:
            settings = _DIFFICULTY_SETTINGS[difficulty]
            missions.append(
                IkemenMissionSpec(
                    id=f"ikemen.vs.{slug}.{difficulty}",
                    title=f"KFM vs {title} ({difficulty.title()})",
                    game="ikemen",
                    source="builtin",
                    difficulty=difficulty,
                    native_difficulty=str(settings["ai_level"]),
                    tags=("fighting", "single-match", f"ai:{settings['ai_level']}"),
                    time_limit_ticks=int(settings["ticks"]),
                    p1="kfm",
                    p2=character,
                    stage="stages/stage1.def",
                    ai_level=int(settings["ai_level"]),
                    rounds=int(settings["rounds"]),
                    round_time=int(settings["time"]),
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


def load_mission_catalog(path: str | Path) -> tuple[IkemenMissionSpec, ...]:
    root = Path(path)
    if not root.exists():
        return ()
    return tuple(
        _mission_from_payload(json.loads(file.read_text(encoding="utf-8")))
        for file in sorted(root.glob("*/*.json"))
    )


def _mission_payload(mission: IkemenMissionSpec) -> dict[str, object]:
    return {
        "id": mission.id,
        "title": mission.title,
        "game": mission.game,
        "source": mission.source,
        "difficulty": mission.difficulty,
        "native_difficulty": mission.native_difficulty,
        "tags": list(mission.tags),
        "time_limit_ticks": mission.time_limit_ticks,
        "p1": mission.p1,
        "p2": mission.p2,
        "stage": mission.stage,
        "ai_level": mission.ai_level,
        "rounds": mission.rounds,
        "round_time": mission.round_time,
    }


def _mission_from_payload(data: Mapping[str, Any]) -> IkemenMissionSpec:
    return IkemenMissionSpec(
        id=str(data["id"]),
        title=str(data["title"]),
        game=str(data["game"]),
        source=data.get("source", "builtin"),
        difficulty=data.get("difficulty", "normal"),
        native_difficulty=str(data.get("native_difficulty", data.get("ai_level", 5))),
        tags=tuple(str(tag) for tag in data.get("tags", ())),
        time_limit_ticks=int(data.get("time_limit_ticks", 7_200)),
        p1=str(data.get("p1", "kfm")),
        p2=str(data.get("p2", "kfm")),
        stage=str(data.get("stage", "stages/stage1.def")),
        ai_level=int(data.get("ai_level", 5)),
        rounds=int(data.get("rounds", 1)),
        round_time=int(data.get("round_time", 99)),
    )
