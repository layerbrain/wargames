from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wargames.core.missions.catalog import resolve_mission_catalog_path
from wargames.core.missions.spec import MissionDifficulty, MissionSpec

OPENSURGE_DIFFICULTIES: tuple[MissionDifficulty, ...] = ("easy", "normal", "hard")

_DIFFICULTY_SETTINGS = {
    "easy": {"time_factor": 1.75, "tag": "training"},
    "normal": {"time_factor": 1.25, "tag": "momentum"},
    "hard": {"time_factor": 1.0, "tag": "speedrun"},
}
_SKIPPED_LEVELS = {"empty", "sandbox", "surgescript"}


@dataclass(frozen=True, kw_only=True)
class OpenSurgeMissionSpec(MissionSpec):
    level_file: str
    level_set: str
    act: int
    target_time_seconds: int
    data_dir: str | None = None

    def __post_init__(self) -> None:
        if not self.level_file:
            raise ValueError(f"OpenSurge mission must reference a level file: {self.id}")


def discover(root: str | Path | None = None) -> tuple[OpenSurgeMissionSpec, ...]:
    data_dir = _data_dir(Path(root).expanduser() if root else None)
    if data_dir is None:
        return ()

    missions: list[OpenSurgeMissionSpec] = []
    for level in sorted((data_dir / "levels").glob("*.lev")):
        if level.stem in _SKIPPED_LEVELS:
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


def load_mission_catalog(path: str | Path) -> tuple[OpenSurgeMissionSpec, ...]:
    root = resolve_mission_catalog_path(path)
    if not root.exists():
        return ()
    return tuple(
        _mission_from_payload(json.loads(file.read_text(encoding="utf-8")))
        for file in sorted(root.glob("*/*.json"))
    )


def _missions_for_level(level: Path, data_dir: Path) -> tuple[OpenSurgeMissionSpec, ...]:
    metadata = _level_metadata(level)
    slug = _slug(level.stem)
    title = metadata.get("name") or level.stem.replace("-", " ").title()
    act = _optional_int(metadata.get("act")) or 1
    width = _optional_int(metadata.get("max_x")) or 20_000
    target_time = _target_time_seconds(width)
    relative = str(level.relative_to(data_dir))
    missions: list[OpenSurgeMissionSpec] = []
    for difficulty in OPENSURGE_DIFFICULTIES:
        settings = _DIFFICULTY_SETTINGS[difficulty]
        missions.append(
            OpenSurgeMissionSpec(
                id=f"opensurge.level.{slug}.{difficulty}",
                title=f"{title} Act {act} ({difficulty.title()})",
                game="opensurge",
                source="builtin",
                difficulty=difficulty,
                native_difficulty=difficulty,
                tags=("platformer", "running", str(settings["tag"])),
                time_limit_ticks=_time_limit_ticks(target_time, difficulty),
                level_file=relative,
                level_set="builtin",
                act=act,
                target_time_seconds=target_time,
                data_dir=str(data_dir),
            )
        )
    return tuple(missions)


def _level_metadata(level: Path) -> dict[str, str]:
    text = level.read_text(encoding="utf-8", errors="replace")
    metadata: dict[str, str] = {}
    for key in ("name", "author", "license", "version"):
        if match := re.search(rf'^{key}\s+"([^"]+)"', text, re.MULTILINE):
            metadata[key] = match.group(1)
    if match := re.search(r"^act\s+([0-9]+)", text, re.MULTILINE):
        metadata["act"] = match.group(1)
    xs = [
        int(match.group(1))
        for match in re.finditer(
            r"^(?:brick|item|object)\s+\S+\s+(-?\d+)\s+-?\d+", text, re.MULTILINE
        )
    ]
    if xs:
        metadata["max_x"] = str(max(xs))
    return metadata


def _target_time_seconds(level_width: int) -> int:
    return max(45, min(300, level_width // 220))


def _time_limit_ticks(target_time: int, difficulty: str) -> int:
    factor = float(_DIFFICULTY_SETTINGS[difficulty]["time_factor"])
    return max(1, int(target_time * factor * 60))


def _mission_payload(mission: OpenSurgeMissionSpec) -> dict[str, object]:
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
        "act": mission.act,
        "target_time_seconds": mission.target_time_seconds,
        "data_dir": mission.data_dir,
    }


def _mission_from_payload(data: Mapping[str, Any]) -> OpenSurgeMissionSpec:
    return OpenSurgeMissionSpec(
        id=str(data["id"]),
        title=str(data["title"]),
        game=str(data["game"]),
        source=data.get("source", "builtin"),
        difficulty=data.get("difficulty", "normal"),
        native_difficulty=str(data.get("native_difficulty", data.get("difficulty", "normal"))),
        tags=tuple(str(tag) for tag in data.get("tags", ())),
        time_limit_ticks=int(data.get("time_limit_ticks", 7_200)),
        level_file=str(data["level_file"]),
        level_set=str(data.get("level_set", "builtin")),
        act=int(data.get("act", 1)),
        target_time_seconds=int(data.get("target_time_seconds", 120)),
        data_dir=None if data.get("data_dir") is None else str(data["data_dir"]),
    )


def _data_dir(root: Path | None) -> Path | None:
    candidates: list[Path | None] = [
        root if root and (root / "levels").exists() else None,
        root / "data" if root else None,
        root / "share" / "games" / "opensurge" if root else None,
        root / "usr" / "share" / "games" / "opensurge" if root else None,
        Path("/usr/share/games/opensurge"),
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
