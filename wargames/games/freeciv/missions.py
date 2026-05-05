from __future__ import annotations

import bz2
import gzip
import json
import lzma
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wargames.core.missions.catalog import resolve_mission_catalog_path
from wargames.core.missions.spec import MissionDifficulty, MissionSpec

FREECIV_DIFFICULTIES: tuple[MissionDifficulty, ...] = ("easy", "normal", "hard")


@dataclass(frozen=True, kw_only=True)
class FreeCivMissionSpec(MissionSpec):
    scenario_file: str
    ruleset: str = "civ2civ3"
    players: int = 0
    ai_level: str = "normal"
    timeout_seconds: int = 3600
    player_name: str = "wargames"
    launch_mode: str = "client-server"
    description: str = ""

    def __post_init__(self) -> None:
        if not self.scenario_file:
            raise ValueError(f"Freeciv mission must reference a scenario file: {self.id}")

    def startup_script(self) -> str:
        lines = [
            f"set timeout {self.timeout_seconds}",
            "set saveturns 0",
        ]
        return "\n".join(lines) + "\n"


def discover(root: str | Path) -> tuple[FreeCivMissionSpec, ...]:
    scenarios = _scenarios_dir(Path(root))
    if scenarios is None:
        return ()
    missions: list[FreeCivMissionSpec] = []
    for file in sorted(scenarios.glob("*.sav*")):
        mission = _scenario_mission(file)
        if mission is not None:
            missions.append(mission)
    return tuple(missions)


def load_mission_catalog(path: str | Path) -> tuple[FreeCivMissionSpec, ...]:
    root = resolve_mission_catalog_path(path)
    if not root.exists():
        return ()
    missions: list[FreeCivMissionSpec] = []
    for file in sorted(root.glob("*/*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        missions.append(_mission_from_payload(data))
    return tuple(missions)


def extract_mission_catalog(root: str | Path, output_dir: str | Path) -> tuple[Path, ...]:
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


def _scenario_mission(file: Path) -> FreeCivMissionSpec | None:
    sections = _save_sections(_read_save(file))
    scenario = sections.get("scenario", {})
    savefile = sections.get("savefile", {})
    game = sections.get("game", {})
    if _clean_freeciv_text(savefile.get("reason")).casefold() != "scenario":
        return None

    scenario_id = _scenario_id(file)
    title = _clean_freeciv_text(scenario.get("name")) or scenario_id.replace("-", " ").title()
    description = _clean_freeciv_text(scenario.get("description"))
    native_difficulty = _clean_freeciv_text(game.get("level")) or "Normal"
    difficulty = _difficulty(native_difficulty)
    ruleset = _clean_freeciv_text(savefile.get("rulesetdir")) or "civ2civ3"
    player_count = _player_count(sections)
    tags = ("scenario", ruleset, f"players:{player_count}") if player_count else ("scenario", ruleset)
    return FreeCivMissionSpec(
        id=f"freeciv.scenario.{_slug(scenario_id)}",
        title=title,
        game="freeciv",
        source="builtin",
        difficulty=difficulty,
        native_difficulty=native_difficulty,
        tags=tags,
        time_limit_ticks=36_000,
        ruleset=ruleset,
        players=player_count,
        ai_level=difficulty,
        scenario_file=file.name,
        description=description,
    )


def _mission_from_payload(data: Mapping[str, Any]) -> FreeCivMissionSpec:
    return FreeCivMissionSpec(
        id=str(data["id"]),
        title=str(data["title"]),
        game=str(data["game"]),
        source=data.get("source", "builtin"),
        difficulty=data.get("difficulty", "normal"),
        native_difficulty=str(data.get("native_difficulty", "normal")),
        tags=tuple(str(tag) for tag in data.get("tags", ())),
        time_limit_ticks=int(data.get("time_limit_ticks", 36_000)),
        ruleset=str(data.get("ruleset", "civ2civ3")),
        players=int(data.get("players", 0)),
        ai_level=str(data.get("ai_level", "normal")),
        timeout_seconds=int(data.get("timeout_seconds", 3600)),
        player_name=str(data.get("player_name", "wargames")),
        launch_mode=str(data.get("launch_mode", "client-server")),
        scenario_file=str(data["scenario_file"]),
        description=str(data.get("description", "")),
    )


def _mission_payload(mission: FreeCivMissionSpec) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": mission.id,
        "title": mission.title,
        "game": mission.game,
        "source": mission.source,
        "difficulty": mission.difficulty,
        "native_difficulty": mission.native_difficulty,
        "tags": list(mission.tags),
        "time_limit_ticks": mission.time_limit_ticks,
        "ruleset": mission.ruleset,
        "players": mission.players,
        "ai_level": mission.ai_level,
        "timeout_seconds": mission.timeout_seconds,
        "player_name": mission.player_name,
        "launch_mode": mission.launch_mode,
        "scenario_file": mission.scenario_file,
        "description": mission.description,
    }
    return payload


def _scenarios_dir(root: Path) -> Path | None:
    candidates = (
        root if root.name == "scenarios" else None,
        root / "scenarios",
        root / "share" / "games" / "freeciv" / "scenarios",
        root / "usr" / "share" / "games" / "freeciv" / "scenarios",
        Path("/usr/share/games/freeciv/scenarios"),
    )
    for candidate in candidates:
        if candidate is not None and candidate.exists():
            return candidate
    return None


def _save_sections(text: str) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = sections.setdefault(line[1:-1], {})
            continue
        if current is None or "=" not in line:
            continue
        key, _, value = line.partition("=")
        current[key.strip()] = value.strip()
    return sections


def _read_save(path: Path) -> str:
    if path.suffix == ".xz":
        return lzma.decompress(path.read_bytes()).decode("utf-8", errors="replace")
    if path.suffix == ".gz":
        return gzip.decompress(path.read_bytes()).decode("utf-8", errors="replace")
    if path.suffix == ".bz2":
        return bz2.decompress(path.read_bytes()).decode("utf-8", errors="replace")
    return path.read_text(encoding="utf-8", errors="replace")


def _clean_freeciv_text(value: object) -> str:
    text = "" if value is None else str(value).strip()
    translated = re.fullmatch(r'_\("(.*)"\)', text, flags=re.DOTALL)
    if translated:
        text = translated.group(1)
    elif len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1]
    return text.replace(r"\n", "\n").replace(r"\"", '"').strip()


def _scenario_id(file: Path) -> str:
    name = file.name
    for suffix in (".sav.gz", ".sav.xz", ".sav.bz2", ".sav"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return file.stem


def _player_count(sections: Mapping[str, Mapping[str, str]]) -> int:
    game = sections.get("game", {})
    map_section = sections.get("map", {})
    for value in (game.get("nplayers"), map_section.get("startpos_count")):
        try:
            parsed = int(str(value))
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            return parsed
    return sum(1 for section in sections if re.fullmatch(r"player\d+", section))


def _difficulty(level: str) -> MissionDifficulty:
    lowered = level.casefold()
    if lowered == "easy":
        return "easy"
    if lowered == "hard":
        return "hard"
    return "normal"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "scenario"
