from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from wargames.core.missions.catalog import resolve_mission_catalog_path
from wargames.core.missions.spec import MissionSpec


@dataclass(frozen=True)
class FlightGearMissionSpec(MissionSpec):
    aircraft: str = "c172p"
    airport: str = "KSFO"
    runway: str | None = None
    timeofday: str = "noon"
    launch_mode: str = "direct"
    tutorial: str | None = None
    tutorial_file: str | None = None
    description: str = ""
    startup_args: tuple[str, ...] = ()


def discover(
    flightgear_root: str | Path, *, aircraft: str = "c172p"
) -> tuple[FlightGearMissionSpec, ...]:
    tutorials = _tutorials_dir(Path(flightgear_root), aircraft)
    if tutorials is None:
        return ()

    files = _tutorial_files(tutorials, aircraft)
    missions: list[FlightGearMissionSpec] = []
    for file in files:
        mission = _tutorial_mission(file, aircraft=aircraft)
        if mission is not None:
            missions.append(mission)
    return tuple(missions)


def extract_mission_catalog(
    flightgear_root: str | Path,
    output_dir: str | Path,
    *,
    aircraft: str = "c172p",
) -> tuple[Path, ...]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    for stale in root.glob("*/*.json"):
        stale.unlink()

    written: list[Path] = []
    for mission in discover(flightgear_root, aircraft=aircraft):
        path = root / mission.difficulty / f"{mission.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "id": mission.id,
                    "title": mission.title,
                    "game": mission.game,
                    "source": mission.source,
                    "difficulty": mission.difficulty,
                    "native_difficulty": mission.native_difficulty,
                    "tags": list(mission.tags),
                    "time_limit_ticks": mission.time_limit_ticks,
                    "aircraft": mission.aircraft,
                    "airport": mission.airport,
                    "runway": mission.runway,
                    "timeofday": mission.timeofday,
                    "launch_mode": mission.launch_mode,
                    "tutorial": mission.tutorial,
                    "tutorial_file": mission.tutorial_file,
                    "description": mission.description,
                    "startup_args": list(mission.startup_args),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return tuple(written)


def load_mission_catalog(path: str | Path) -> tuple[FlightGearMissionSpec, ...]:
    root = resolve_mission_catalog_path(path)
    if not root.exists():
        return ()
    missions: list[FlightGearMissionSpec] = []
    for file in sorted(root.glob("*/*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        missions.append(
            FlightGearMissionSpec(
                id=str(data["id"]),
                title=str(data["title"]),
                game=str(data["game"]),
                source=data.get("source", "builtin"),
                difficulty=data.get("difficulty", "normal"),
                native_difficulty=str(data.get("native_difficulty", "normal")),
                tags=tuple(str(tag) for tag in data.get("tags", ())),
                time_limit_ticks=int(data.get("time_limit_ticks", 36_000)),
                aircraft=str(data.get("aircraft", "c172p")),
                airport=str(data.get("airport", "KSFO")),
                runway=str(data["runway"]) if data.get("runway") else None,
                timeofday=str(data.get("timeofday", "noon")),
                launch_mode=str(data.get("launch_mode", "direct")),
                tutorial=str(data["tutorial"]) if data.get("tutorial") else None,
                tutorial_file=str(data["tutorial_file"]) if data.get("tutorial_file") else None,
                description=str(data.get("description", "")),
                startup_args=tuple(str(arg) for arg in data.get("startup_args", ())),
            )
        )
    return tuple(missions)


def _tutorials_dir(root: Path, aircraft: str) -> Path | None:
    candidates = (
        root / "Aircraft" / aircraft / "Tutorials",
        root / "share" / "games" / "flightgear" / "Aircraft" / aircraft / "Tutorials",
        root / "data" / "Aircraft" / aircraft / "Tutorials",
        Path("/usr/share/games/flightgear") / "Aircraft" / aircraft / "Tutorials",
        Path("/usr/share/flightgear") / "Aircraft" / aircraft / "Tutorials",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _tutorial_files(tutorials: Path, aircraft: str) -> tuple[Path, ...]:
    manifest = next(iter(sorted(tutorials.glob("*-tutorials.xml"))), None)
    if manifest is None:
        return tuple(
            path
            for path in sorted(tutorials.glob("*.xml"))
            if not path.name.endswith("-tutorials.xml")
        )

    root = ElementTree.parse(manifest).getroot()
    files: list[Path] = []
    for node in root.findall("tutorial"):
        include = node.get("include")
        if include:
            path = tutorials / include
            if path.exists():
                files.append(path)
    return tuple(files)


def _tutorial_mission(file: Path, *, aircraft: str) -> FlightGearMissionSpec | None:
    root = ElementTree.parse(file).getroot()
    title = _text(root, "name") or file.stem.replace("-", " ").title()
    tutorial_id = _slug(file.stem)
    presets = root.find("presets")
    airport = _text(presets, "airport-id") or "KSFO"
    return FlightGearMissionSpec(
        id=f"flightgear.{aircraft}.tutorial.{tutorial_id}",
        title=title,
        game="flightgear",
        source="builtin",
        difficulty=_difficulty_for_tutorial(file.stem),
        native_difficulty="tutorial",
        tags=("tutorial", aircraft, tutorial_id),
        time_limit_ticks=36_000,
        aircraft=aircraft,
        airport=airport,
        runway=_text(presets, "runway"),
        timeofday=_text(root, "timeofday") or "noon",
        tutorial=title,
        tutorial_file=file.name,
        description=_clean_description(_text(root, "description") or ""),
        startup_args=("--disable-freeze",),
    )


def _difficulty_for_tutorial(name: str) -> str:
    easy = {"preflight", "startup", "taxiing", "runup", "radios", "altimeter", "securing"}
    hard = {"engine-failure", "amphibious-landing", "amphibious-night"}
    if name in easy:
        return "easy"
    if name in hard:
        return "hard"
    return "normal"


def _text(node: ElementTree.Element | None, name: str) -> str | None:
    if node is None:
        return None
    found = node.find(name)
    if found is None or found.text is None:
        return None
    value = found.text.strip()
    return value or None


def _clean_description(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "tutorial"
