from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
import json
from pathlib import Path

from wargames.core.missions.spec import MissionDifficulty
from wargames.core.missions.spec import MissionSpec

REDALERT_DIFFICULTIES: tuple[MissionDifficulty, ...] = ("easy", "normal", "hard")


@dataclass(frozen=True)
class RedAlertMissionSpec(MissionSpec):
    map: str = ""
    faction: str | None = None
    player_slots: int = 1
    min_players: int = 1
    launch_mode: str = "direct"


def _slug(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "map"


def _read_title(map_yaml: str, fallback: str) -> str:
    for line in map_yaml.splitlines():
        stripped = line.strip()
        if stripped.startswith("Title:"):
            return stripped.partition(":")[2].strip().strip("'\"") or fallback
    return fallback


def _side_tags(map_name: str) -> tuple[str, ...]:
    tags = ["campaign"] if not map_name.startswith("skirmish.") else ["skirmish"]
    lowered = map_name.lower()
    if lowered.startswith("soviet"):
        tags.append("soviet")
    elif lowered.startswith("allies"):
        tags.append("allies")
    return tuple(tags)


def _native_difficulties_for_map(map_dir: Path) -> tuple[str, ...]:
    rules = map_dir / "rules.yaml"
    if not rules.exists():
        return ("normal",)
    text = rules.read_text(errors="ignore")
    if "ScriptLobbyDropdown@difficulty" not in text:
        return ("normal",)
    found = tuple(
        difficulty
        for difficulty in REDALERT_DIFFICULTIES
        if re.search(rf"^\s*{difficulty}:", text, re.MULTILINE)
    )
    return found or ("normal",)


def _mission_variants(
    *,
    id_prefix: str,
    title: str,
    source: str,
    map_name: str,
    map_path: Path | None = None,
    player_slots: int = 1,
    min_players: int = 1,
) -> list[RedAlertMissionSpec]:
    native_difficulties = (
        _native_difficulties_for_map(map_path) if map_path and map_path.is_dir() else ("normal",)
    )
    specs: list[RedAlertMissionSpec] = []
    for native in native_difficulties:
        difficulty: MissionDifficulty = native if native in REDALERT_DIFFICULTIES else "normal"  # type: ignore[assignment]
        spec_id = f"{id_prefix}.{difficulty}" if source == "builtin" else id_prefix
        spec_title = (
            f"{title} ({difficulty.replace('_', ' ').title()})" if source == "builtin" else title
        )
        specs.append(
            RedAlertMissionSpec(
                id=spec_id,
                title=spec_title,
                game="redalert",
                source=source,  # type: ignore[arg-type]
                map=map_name,
                difficulty=difficulty,
                native_difficulty=native,
                tags=_side_tags(map_name),
                player_slots=player_slots,
                min_players=min_players,
            )
        )
    return specs


def _mission_entries(missions_yaml: Path) -> list[tuple[str, str]]:
    if not missions_yaml.exists():
        return []
    entries: list[tuple[str, str]] = []
    lines = missions_yaml.read_text().splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped or line[:1].isspace() or not stripped.endswith(":"):
            index += 1
            continue
        key = stripped[:-1]
        children: list[str] = []
        index += 1
        while index < len(lines) and (not lines[index].strip() or lines[index][:1].isspace()):
            child = lines[index].strip()
            if child:
                children.append(child)
            index += 1
        title = next(
            (
                child.partition("Title:")[2].strip().strip("'\"")
                for child in children
                if child.startswith("Title:")
            ),
            "",
        )
        mission_children = [child for child in children if ":" not in child]
        if title:
            entries.append((key, title))
        else:
            for mission in mission_children:
                entries.append((mission, mission.replace("-", " ").title()))
    return entries


def _skirmish_directory(path: Path) -> RedAlertMissionSpec | None:
    map_yaml = path / "map.yaml"
    if not map_yaml.exists():
        return None
    title = _read_title(map_yaml.read_text(), path.name)
    id = f"redalert.skirmish.{_slug(path.name)}"
    return RedAlertMissionSpec(
        id=id,
        title=title,
        game="redalert",
        source="skirmish",
        map=str(path),
        difficulty="normal",
        native_difficulty="normal",
        tags=("skirmish",),
        player_slots=8,
        min_players=2,
    )


def _skirmish_archive(path: Path) -> RedAlertMissionSpec | None:
    try:
        with zipfile.ZipFile(path) as archive:
            with archive.open("map.yaml") as handle:
                text = handle.read().decode()
    except (KeyError, zipfile.BadZipFile):
        return None
    title = _read_title(text, path.stem)
    id = f"redalert.skirmish.{_slug(path.stem)}"
    return RedAlertMissionSpec(
        id=id,
        title=title,
        game="redalert",
        source="skirmish",
        map=str(path),
        difficulty="normal",
        native_difficulty="normal",
        tags=("skirmish",),
        player_slots=8,
        min_players=2,
    )


def discover(openra_root: str | Path) -> tuple[RedAlertMissionSpec, ...]:
    root = Path(openra_root)
    ra = root / "mods" / "ra"
    discovered: list[RedAlertMissionSpec] = []
    for map_name, title in _mission_entries(ra / "missions.yaml"):
        discovered.extend(
            _mission_variants(
                id_prefix=f"redalert.{_slug(map_name)}",
                title=title,
                source="builtin",
                map_name=map_name,
                map_path=ra / "maps" / map_name,
            )
        )
    maps = ra / "maps"
    if maps.exists():
        for path in sorted(maps.iterdir()):
            spec = (
                _skirmish_archive(path) if path.suffix == ".oramap" else _skirmish_directory(path)
            )
            if spec is not None:
                discovered.append(spec)
    return tuple(discovered)


def load_mission_catalog(path: str | Path) -> tuple[RedAlertMissionSpec, ...]:
    root = Path(path)
    if not root.exists():
        return ()
    missions: list[RedAlertMissionSpec] = []
    for file in sorted(root.glob("*/*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        missions.append(
            RedAlertMissionSpec(
                id=str(data["id"]),
                title=str(data["title"]),
                game=str(data["game"]),
                source=data.get("source", "builtin"),
                map=str(data["map"]),
                difficulty=data.get("difficulty", "normal"),
                native_difficulty=str(data.get("native_difficulty", "normal")),
                tags=tuple(str(tag) for tag in data.get("tags", ())),
                player_slots=int(data.get("player_slots", 1)),
                min_players=int(data.get("min_players", 1)),
                launch_mode=str(data.get("launch_mode", "direct")),
                time_limit_ticks=int(data.get("time_limit_ticks", 36_000)),
            )
        )
    return tuple(missions)


def fallback_missions() -> tuple[RedAlertMissionSpec, ...]:
    return (
        RedAlertMissionSpec(
            id="redalert.soviet-01.normal",
            title="Soviet Mission 1 (Normal)",
            game="redalert",
            source="builtin",
            map="soviet-01",
            difficulty="normal",
            native_difficulty="normal",
            tags=("campaign", "soviet"),
        ),
        RedAlertMissionSpec(
            id="redalert.skirmish.oasis",
            title="Oasis",
            game="redalert",
            source="skirmish",
            map="oasis",
            difficulty="normal",
            native_difficulty="normal",
            tags=("skirmish",),
            player_slots=8,
            min_players=2,
        ),
    )


def extract_mission_catalog(openra_root: str | Path, output_dir: str | Path) -> tuple[Path, ...]:
    root = Path(output_dir)
    written: list[Path] = []
    for difficulty in (*REDALERT_DIFFICULTIES, "extra_hard"):
        (root / difficulty).mkdir(parents=True, exist_ok=True)
    for mission in discover(openra_root):
        path = root / mission.difficulty / f"{mission.id}.json"
        path.write_text(
            json.dumps(
                {
                    "id": mission.id,
                    "title": mission.title,
                    "game": mission.game,
                    "source": mission.source,
                    "map": mission.map,
                    "difficulty": mission.difficulty,
                    "native_difficulty": mission.native_difficulty,
                    "tags": list(mission.tags),
                    "player_slots": mission.player_slots,
                    "min_players": mission.min_players,
                    "launch_mode": mission.launch_mode,
                    "time_limit_ticks": mission.time_limit_ticks,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        written.append(path)
    return tuple(written)
