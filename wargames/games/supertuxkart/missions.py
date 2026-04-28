from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from wargames.core.missions.spec import MissionDifficulty, MissionSpec

SUPERTUXKART_DIFFICULTIES: tuple[MissionDifficulty, ...] = ("easy", "normal", "hard")

_DIFFICULTY_SETTINGS = {
    "easy": {"native": "0", "laps": 1, "karts": 3},
    "normal": {"native": "1", "laps": None, "karts": 6},
    "hard": {"native": "2", "laps": None, "karts": 9},
}


@dataclass(frozen=True)
class SuperTuxKartMissionSpec(MissionSpec):
    track: str = ""
    laps: int = 3
    num_karts: int = 6
    kart: str = "tux"
    mode: str = "normal"
    reverse: bool = False
    launch_mode: str = "direct"


def discover(root: str | Path) -> tuple[SuperTuxKartMissionSpec, ...]:
    tracks_dir = _tracks_dir(Path(root))
    if tracks_dir is None:
        return ()

    missions: list[SuperTuxKartMissionSpec] = []
    for track_xml in sorted(tracks_dir.glob("*/track.xml")):
        track = _track_metadata(track_xml)
        if track is None:
            continue
        missions.extend(_mission_variants(track))
    return tuple(missions)


def extract_mission_catalog(root: str | Path, output_dir: str | Path) -> tuple[Path, ...]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*/*.json"):
        stale.unlink()

    written: list[Path] = []
    for mission in discover(root):
        path = out / mission.difficulty / f"{mission.id}.json"
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
                    "track": mission.track,
                    "laps": mission.laps,
                    "num_karts": mission.num_karts,
                    "kart": mission.kart,
                    "mode": mission.mode,
                    "reverse": mission.reverse,
                    "launch_mode": mission.launch_mode,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return tuple(written)


def load_mission_catalog(path: str | Path) -> tuple[SuperTuxKartMissionSpec, ...]:
    root = Path(path)
    if not root.exists():
        return ()
    missions: list[SuperTuxKartMissionSpec] = []
    for file in sorted(root.glob("*/*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        missions.append(
            SuperTuxKartMissionSpec(
                id=str(data["id"]),
                title=str(data["title"]),
                game=str(data["game"]),
                source=data.get("source", "builtin"),
                difficulty=data.get("difficulty", "normal"),
                native_difficulty=str(data.get("native_difficulty", "1")),
                tags=tuple(str(tag) for tag in data.get("tags", ())),
                time_limit_ticks=int(data.get("time_limit_ticks", 36_000)),
                track=str(data.get("track", "")),
                laps=int(data.get("laps", 3)),
                num_karts=int(data.get("num_karts", 6)),
                kart=str(data.get("kart", "tux")),
                mode=str(data.get("mode", "normal")),
                reverse=bool(data.get("reverse", False)),
                launch_mode=str(data.get("launch_mode", "direct")),
            )
        )
    return tuple(missions)


def _mission_variants(track: dict[str, object]) -> list[SuperTuxKartMissionSpec]:
    specs: list[SuperTuxKartMissionSpec] = []
    track_id = str(track["id"])
    title = str(track["title"])
    default_laps = int(track["laps"])
    for difficulty in SUPERTUXKART_DIFFICULTIES:
        settings = _DIFFICULTY_SETTINGS[difficulty]
        laps = int(settings["laps"] or default_laps)
        native = str(settings["native"])
        specs.append(
            SuperTuxKartMissionSpec(
                id=f"supertuxkart.race.{_slug(track_id)}.{difficulty}",
                title=f"{title} ({difficulty.replace('_', ' ').title()})",
                game="supertuxkart",
                source="builtin",
                difficulty=difficulty,
                native_difficulty=native,
                tags=("race", track_id),
                time_limit_ticks=max(1, laps) * 7_200,
                track=track_id,
                laps=laps,
                num_karts=int(settings["karts"]),
                kart="tux",
                mode="normal",
                reverse=False,
            )
        )
    return specs


def _track_metadata(track_xml: Path) -> dict[str, object] | None:
    root = ElementTree.parse(track_xml).getroot()
    attrs = root.attrib
    groups = {group.strip().lower() for group in attrs.get("groups", "").split() if group.strip()}
    if attrs.get("internal", "N").upper() == "Y":
        return None
    if attrs.get("arena", "N").upper() == "Y" or attrs.get("soccer", "N").upper() == "Y":
        return None
    if groups & {"arena", "soccer", "cutscene"}:
        return None
    if "standard" not in groups:
        return None
    laps = _positive_int(attrs.get("default-number-of-laps"), default=3)
    return {
        "id": track_xml.parent.name,
        "title": attrs.get("name") or track_xml.parent.name.replace("_", " ").title(),
        "laps": laps,
    }


def _tracks_dir(root: Path) -> Path | None:
    candidates = (
        root / "data" / "tracks",
        root / "share" / "games" / "supertuxkart" / "data" / "tracks",
        root / "supertuxkart" / "data" / "tracks",
        Path("/usr/share/games/supertuxkart/data/tracks"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _positive_int(value: str | None, *, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "track"
