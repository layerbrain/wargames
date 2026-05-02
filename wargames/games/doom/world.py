from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MissionState:
    finished: bool = False
    failed: bool = False


@dataclass(frozen=True)
class LevelState:
    map: str
    episode: int | None
    map_number: int
    skill: int
    elapsed_ticks: int
    kills: int
    total_kills: int
    items: int
    total_items: int
    secrets: int
    total_secrets: int


@dataclass(frozen=True)
class PlayerState:
    x: float | None
    y: float | None
    angle: float | None
    health: int
    armor: int
    ammo: tuple[int, ...]
    weapons: tuple[bool, ...]
    keys: tuple[bool, ...]
    damage_taken: int
    dead: bool


@dataclass(frozen=True)
class DoomWorld:
    tick: int
    mission: MissionState
    level: LevelState
    player: PlayerState


def world_from_frame(frame: dict[str, Any]) -> DoomWorld:
    mission = frame.get("mission", {})
    level = frame.get("level", {})
    player = frame.get("player", {})
    return DoomWorld(
        tick=int(frame.get("tick", level.get("elapsed_ticks", 0)) or 0),
        mission=MissionState(
            finished=bool(mission.get("finished", False)),
            failed=bool(mission.get("failed", False)),
        ),
        level=LevelState(
            map=str(level.get("map", "")),
            episode=_optional_int(level.get("episode")),
            map_number=int(level.get("map_number", 0) or 0),
            skill=int(level.get("skill", 0) or 0),
            elapsed_ticks=int(level.get("elapsed_ticks", frame.get("tick", 0)) or 0),
            kills=int(level.get("kills", 0) or 0),
            total_kills=int(level.get("total_kills", 0) or 0),
            items=int(level.get("items", 0) or 0),
            total_items=int(level.get("total_items", 0) or 0),
            secrets=int(level.get("secrets", 0) or 0),
            total_secrets=int(level.get("total_secrets", 0) or 0),
        ),
        player=PlayerState(
            x=_optional_float(player.get("x")),
            y=_optional_float(player.get("y")),
            angle=_optional_float(player.get("angle")),
            health=int(player.get("health", 0) or 0),
            armor=int(player.get("armor", 0) or 0),
            ammo=tuple(int(value) for value in player.get("ammo", ())),
            weapons=tuple(bool(value) for value in player.get("weapons", ())),
            keys=tuple(bool(value) for value in player.get("keys", ())),
            damage_taken=int(player.get("damage_taken", 0) or 0),
            dead=bool(player.get("dead", False)),
        ),
    )


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)
