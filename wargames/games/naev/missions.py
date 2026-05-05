from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from wargames.core.missions.spec import MissionDifficulty, MissionSpec

NAEV_DIFFICULTIES: tuple[MissionDifficulty, ...] = ("easy", "normal", "hard")
_MISSION_XML = re.compile(r"(<\?xml[^>]*>\s*)?<mission\b.*?</mission>", re.DOTALL)


@dataclass(frozen=True, kw_only=True)
class NaevMissionSpec(MissionSpec):
    mission_name: str
    mission_file: str
    native_location: str
    tier: int | None
    data_dir: str | None = None

    def __post_init__(self) -> None:
        if not self.mission_name:
            raise ValueError(f"Naev mission must declare a native mission name: {self.id}")


@dataclass(frozen=True)
class _NativeMission:
    name: str
    path: Path
    relative_path: str
    location: str
    tier: int | None
    factions: tuple[str, ...]
    campaign: str
    unique: bool
    data_dir: Path


def discover(root: str | Path | None = None) -> tuple[NaevMissionSpec, ...]:
    data_dir = _source_data_dir(Path(root).expanduser() if root else None)
    if data_dir is None:
        return ()
    missions = [
        _mission_for_native(native)
        for native in _discover_native_missions(data_dir)
        if native.name
    ]
    return tuple(sorted(missions, key=lambda mission: (mission.difficulty, mission.id)))


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
        static_mission = _without_data_dir(mission)
        path = out / mission.difficulty / f"{mission.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(_mission_payload(static_mission), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return tuple(written)


def load_mission_catalog(path: str | Path) -> tuple[NaevMissionSpec, ...]:
    root = Path(path)
    if not root.exists():
        return ()
    return tuple(
        _mission_from_payload(json.loads(file.read_text(encoding="utf-8")))
        for file in sorted(root.glob("*/*.json"))
    )


def _discover_native_missions(data_dir: Path) -> tuple[_NativeMission, ...]:
    missions: list[_NativeMission] = []
    mission_root = data_dir / "missions"
    for path in sorted(mission_root.rglob("*.lua")):
        parsed = _parse_native_mission(path, data_dir)
        if parsed is not None:
            missions.append(parsed)
    return tuple(missions)


def _parse_native_mission(path: Path, data_dir: Path) -> _NativeMission | None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = _MISSION_XML.search(text)
    if match is None:
        return None
    root = ET.fromstring(match.group(0))
    relative_path = path.relative_to(data_dir).as_posix()
    return _NativeMission(
        name=str(root.attrib.get("name", "")).strip(),
        path=path,
        relative_path=relative_path,
        location=_text(root, "location"),
        tier=_optional_int(_text(root, "notes/tier")),
        factions=tuple(_text_nodes(root, "faction")),
        campaign=_text(root, "notes/campaign"),
        unique=root.find("unique") is not None,
        data_dir=data_dir,
    )


def _mission_for_native(native: _NativeMission) -> NaevMissionSpec:
    difficulty = _difficulty(native)
    slug = _slug(Path(native.relative_path).with_suffix("").as_posix())
    title = native.name if not native.campaign else f"{native.name} ({native.campaign})"
    return NaevMissionSpec(
        id=f"naev.mission.{slug}.{difficulty}",
        title=title,
        game="naev",
        source="builtin",
        difficulty=difficulty,
        native_difficulty=_native_difficulty(native),
        tags=_tags(native, difficulty),
        time_limit_ticks=_time_limit_ticks(native, difficulty),
        estimated_duration_ticks=_estimated_duration(native, difficulty),
        mission_name=native.name,
        mission_file=native.relative_path,
        native_location=native.location,
        tier=native.tier,
        data_dir=str(native.data_dir),
    )


def _mission_payload(mission: NaevMissionSpec) -> dict[str, object]:
    return {
        "data_dir": mission.data_dir,
        "difficulty": mission.difficulty,
        "estimated_duration_ticks": mission.estimated_duration_ticks,
        "game": mission.game,
        "id": mission.id,
        "mission_file": mission.mission_file,
        "mission_name": mission.mission_name,
        "native_difficulty": mission.native_difficulty,
        "native_location": mission.native_location,
        "source": mission.source,
        "tags": list(mission.tags),
        "tier": mission.tier,
        "time_limit_ticks": mission.time_limit_ticks,
        "title": mission.title,
    }


def _mission_from_payload(data: dict[str, object]) -> NaevMissionSpec:
    return NaevMissionSpec(
        id=str(data["id"]),
        title=str(data["title"]),
        game=str(data.get("game", "naev")),
        source="builtin",
        difficulty=str(data["difficulty"]),  # type: ignore[arg-type]
        native_difficulty=None
        if data.get("native_difficulty") is None
        else str(data["native_difficulty"]),
        tags=tuple(str(tag) for tag in data.get("tags", ())),
        time_limit_ticks=int(data.get("time_limit_ticks", 36_000)),
        estimated_duration_ticks=int(data.get("estimated_duration_ticks", 0)),
        mission_name=str(data["mission_name"]),
        mission_file=str(data["mission_file"]),
        native_location=str(data.get("native_location", "")),
        tier=None if data.get("tier") is None else int(data["tier"]),
        data_dir=None if data.get("data_dir") is None else str(data["data_dir"]),
    )


def _without_data_dir(mission: NaevMissionSpec) -> NaevMissionSpec:
    return NaevMissionSpec(
        id=mission.id,
        title=mission.title,
        game=mission.game,
        source=mission.source,
        difficulty=mission.difficulty,
        native_difficulty=mission.native_difficulty,
        tags=mission.tags,
        time_limit_ticks=mission.time_limit_ticks,
        estimated_duration_ticks=mission.estimated_duration_ticks,
        mission_name=mission.mission_name,
        mission_file=mission.mission_file,
        native_location=mission.native_location,
        tier=mission.tier,
        data_dir=None,
    )


def _source_data_dir(root: Path | None) -> Path | None:
    candidates = [
        root,
        root / "dat" if root else None,
        Path("/usr/share/naev/dat"),
    ]
    for candidate in candidates:
        if candidate and (candidate / "missions").is_dir() and (candidate / "start.xml").exists():
            return candidate
    return None


def _difficulty(native: _NativeMission) -> MissionDifficulty:
    name = native.name.lower()
    path = native.relative_path.lower()
    location = native.location.lower()
    tier = native.tier or 1
    combat_words = (
        "pirate",
        "bounty",
        "hitman",
        "raid",
        "combat",
        "convoy",
        "assault",
        "war",
        "warlord",
        "shadow",
        "shark",
        "flf",
        "empire",
        "dvaered",
        "proteron",
    )
    easy_words = ("tutorial", "cargo", "courier", "ferry", "sightseeing", "delivery")
    if tier >= 3 or any(word in path or word in name for word in combat_words):
        return "hard"
    if tier <= 1 and (
        location in {"bar", "computer", "none"}
        or any(word in path or word in name for word in easy_words)
    ):
        return "easy"
    return "normal"


def _native_difficulty(native: _NativeMission) -> str:
    if native.tier is None:
        return "scripted"
    return f"tier-{native.tier}"


def _tags(native: _NativeMission, difficulty: MissionDifficulty) -> tuple[str, ...]:
    tags = {"space", "mission", difficulty}
    if native.location:
        tags.add(_slug(native.location))
    if native.tier is not None:
        tags.add(f"tier-{native.tier}")
    for source in (native.relative_path, native.name, native.campaign):
        lowered = source.lower()
        if any(word in lowered for word in ("pirate", "bounty", "raid", "combat", "hitman")):
            tags.add("combat")
        if any(word in lowered for word in ("cargo", "commodity", "courier", "delivery")):
            tags.add("delivery")
        if any(word in lowered for word in ("sightseeing", "explore", "survey")):
            tags.add("exploration")
        if "tutorial" in lowered:
            tags.add("tutorial")
        if "trader" in lowered:
            tags.add("trading")
    return tuple(sorted(tags))


def _time_limit_ticks(native: _NativeMission, difficulty: MissionDifficulty) -> int:
    tier = native.tier or 1
    base = {"easy": 7200, "normal": 14_400, "hard": 21_600}[difficulty]
    return base + max(0, tier - 1) * 3600


def _estimated_duration(native: _NativeMission, difficulty: MissionDifficulty) -> int:
    return _time_limit_ticks(native, difficulty) // 2


def _text(root: ET.Element, path: str) -> str:
    found = root.find(path)
    if found is None or found.text is None:
        return ""
    return found.text.strip()


def _text_nodes(root: ET.Element, path: str) -> list[str]:
    return [node.text.strip() for node in root.findall(path) if node.text and node.text.strip()]


def _optional_int(value: str) -> int | None:
    if not value:
        return None
    return int(value)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "mission"
