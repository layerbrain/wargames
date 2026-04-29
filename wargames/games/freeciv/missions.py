from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wargames.core.missions.spec import MissionDifficulty, MissionSpec

FREECIV_DIFFICULTIES: tuple[MissionDifficulty, ...] = ("easy", "normal", "hard")


@dataclass(frozen=True)
class FreeCivMissionSpec(MissionSpec):
    ruleset: str = "civ2civ3"
    generator: str = "FRACTAL"
    map_size: int = 4
    xsize: int | None = None
    ysize: int | None = None
    players: int = 2
    ai_level: str = "normal"
    timeout_seconds: int = 3600
    player_name: str = "wargames"
    server_settings: Mapping[str, Any] | None = None
    launch_mode: str = "client-server"

    def startup_script(self) -> str:
        settings = dict(self.server_settings or {})
        lines = [
            f"set aifill {self.players}",
            f"set timeout {self.timeout_seconds}",
            f"set generator {self.generator}",
            f"set size {self.map_size}",
            "set saveturns 0",
        ]
        if self.xsize is not None:
            lines.append(f"set xsize {self.xsize}")
        if self.ysize is not None:
            lines.append(f"set ysize {self.ysize}")
        for key, value in sorted(settings.items()):
            lines.append(f"set {key} {_setting_value(value)}")
        for index in range(1, max(self.players, 1)):
            lines.append(f"{self.ai_level} AI*{index}")
        return "\n".join(lines) + "\n"


def load_mission_catalog(path: str | Path) -> tuple[FreeCivMissionSpec, ...]:
    root = Path(path)
    if not root.exists():
        return ()
    missions: list[FreeCivMissionSpec] = []
    for file in sorted(root.glob("*/*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        missions.append(_mission_from_payload(data))
    return tuple(missions)


def extract_mission_catalog(output_dir: str | Path) -> tuple[Path, ...]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*/*.json"):
        stale.unlink()

    written: list[Path] = []
    for mission in fallback_missions():
        path = out / mission.difficulty / f"{mission.id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(_mission_payload(mission), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return tuple(written)


def fallback_missions() -> tuple[FreeCivMissionSpec, ...]:
    return (
        FreeCivMissionSpec(
            id="freeciv.duel.tiny.easy",
            title="Tiny Duel",
            game="freeciv",
            source="builtin",
            difficulty="easy",
            native_difficulty="easy",
            tags=("turn_based", "strategy", "players:2", "tiny"),
            time_limit_ticks=120,
            map_size=4,
            xsize=40,
            ysize=30,
            players=2,
            ai_level="easy",
        ),
        FreeCivMissionSpec(
            id="freeciv.builder.tiny.easy",
            title="Builder Opening",
            game="freeciv",
            source="builtin",
            difficulty="easy",
            native_difficulty="easy",
            tags=("turn_based", "strategy", "economy", "players:2"),
            time_limit_ticks=160,
            map_size=4,
            xsize=44,
            ysize=34,
            players=2,
            ai_level="easy",
            server_settings={"startunits": "cwsxx"},
        ),
        FreeCivMissionSpec(
            id="freeciv.continents.small.normal",
            title="Small Continents",
            game="freeciv",
            source="builtin",
            difficulty="normal",
            native_difficulty="normal",
            tags=("turn_based", "strategy", "exploration", "players:4"),
            time_limit_ticks=240,
            map_size=5,
            xsize=56,
            ysize=40,
            players=4,
            ai_level="normal",
        ),
        FreeCivMissionSpec(
            id="freeciv.science.small.normal",
            title="Science Race",
            game="freeciv",
            source="builtin",
            difficulty="normal",
            native_difficulty="normal",
            tags=("turn_based", "strategy", "science", "players:4"),
            time_limit_ticks=260,
            map_size=5,
            xsize=56,
            ysize=42,
            players=4,
            ai_level="normal",
            server_settings={"techlevel": 1},
        ),
        FreeCivMissionSpec(
            id="freeciv.crowded-empire.hard",
            title="Crowded Empire",
            game="freeciv",
            source="builtin",
            difficulty="hard",
            native_difficulty="hard",
            tags=("turn_based", "strategy", "crowded", "players:6"),
            time_limit_ticks=320,
            map_size=5,
            xsize=60,
            ysize=44,
            players=6,
            ai_level="hard",
        ),
        FreeCivMissionSpec(
            id="freeciv.domination.standard.hard",
            title="Standard Domination",
            game="freeciv",
            source="builtin",
            difficulty="hard",
            native_difficulty="hard",
            tags=("turn_based", "strategy", "domination", "players:7"),
            time_limit_ticks=360,
            map_size=6,
            xsize=72,
            ysize=48,
            players=7,
            ai_level="hard",
        ),
    )


def _mission_from_payload(data: Mapping[str, Any]) -> FreeCivMissionSpec:
    return FreeCivMissionSpec(
        id=str(data["id"]),
        title=str(data["title"]),
        game=str(data["game"]),
        source=data.get("source", "builtin"),
        difficulty=data.get("difficulty", "normal"),
        native_difficulty=str(data.get("native_difficulty", data.get("ai_level", "normal"))),
        tags=tuple(str(tag) for tag in data.get("tags", ())),
        time_limit_ticks=int(data.get("time_limit_ticks", data.get("max_turns", 240))),
        ruleset=str(data.get("ruleset", "civ2civ3")),
        generator=str(data.get("generator", "FRACTAL")),
        map_size=int(data.get("map_size", 4)),
        xsize=_optional_int(data.get("xsize")),
        ysize=_optional_int(data.get("ysize")),
        players=int(data.get("players", 2)),
        ai_level=str(data.get("ai_level", "normal")),
        timeout_seconds=int(data.get("timeout_seconds", 3600)),
        player_name=str(data.get("player_name", "wargames")),
        server_settings=(
            data.get("server_settings") if isinstance(data.get("server_settings"), dict) else {}
        ),
        launch_mode=str(data.get("launch_mode", "client-server")),
    )


def _mission_payload(mission: FreeCivMissionSpec) -> dict[str, object]:
    return {
        "id": mission.id,
        "title": mission.title,
        "game": mission.game,
        "source": mission.source,
        "difficulty": mission.difficulty,
        "native_difficulty": mission.native_difficulty,
        "tags": list(mission.tags),
        "time_limit_ticks": mission.time_limit_ticks,
        "ruleset": mission.ruleset,
        "generator": mission.generator,
        "map_size": mission.map_size,
        "xsize": mission.xsize,
        "ysize": mission.ysize,
        "players": mission.players,
        "ai_level": mission.ai_level,
        "timeout_seconds": mission.timeout_seconds,
        "player_name": mission.player_name,
        "server_settings": dict(mission.server_settings or {}),
        "launch_mode": mission.launch_mode,
    }


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)


def _setting_value(value: object) -> str:
    if isinstance(value, bool):
        return "enabled" if value else "disabled"
    return str(value)
