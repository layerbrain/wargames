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
        _fallback_mission(
            id="freeciv.duel.tiny.easy",
            title="Tiny Duel",
            difficulty="easy",
            tags=("players:2", "tiny"),
            time_limit_ticks=120,
            map_size=4,
            xsize=40,
            ysize=30,
            players=2,
        ),
        _fallback_mission(
            id="freeciv.builder.tiny.easy",
            title="Builder Opening",
            difficulty="easy",
            tags=("economy", "players:2"),
            time_limit_ticks=160,
            map_size=4,
            xsize=44,
            ysize=34,
            players=2,
            server_settings={"startunits": "cwsxx"},
        ),
        _fallback_mission(
            id="freeciv.scout-contact.tiny.easy",
            title="Scout Contact",
            difficulty="easy",
            tags=("exploration", "players:2"),
            time_limit_ticks=160,
            map_size=4,
            xsize=44,
            ysize=32,
            players=2,
            server_settings={"startunits": "cwx"},
        ),
        _fallback_mission(
            id="freeciv.settler-race.tiny.easy",
            title="Settler Race",
            difficulty="easy",
            tags=("settlement", "players:2"),
            time_limit_ticks=180,
            map_size=4,
            xsize=48,
            ysize=34,
            players=2,
            server_settings={"startunits": "ccwwx"},
        ),
        _fallback_mission(
            id="freeciv.coastal-opening.tiny.easy",
            title="Coastal Opening",
            difficulty="easy",
            tags=("coastal", "players:2"),
            time_limit_ticks=180,
            map_size=4,
            xsize=50,
            ysize=34,
            players=2,
        ),
        _fallback_mission(
            id="freeciv.frontier-three.small.easy",
            title="Frontier Three",
            difficulty="easy",
            tags=("frontier", "players:3"),
            time_limit_ticks=200,
            map_size=4,
            xsize=52,
            ysize=36,
            players=3,
        ),
        _fallback_mission(
            id="freeciv.research-start.small.easy",
            title="Research Start",
            difficulty="easy",
            tags=("science", "players:3"),
            time_limit_ticks=200,
            map_size=4,
            xsize=52,
            ysize=38,
            players=3,
            server_settings={"techlevel": 1},
        ),
        _fallback_mission(
            id="freeciv.expansion-small.easy",
            title="Small Expansion",
            difficulty="easy",
            tags=("expansion", "players:3"),
            time_limit_ticks=220,
            map_size=5,
            xsize=56,
            ysize=38,
            players=3,
            server_settings={"startunits": "ccwxx"},
        ),
        _fallback_mission(
            id="freeciv.sparse-duel.small.easy",
            title="Sparse Duel",
            difficulty="easy",
            tags=("exploration", "sparse", "players:2"),
            time_limit_ticks=220,
            map_size=5,
            xsize=58,
            ysize=40,
            players=2,
        ),
        _fallback_mission(
            id="freeciv.compact-three.tiny.easy",
            title="Compact Three",
            difficulty="easy",
            tags=("crowded", "players:3"),
            time_limit_ticks=180,
            map_size=4,
            xsize=44,
            ysize=32,
            players=3,
        ),
        _fallback_mission(
            id="freeciv.continents.small.normal",
            title="Small Continents",
            difficulty="normal",
            tags=("exploration", "players:4"),
            time_limit_ticks=240,
            map_size=5,
            xsize=56,
            ysize=40,
            players=4,
        ),
        _fallback_mission(
            id="freeciv.science.small.normal",
            title="Science Race",
            difficulty="normal",
            tags=("science", "players:4"),
            time_limit_ticks=260,
            map_size=5,
            xsize=56,
            ysize=42,
            players=4,
            server_settings={"techlevel": 1},
        ),
        _fallback_mission(
            id="freeciv.frontier.small.normal",
            title="Small Frontier",
            difficulty="normal",
            tags=("frontier", "players:3"),
            time_limit_ticks=260,
            map_size=5,
            xsize=58,
            ysize=40,
            players=3,
        ),
        _fallback_mission(
            id="freeciv.trade-triangle.small.normal",
            title="Trade Triangle",
            difficulty="normal",
            tags=("economy", "players:3"),
            time_limit_ticks=280,
            map_size=5,
            xsize=60,
            ysize=42,
            players=3,
            server_settings={"techlevel": 1},
        ),
        _fallback_mission(
            id="freeciv.four-way-contact.small.normal",
            title="Four-Way Contact",
            difficulty="normal",
            tags=("contact", "players:4"),
            time_limit_ticks=280,
            map_size=5,
            xsize=60,
            ysize=42,
            players=4,
        ),
        _fallback_mission(
            id="freeciv.republic-race.small.normal",
            title="Republic Race",
            difficulty="normal",
            tags=("science", "government", "players:4"),
            time_limit_ticks=300,
            map_size=5,
            xsize=60,
            ysize=44,
            players=4,
            server_settings={"techlevel": 2},
        ),
        _fallback_mission(
            id="freeciv.long-game.small.normal",
            title="Long Small Game",
            difficulty="normal",
            tags=("long_horizon", "players:4"),
            time_limit_ticks=320,
            map_size=5,
            xsize=62,
            ysize=44,
            players=4,
        ),
        _fallback_mission(
            id="freeciv.open-map.small.normal",
            title="Open Map",
            difficulty="normal",
            tags=("wide_map", "players:4"),
            time_limit_ticks=300,
            map_size=5,
            xsize=64,
            ysize=44,
            players=4,
        ),
        _fallback_mission(
            id="freeciv.compact-four.small.normal",
            title="Compact Four",
            difficulty="normal",
            tags=("crowded", "players:4"),
            time_limit_ticks=260,
            map_size=4,
            xsize=52,
            ysize=38,
            players=4,
        ),
        _fallback_mission(
            id="freeciv.builder-four.small.normal",
            title="Builder Four",
            difficulty="normal",
            tags=("economy", "settlement", "players:4"),
            time_limit_ticks=300,
            map_size=5,
            xsize=60,
            ysize=42,
            players=4,
            server_settings={"startunits": "ccwsxx"},
        ),
        _fallback_mission(
            id="freeciv.crowded-empire.hard",
            title="Crowded Empire",
            difficulty="hard",
            tags=("crowded", "players:6"),
            time_limit_ticks=320,
            map_size=5,
            xsize=60,
            ysize=44,
            players=6,
        ),
        _fallback_mission(
            id="freeciv.domination.standard.hard",
            title="Standard Domination",
            difficulty="hard",
            tags=("domination", "players:7"),
            time_limit_ticks=360,
            map_size=6,
            xsize=72,
            ysize=48,
            players=7,
        ),
        _fallback_mission(
            id="freeciv.seven-fronts.standard.hard",
            title="Seven Fronts",
            difficulty="hard",
            tags=("contact", "players:7"),
            time_limit_ticks=360,
            map_size=6,
            xsize=72,
            ysize=50,
            players=7,
        ),
        _fallback_mission(
            id="freeciv.science-pressure.standard.hard",
            title="Science Pressure",
            difficulty="hard",
            tags=("science", "players:6"),
            time_limit_ticks=360,
            map_size=6,
            xsize=70,
            ysize=48,
            players=6,
            server_settings={"techlevel": 2},
        ),
        _fallback_mission(
            id="freeciv.expansion-pressure.standard.hard",
            title="Expansion Pressure",
            difficulty="hard",
            tags=("expansion", "players:6"),
            time_limit_ticks=380,
            map_size=6,
            xsize=72,
            ysize=50,
            players=6,
            server_settings={"startunits": "ccwxx"},
        ),
        _fallback_mission(
            id="freeciv.survival-small.hard",
            title="Small Survival",
            difficulty="hard",
            tags=("crowded", "survival", "players:6"),
            time_limit_ticks=340,
            map_size=5,
            xsize=58,
            ysize=42,
            players=6,
        ),
        _fallback_mission(
            id="freeciv.recovery-small.hard",
            title="Recovery Start",
            difficulty="hard",
            tags=("recovery", "players:5"),
            time_limit_ticks=340,
            map_size=5,
            xsize=60,
            ysize=42,
            players=5,
            server_settings={"startunits": "cwx"},
        ),
        _fallback_mission(
            id="freeciv.wide-standard.hard",
            title="Wide Standard",
            difficulty="hard",
            tags=("wide_map", "players:6"),
            time_limit_ticks=400,
            map_size=6,
            xsize=76,
            ysize=52,
            players=6,
        ),
        _fallback_mission(
            id="freeciv.compact-brawl.hard",
            title="Compact Brawl",
            difficulty="hard",
            tags=("crowded", "players:7"),
            time_limit_ticks=320,
            map_size=5,
            xsize=58,
            ysize=42,
            players=7,
        ),
        _fallback_mission(
            id="freeciv.marathon-standard.hard",
            title="Marathon Standard",
            difficulty="hard",
            tags=("long_horizon", "players:7"),
            time_limit_ticks=420,
            map_size=6,
            xsize=74,
            ysize=52,
            players=7,
        ),
    )


def _fallback_mission(
    *,
    id: str,
    title: str,
    difficulty: MissionDifficulty,
    tags: tuple[str, ...],
    time_limit_ticks: int,
    map_size: int,
    xsize: int,
    ysize: int,
    players: int,
    server_settings: Mapping[str, Any] | None = None,
) -> FreeCivMissionSpec:
    return FreeCivMissionSpec(
        id=id,
        title=title,
        game="freeciv",
        source="builtin",
        difficulty=difficulty,
        native_difficulty=difficulty,
        tags=("turn_based", "strategy", *tags),
        time_limit_ticks=time_limit_ticks,
        map_size=map_size,
        xsize=xsize,
        ysize=ysize,
        players=players,
        ai_level=difficulty,
        server_settings=server_settings,
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
