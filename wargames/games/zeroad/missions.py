from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from wargames.core.missions.catalog import resolve_mission_catalog_path
from wargames.core.missions.spec import MissionDifficulty, MissionSpec

ZEROAD_DIFFICULTIES: tuple[MissionDifficulty, ...] = ("easy", "normal", "hard")

_DIFFICULTY_SETTINGS = {
    "easy": {"native": "2", "ai_difficulty": 2},
    "normal": {"native": "3", "ai_difficulty": 3},
    "hard": {"native": "5", "ai_difficulty": 5},
}

_CONQUEST_TRIGGER_SCRIPTS = {
    "conquest": ["scripts/ConquestCommon.js", "scripts/Conquest.js"],
    "conquest_units": ["scripts/ConquestCommon.js", "scripts/ConquestUnits.js"],
    "conquest_structures": ["scripts/ConquestCommon.js", "scripts/ConquestStructures.js"],
    "conquest_civic_centres": [
        "scripts/ConquestCommon.js",
        "scripts/ConquestCivicCentres.js",
    ],
}

@dataclass(frozen=True)
class ZeroADMissionSpec(MissionSpec):
    map: str = ""
    map_type: str = "scenario"
    settings: Mapping[str, Any] | None = None
    player_id: int = 1
    ai: str = "petra"
    ai_difficulty: int = 3
    game_speed: float = 1.0
    launch_mode: str = "rl"

    def scenario_config(self, *, seed: int) -> dict[str, Any]:
        settings = _scenario_settings(
            self.settings or {}, seed=seed, ai=self.ai, ai_difficulty=self.ai_difficulty
        )
        settings.setdefault("mapName", self.title)
        settings.setdefault("mapType", self.map_type)
        return {
            "settings": settings,
            "mapType": self.map_type,
            "map": self.map,
            "gameSpeed": self.game_speed,
        }


def discover(root: str | Path) -> tuple[ZeroADMissionSpec, ...]:
    maps_dir = _maps_dir(Path(root))
    if maps_dir is None:
        return ()

    missions: list[ZeroADMissionSpec] = []
    for map_type in ("scenario", "skirmish"):
        directory = maps_dir / _map_type_dir(map_type)
        for map_xml in sorted(directory.glob("*.xml")):
            metadata = _map_metadata(map_xml, map_type=map_type)
            if metadata is None:
                continue
            missions.extend(_mission_variants(metadata))
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


def load_mission_catalog(path: str | Path) -> tuple[ZeroADMissionSpec, ...]:
    root = resolve_mission_catalog_path(path)
    if not root.exists():
        return ()
    missions: list[ZeroADMissionSpec] = []
    for file in sorted(root.glob("*/*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        missions.append(
            ZeroADMissionSpec(
                id=str(data["id"]),
                title=str(data["title"]),
                game=str(data["game"]),
                source=data.get("source", "builtin"),
                difficulty=data.get("difficulty", "normal"),
                native_difficulty=str(data.get("native_difficulty", "3")),
                tags=tuple(str(tag) for tag in data.get("tags", ())),
                time_limit_ticks=int(data.get("time_limit_ticks", 36_000)),
                map=str(data.get("map", "")),
                map_type=str(data.get("map_type", "scenario")),
                settings=data.get("settings") if isinstance(data.get("settings"), dict) else {},
                player_id=int(data.get("player_id", 1)),
                ai=str(data.get("ai", "petra")),
                ai_difficulty=int(data.get("ai_difficulty", 3)),
                game_speed=float(data.get("game_speed", 1.0)),
                launch_mode=str(data.get("launch_mode", "rl")),
            )
        )
    return tuple(missions)


def _mission_variants(map_data: dict[str, Any]) -> list[ZeroADMissionSpec]:
    specs: list[ZeroADMissionSpec] = []
    map_id = str(map_data["id"])
    title = str(map_data["title"])
    for difficulty in ZEROAD_DIFFICULTIES:
        settings = _DIFFICULTY_SETTINGS[difficulty]
        specs.append(
            ZeroADMissionSpec(
                id=f"zeroad.{map_data['map_type']}.{_slug(map_id)}.{difficulty}",
                title=f"{title} ({difficulty.replace('_', ' ').title()})",
                game="zeroad",
                source="builtin",
                difficulty=difficulty,
                native_difficulty=str(settings["native"]),
                tags=tuple(map_data["tags"]),
                time_limit_ticks=36_000,
                map=str(map_data["map"]),
                map_type=str(map_data["map_type"]),
                settings=copy.deepcopy(map_data["settings"]),
                ai_difficulty=int(settings["ai_difficulty"]),
            )
        )
    return specs


def _map_metadata(map_xml: Path, *, map_type: str) -> dict[str, Any] | None:
    root = ElementTree.parse(map_xml).getroot()
    settings_text = root.findtext("ScriptSettings")
    if not settings_text:
        return None
    try:
        settings = json.loads(settings_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(settings, dict):
        return None
    player_count = _playable_player_count(settings.get("PlayerData"))
    if player_count < 2:
        return None
    title = str(settings.get("Name") or map_xml.stem.replace("_", " ").title())
    victory_conditions = _strings(settings.get("VictoryConditions")) or ("conquest",)
    return {
        "id": map_xml.stem,
        "title": title,
        "map_type": map_type,
        "map": f"maps/{_map_type_dir(map_type)}/{map_xml.stem}",
        "settings": settings,
        "tags": (map_type, f"players:{player_count}", *victory_conditions),
    }


def _scenario_settings(
    raw_settings: Mapping[str, Any], *, seed: int, ai: str, ai_difficulty: int
) -> dict[str, Any]:
    settings = copy.deepcopy(dict(raw_settings))
    settings["AISeed"] = seed
    settings["Seed"] = seed
    settings["CheatsEnabled"] = True
    settings.setdefault("Ceasefire", 0)
    settings.setdefault("VictoryConditions", ["conquest"])
    settings["TriggerScripts"] = _trigger_scripts(settings)
    settings["PlayerData"] = _player_data(settings.get("PlayerData"), ai, ai_difficulty)
    return settings


def _trigger_scripts(settings: Mapping[str, Any]) -> list[str]:
    scripts = list(_strings(settings.get("TriggerScripts")))
    if "scripts/TriggerHelper.js" not in scripts:
        scripts.insert(0, "scripts/TriggerHelper.js")
    for condition in _strings(settings.get("VictoryConditions")) or ("conquest",):
        for script in _CONQUEST_TRIGGER_SCRIPTS.get(condition, ()):
            if script not in scripts:
                scripts.append(script)
    return scripts


def _player_data(raw: object, ai: str, ai_difficulty: int) -> list[dict[str, Any]]:
    players = (
        [dict(item) for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []
    )
    while len(players) < 2:
        players.append({"Name": f"Player {len(players) + 1}", "Civ": "spart"})

    for index, player in enumerate(players):
        player.setdefault("Name", f"Player {index + 1}")
        player.setdefault("Civ", "spart")
        player["AIDiff"] = ai_difficulty
        player["AIBehavior"] = "random"
        if index == 0:
            player["AI"] = ""
            player["Team"] = 1
        else:
            player["AI"] = ai
            player["Team"] = 2
    return players


def _mission_payload(mission: ZeroADMissionSpec) -> dict[str, Any]:
    return {
        "id": mission.id,
        "title": mission.title,
        "game": mission.game,
        "source": mission.source,
        "difficulty": mission.difficulty,
        "native_difficulty": mission.native_difficulty,
        "tags": list(mission.tags),
        "time_limit_ticks": mission.time_limit_ticks,
        "map": mission.map,
        "map_type": mission.map_type,
        "settings": dict(mission.settings or {}),
        "player_id": mission.player_id,
        "ai": mission.ai,
        "ai_difficulty": mission.ai_difficulty,
        "game_speed": mission.game_speed,
        "launch_mode": mission.launch_mode,
    }


def _maps_dir(root: Path) -> Path | None:
    candidates = (
        root / "binaries" / "data" / "mods" / "public" / "maps",
        root / "data" / "mods" / "public" / "maps",
        root / "mods" / "public" / "maps",
        root / "share" / "games" / "0ad" / "mods" / "public" / "maps",
        Path("/usr/share/games/0ad/mods/public/maps"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _map_type_dir(map_type: str) -> str:
    return "skirmishes" if map_type == "skirmish" else f"{map_type}s"


def _playable_player_count(raw: object) -> int:
    if not isinstance(raw, list):
        return 0
    return sum(1 for item in raw if isinstance(item, dict) and item.get("Civ") != "gaia")


def _strings(raw: object) -> tuple[str, ...]:
    if isinstance(raw, list):
        return tuple(str(item) for item in raw if item)
    return ()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "map"
