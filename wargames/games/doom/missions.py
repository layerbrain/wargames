from __future__ import annotations

import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path

from wargames.core.missions.spec import MissionDifficulty, MissionSpec

DOOM_DIFFICULTIES: tuple[MissionDifficulty, ...] = ("easy", "normal", "hard")

_DIFFICULTY_SETTINGS = {
    "easy": {"skill": 2, "ticks": 12_600},
    "normal": {"skill": 3, "ticks": 21_000},
    "hard": {"skill": 4, "ticks": 31_500},
}


@dataclass(frozen=True)
class DoomMissionSpec(MissionSpec):
    iwad: str = ""
    map: str = "MAP01"
    skill: int = 3
    episode: int | None = None
    map_number: int = 1
    content: str = "freedoom2"


def discover(root: str | Path | None = None) -> tuple[DoomMissionSpec, ...]:
    missions: list[DoomMissionSpec] = []
    for iwad in discover_iwads(root):
        missions.extend(_missions_for_iwad(iwad))
    return tuple(missions)


def discover_iwads(root: str | Path | None = None) -> tuple[Path, ...]:
    roots = _iwad_roots(Path(root).expanduser() if root else None)
    found: list[Path] = []
    for candidate_root in roots:
        for name in ("freedoom2.wad", "freedoom1.wad"):
            candidate = candidate_root / name
            if candidate.exists() and candidate not in found:
                found.append(candidate)
    return tuple(found)


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
                    "iwad": mission.iwad,
                    "map": mission.map,
                    "skill": mission.skill,
                    "episode": mission.episode,
                    "map_number": mission.map_number,
                    "content": mission.content,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return tuple(written)


def load_mission_catalog(path: str | Path) -> tuple[DoomMissionSpec, ...]:
    root = Path(path)
    if not root.exists():
        return ()
    missions: list[DoomMissionSpec] = []
    for file in sorted(root.glob("*/*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        episode_raw = data.get("episode")
        missions.append(
            DoomMissionSpec(
                id=str(data["id"]),
                title=str(data["title"]),
                game=str(data["game"]),
                source=data.get("source", "builtin"),
                difficulty=data.get("difficulty", "normal"),
                native_difficulty=str(data.get("native_difficulty", data.get("skill", 3))),
                tags=tuple(str(tag) for tag in data.get("tags", ())),
                time_limit_ticks=int(data.get("time_limit_ticks", 21_000)),
                iwad=str(data.get("iwad", "")),
                map=str(data.get("map", "MAP01")).upper(),
                skill=int(data.get("skill", 3)),
                episode=None if episode_raw is None else int(episode_raw),
                map_number=int(data.get("map_number", 1)),
                content=str(data.get("content", "freedoom2")),
            )
        )
    return tuple(missions)


def wad_maps(path: str | Path) -> tuple[str, ...]:
    data = Path(path).read_bytes()
    if len(data) < 12 or data[:4] not in {b"IWAD", b"PWAD"}:
        return ()
    count, directory_offset = struct.unpack_from("<II", data, 4)
    maps: list[str] = []
    for index in range(count):
        entry_offset = directory_offset + index * 16
        if entry_offset + 16 > len(data):
            break
        name = data[entry_offset + 8 : entry_offset + 16].split(b"\0", 1)[0].decode(
            "ascii", errors="ignore"
        )
        if _is_map_marker(name):
            maps.append(name.upper())
    return tuple(maps)


def _missions_for_iwad(iwad: Path) -> tuple[DoomMissionSpec, ...]:
    maps = wad_maps(iwad)
    content = iwad.stem.lower()
    missions: list[DoomMissionSpec] = []
    for map_id in maps:
        parsed = _parse_map_id(map_id)
        if parsed is None:
            continue
        episode, map_number = parsed
        for difficulty in DOOM_DIFFICULTIES:
            settings = _DIFFICULTY_SETTINGS[difficulty]
            native = str(settings["skill"])
            mission_id = _mission_id(map_id, difficulty)
            missions.append(
                DoomMissionSpec(
                    id=mission_id,
                    title=f"{_title(content)} {map_id} ({difficulty.title()})",
                    game="doom",
                    source="builtin",
                    difficulty=difficulty,
                    native_difficulty=native,
                    tags=(content, map_id.lower(), "fps", "freedoom"),
                    time_limit_ticks=int(settings["ticks"]),
                    iwad=str(iwad),
                    map=map_id,
                    skill=int(settings["skill"]),
                    episode=episode,
                    map_number=map_number,
                    content=content,
                )
            )
    return tuple(missions)


def _iwad_roots(root: Path | None) -> tuple[Path, ...]:
    roots: list[Path] = []
    if root is not None:
        roots.extend([root, root / "doom", root / "games" / "doom"])
    roots.extend(
        [
            Path("/usr/share/games/doom"),
            Path("/usr/share/doom"),
            Path("/usr/local/share/games/doom"),
        ]
    )
    return tuple(roots)


def _is_map_marker(name: str) -> bool:
    upper = name.upper()
    return re.fullmatch(r"MAP\d\d", upper) is not None or re.fullmatch(r"E\dM\d", upper) is not None


def _parse_map_id(map_id: str) -> tuple[int | None, int] | None:
    if match := re.fullmatch(r"MAP(\d\d)", map_id.upper()):
        return None, int(match.group(1))
    if match := re.fullmatch(r"E(\d)M(\d)", map_id.upper()):
        return int(match.group(1)), int(match.group(2))
    return None


def _mission_id(map_id: str, difficulty: str) -> str:
    if map_id.startswith("MAP"):
        return f"doom.map.{map_id.lower()}.{difficulty}"
    return f"doom.episode.{map_id.lower()}.{difficulty}"


def _title(content: str) -> str:
    return {
        "freedoom1": "Freedoom Phase 1",
        "freedoom2": "Freedoom Phase 2",
    }.get(content, content.replace("-", " ").replace("_", " ").title())
