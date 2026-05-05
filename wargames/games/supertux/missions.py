from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wargames.core.missions.catalog import resolve_mission_catalog_path
from wargames.core.missions.spec import MissionDifficulty, MissionSpec

SUPERTUX_DIFFICULTIES: tuple[MissionDifficulty, ...] = ("easy", "normal", "hard")

_DIFFICULTY_SETTINGS = {
    "easy": {"time_factor": 1.75, "tag": "training"},
    "normal": {"time_factor": 1.25, "tag": "platforming"},
    "hard": {"time_factor": 1.0, "tag": "speedrun"},
}


@dataclass(frozen=True, kw_only=True)
class SuperTuxMissionSpec(MissionSpec):
    level_file: str
    level_set: str
    target_time_seconds: int | None = None
    data_dir: str | None = None

    def __post_init__(self) -> None:
        if not self.level_file:
            raise ValueError(f"SuperTux mission must reference a level file: {self.id}")


def discover(root: str | Path | None = None) -> tuple[SuperTuxMissionSpec, ...]:
    data_dir = _data_dir(Path(root).expanduser() if root else None)
    if data_dir is None:
        return ()

    levels_root = data_dir / "levels"
    missions: list[SuperTuxMissionSpec] = []
    for level in sorted(levels_root.glob("*/*.stl")):
        if level.parent.name == "misc":
            continue
        missions.extend(_missions_for_level(level, data_dir))
    return tuple(missions)


def extract_mission_catalog(root: str | Path | None, output_dir: str | Path) -> tuple[Path, ...]:
    missions = discover(root)
    if not missions:
        return ()

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


def load_mission_catalog(path: str | Path) -> tuple[SuperTuxMissionSpec, ...]:
    root = resolve_mission_catalog_path(path)
    if not root.exists():
        return ()
    missions: list[SuperTuxMissionSpec] = []
    for file in sorted(root.glob("*/*.json")):
        missions.append(_mission_from_payload(json.loads(file.read_text(encoding="utf-8"))))
    return tuple(missions)


def _missions_for_level(level: Path, data_dir: Path) -> tuple[SuperTuxMissionSpec, ...]:
    metadata = _level_metadata(level)
    level_set = level.parent.name
    slug = _slug(level.stem)
    title = metadata.get("name") or level.stem.replace("_", " ").title()
    target_time = _optional_int(metadata.get("target_time"))
    relative = str(level.relative_to(data_dir))
    missions: list[SuperTuxMissionSpec] = []
    for difficulty in SUPERTUX_DIFFICULTIES:
        settings = _DIFFICULTY_SETTINGS[difficulty]
        time_limit = _time_limit_ticks(target_time, difficulty)
        missions.append(
            SuperTuxMissionSpec(
                id=f"supertux.level.{level_set}.{slug}.{difficulty}",
                title=f"{title} ({difficulty.title()})",
                game="supertux",
                source="builtin",
                difficulty=difficulty,
                native_difficulty=difficulty,
                tags=(level_set, str(settings["tag"]), "platformer"),
                time_limit_ticks=time_limit,
                level_file=relative,
                level_set=level_set,
                target_time_seconds=target_time,
                data_dir=str(data_dir),
            )
        )
    return tuple(missions)


def _level_metadata(level: Path) -> dict[str, str]:
    text = level.read_text(encoding="utf-8", errors="replace")
    metadata: dict[str, str] = {}
    if match := re.search(r"\(name\s+\(_\s+\"([^\"]+)\"\)\)", text):
        metadata["name"] = match.group(1)
    elif match := re.search(r"\(name\s+\"([^\"]+)\"\)", text):
        metadata["name"] = match.group(1)
    if match := re.search(r"\(target-time\s+([0-9]+)\)", text):
        metadata["target_time"] = match.group(1)
    return metadata


def _time_limit_ticks(target_time: int | None, difficulty: str) -> int:
    base_seconds = target_time or 120
    factor = float(_DIFFICULTY_SETTINGS[difficulty]["time_factor"])
    return max(1, int(base_seconds * factor * 60))


def _mission_payload(mission: SuperTuxMissionSpec) -> dict[str, object]:
    return {
        "id": mission.id,
        "title": mission.title,
        "game": mission.game,
        "source": mission.source,
        "difficulty": mission.difficulty,
        "native_difficulty": mission.native_difficulty,
        "tags": list(mission.tags),
        "time_limit_ticks": mission.time_limit_ticks,
        "level_file": mission.level_file,
        "level_set": mission.level_set,
        "target_time_seconds": mission.target_time_seconds,
        "data_dir": mission.data_dir,
    }


def _mission_from_payload(data: Mapping[str, Any]) -> SuperTuxMissionSpec:
    target_time = data.get("target_time_seconds")
    return SuperTuxMissionSpec(
        id=str(data["id"]),
        title=str(data["title"]),
        game=str(data["game"]),
        source=data.get("source", "builtin"),
        difficulty=data.get("difficulty", "normal"),
        native_difficulty=str(data.get("native_difficulty", data.get("difficulty", "normal"))),
        tags=tuple(str(tag) for tag in data.get("tags", ())),
        time_limit_ticks=int(data.get("time_limit_ticks", 7_200)),
        level_file=str(data["level_file"]),
        level_set=str(data.get("level_set", "")),
        target_time_seconds=None if target_time is None else int(target_time),
        data_dir=None if data.get("data_dir") is None else str(data["data_dir"]),
    )


def _data_dir(root: Path | None) -> Path | None:
    candidates: list[Path | None] = [
        root if root and (root / "levels").exists() else None,
        root / "data" if root else None,
        root / "share" / "games" / "supertux2" if root else None,
        root / "usr" / "share" / "games" / "supertux2" if root else None,
        Path("/usr/share/games/supertux2"),
    ]
    for candidate in candidates:
        if candidate is not None and (candidate / "levels").exists():
            return candidate
    return None


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "level"


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)
