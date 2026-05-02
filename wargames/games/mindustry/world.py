from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any


@dataclass(frozen=True)
class MissionState:
    finished: bool = False
    failed: bool = False


@dataclass(frozen=True)
class GameState:
    map: str
    wave: int
    enemies: int
    tick: int
    won: bool
    game_over: bool


@dataclass(frozen=True)
class TeamState:
    id: int
    name: str
    cores: int
    units: int
    buildings: int
    items: int
    core_health: float


@dataclass(frozen=True)
class MindustryWorld:
    tick: int
    mission: MissionState
    game: GameState
    us: TeamState
    enemies: tuple[TeamState, ...]
    teams: tuple[TeamState, ...]


def world_from_frame(frame: dict[str, Any]) -> MindustryWorld:
    game = frame.get("game", {})
    mission = frame.get("mission", {})
    teams = tuple(_team(item) for item in frame.get("teams", ()))
    us = next((team for team in teams if team.name == "sharded"), None) or TeamState(
        id=1, name="sharded", cores=0, units=0, buildings=0, items=0, core_health=0.0
    )
    return MindustryWorld(
        tick=int(frame.get("tick", game.get("tick", 0)) or 0),
        mission=MissionState(
            finished=bool(mission.get("finished", False)),
            failed=bool(mission.get("failed", False)),
        ),
        game=GameState(
            map=str(game.get("map", "")),
            wave=int(game.get("wave", 0) or 0),
            enemies=int(game.get("enemies", 0) or 0),
            tick=int(game.get("tick", frame.get("tick", 0)) or 0),
            won=bool(game.get("won", False)),
            game_over=bool(game.get("game_over", False)),
        ),
        us=us,
        enemies=tuple(team for team in teams if team.name != "sharded" and team.cores > 0),
        teams=teams,
    )


def _team(data: Mapping[str, Any]) -> TeamState:
    return TeamState(
        id=int(data.get("id", 0) or 0),
        name=str(data.get("name", "")),
        cores=int(data.get("cores", 0) or 0),
        units=int(data.get("units", 0) or 0),
        buildings=int(data.get("buildings", 0) or 0),
        items=int(data.get("items", 0) or 0),
        core_health=float(data.get("core_health", 0.0) or 0.0),
    )
