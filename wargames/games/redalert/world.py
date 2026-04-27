from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Player:
    id: str
    faction: str = ""
    cash: int = 0
    power_generated: int = 0
    power_consumed: int = 0
    tech_level: int = 0
    units_killed: int = 0
    buildings_lost: int = 0


@dataclass(frozen=True)
class Unit:
    id: str
    type: str
    owner: Player
    x: int
    y: int
    health: int = 100
    visible: bool = True


@dataclass(frozen=True)
class Building:
    id: str
    type: str
    owner: Player
    x: int
    y: int
    health: int = 100
    visible: bool = True


@dataclass(frozen=True)
class Resource:
    id: str
    x: int
    y: int
    amount: int


@dataclass(frozen=True)
class Objective:
    id: str
    description: str
    finished: bool = False
    failed: bool = False


@dataclass(frozen=True)
class MissionState:
    elapsed_ticks: int
    objectives: tuple[Objective, ...]
    finished: bool = False
    failed: bool = False


@dataclass(frozen=True)
class RedAlertWorld:
    tick: int
    us: Player
    enemy: Player
    units: tuple[Unit, ...]
    buildings: tuple[Building, ...]
    resources: tuple[Resource, ...]
    mission: MissionState
    visible_tiles: tuple[tuple[int, int], ...] = ()


def _player(data: dict[str, Any] | None, default_id: str) -> Player:
    data = data or {}
    return Player(
        id=str(data.get("id", default_id)),
        faction=str(data.get("faction", "")),
        cash=int(data.get("cash", 0)),
        power_generated=int(data.get("power_generated", data.get("powerGenerated", 0))),
        power_consumed=int(data.get("power_consumed", data.get("powerConsumed", 0))),
        tech_level=int(data.get("tech_level", data.get("techLevel", 0))),
        units_killed=int(data.get("units_killed", data.get("unitsKilled", 0))),
        buildings_lost=int(data.get("buildings_lost", data.get("buildingsLost", 0))),
    )


def world_from_frame(frame: dict[str, Any]) -> RedAlertWorld:
    players = {"us": _player(frame.get("us"), "p1"), "enemy": _player(frame.get("enemy"), "p2")}

    def owner(data: dict[str, Any]) -> Player:
        value = data.get("owner", "enemy")
        if isinstance(value, dict):
            return _player(value, str(value.get("id", "owner")))
        return players.get(str(value), players["enemy"])

    units = tuple(
        Unit(
            id=str(item.get("id", "")),
            type=str(item.get("type", "")),
            owner=owner(item),
            x=int(item.get("x", 0)),
            y=int(item.get("y", 0)),
            health=int(item.get("health", 100)),
            visible=bool(item.get("visible", True)),
        )
        for item in frame.get("units", ())
    )
    buildings = tuple(
        Building(
            id=str(item.get("id", "")),
            type=str(item.get("type", "")),
            owner=owner(item),
            x=int(item.get("x", 0)),
            y=int(item.get("y", 0)),
            health=int(item.get("health", 100)),
            visible=bool(item.get("visible", True)),
        )
        for item in frame.get("buildings", ())
    )
    resources = tuple(
        Resource(
            id=str(item.get("id", "")),
            x=int(item.get("x", 0)),
            y=int(item.get("y", 0)),
            amount=int(item.get("amount", 0)),
        )
        for item in frame.get("resources", ())
    )
    mission = frame.get("mission", {})
    objectives = tuple(
        Objective(
            id=str(item.get("id", "")),
            description=str(item.get("description", "")),
            finished=bool(item.get("finished", False)),
            failed=bool(item.get("failed", False)),
        )
        for item in mission.get("objectives", ())
    )
    visible_tiles = tuple(
        tuple(tile) for tile in frame.get("visible_tiles", frame.get("visibleTiles", ()))
    )
    return RedAlertWorld(
        tick=int(frame.get("tick", mission.get("elapsed_ticks", 0))),
        us=players["us"],
        enemy=players["enemy"],
        units=units,
        buildings=buildings,
        resources=resources,
        mission=MissionState(
            elapsed_ticks=int(mission.get("elapsed_ticks", mission.get("elapsedTicks", 0))),
            objectives=objectives,
            finished=bool(mission.get("finished", False)),
            failed=bool(mission.get("failed", False)),
        ),
        visible_tiles=visible_tiles,
    )
