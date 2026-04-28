from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MissionState:
    elapsed_ticks: int
    elapsed_seconds: float
    finished: bool = False
    failed: bool = False


@dataclass(frozen=True)
class PlayerState:
    id: int
    name: str = ""
    civ: str = ""
    state: str = ""
    team: int | None = None
    population: int = 0
    population_limit: int = 0
    resources: dict[str, int] | None = None
    percent_map_explored: float = 0.0
    units_trained: int = 0
    units_lost: int = 0
    enemy_units_killed: int = 0
    buildings_constructed: int = 0
    buildings_lost: int = 0
    enemy_buildings_destroyed: int = 0


@dataclass(frozen=True)
class EntityState:
    id: int
    template: str
    owner: int
    x: float | None = None
    z: float | None = None
    angle: float | None = None
    hitpoints: float | None = None
    idle: bool | None = None
    stance: str | None = None
    unit_ai_state: str | None = None
    unit_ai_order_data: object | None = None
    foundation_progress: float | None = None
    training_queue: object | None = None


@dataclass(frozen=True)
class ZeroADWorld:
    tick: int
    mission: MissionState
    players: tuple[PlayerState, ...]
    entities: tuple[EntityState, ...]
    map_size: int = 0
    victory_conditions: tuple[str, ...] = ()
    player_id: int = 1
    us: PlayerState | None = None
    enemies: tuple[PlayerState, ...] = ()


def world_from_state(state: dict[str, Any], *, player_id: int = 1) -> ZeroADWorld:
    time_elapsed_ms = _int(state.get("timeElapsed"), 0)
    tick = max(0, time_elapsed_ms // 200)
    players = tuple(_player(index, item) for index, item in enumerate(state.get("players", ())))
    entities = tuple(
        _entity(item)
        for _, item in sorted(
            _entity_items(state.get("entities", {})), key=lambda pair: _int(pair[0], 0)
        )
    )
    us = _player_by_id(players, player_id)
    enemies = tuple(
        player
        for player in players
        if player.id not in {0, player_id} and player.state != "defeated"
    )
    finished = bool(us and us.state == "won")
    failed = bool(us and us.state == "defeated")
    return ZeroADWorld(
        tick=tick,
        mission=MissionState(
            elapsed_ticks=tick,
            elapsed_seconds=time_elapsed_ms / 1000.0,
            finished=finished,
            failed=failed,
        ),
        players=players,
        entities=entities,
        map_size=_int(state.get("mapSize"), 0),
        victory_conditions=tuple(str(item) for item in state.get("victoryConditions", ())),
        player_id=player_id,
        us=us,
        enemies=enemies,
    )


def _player(index: int, data: object) -> PlayerState:
    if not isinstance(data, dict):
        return PlayerState(id=index)
    statistics = data.get("statistics", {})
    if not isinstance(statistics, dict):
        statistics = {}
    resource_counts = data.get("resourceCounts", {})
    resources = (
        {str(key): _int(value, 0) for key, value in resource_counts.items()}
        if isinstance(resource_counts, dict)
        else {}
    )
    return PlayerState(
        id=index,
        name=str(data.get("name", "")),
        civ=str(data.get("civ", "")),
        state=str(data.get("state", "")),
        team=_optional_int(data.get("team")),
        population=_int(data.get("popCount"), 0),
        population_limit=_int(data.get("popLimit"), 0),
        resources=resources,
        percent_map_explored=_float(statistics.get("percentMapExplored"), 0.0),
        units_trained=_nested_total(statistics, "unitsTrained"),
        units_lost=_nested_total(statistics, "unitsLost"),
        enemy_units_killed=_nested_total(statistics, "enemyUnitsKilled"),
        buildings_constructed=_nested_total(statistics, "buildingsConstructed"),
        buildings_lost=_nested_total(statistics, "buildingsLost"),
        enemy_buildings_destroyed=_nested_total(statistics, "enemyBuildingsDestroyed"),
    )


def _entity(data: object) -> EntityState:
    if not isinstance(data, dict):
        return EntityState(id=0, template="", owner=-1)
    position = data.get("position")
    x = z = None
    if isinstance(position, list | tuple) and len(position) >= 2:
        x = _float(position[0], 0.0)
        z = _float(position[1], 0.0)
    return EntityState(
        id=_int(data.get("id"), 0),
        template=str(data.get("template", "")),
        owner=_int(data.get("owner"), -1),
        x=x,
        z=z,
        angle=_optional_float(data.get("angle")),
        hitpoints=_optional_float(data.get("hitpoints")),
        idle=_optional_bool(data.get("idle")),
        stance=_optional_str(data.get("stance")),
        unit_ai_state=_optional_str(data.get("unitAIState")),
        unit_ai_order_data=data.get("unitAIOrderData"),
        foundation_progress=_optional_float(data.get("foundationProgress")),
        training_queue=data.get("trainingQueue"),
    )


def _entity_items(value: object) -> tuple[tuple[object, object], ...]:
    if isinstance(value, dict):
        return tuple(value.items())
    return ()


def _player_by_id(players: tuple[PlayerState, ...], player_id: int) -> PlayerState | None:
    for player in players:
        if player.id == player_id:
            return player
    return None


def _nested_total(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if isinstance(value, dict):
        return _int(value.get("total"), 0)
    return 0


def _optional_bool(value: object) -> bool | None:
    return None if value is None else bool(value)


def _optional_float(value: object) -> float | None:
    return None if value is None else _float(value, 0.0)


def _optional_int(value: object) -> int | None:
    return None if value is None else _int(value, 0)


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)


def _float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
