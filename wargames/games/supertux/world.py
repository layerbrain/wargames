from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MissionState:
    finished: bool = False
    failed: bool = False


@dataclass(frozen=True)
class LevelState:
    file: str
    name: str
    set: str
    elapsed_ticks: int
    coins: int
    total_coins: int
    secrets: int
    total_secrets: int
    target_time_seconds: float | None


@dataclass(frozen=True)
class PlayerState:
    x: float | None
    y: float | None
    vx: float | None
    vy: float | None
    coins: int
    bonus: str
    alive: bool
    dead: bool
    winning: bool


@dataclass(frozen=True)
class SuperTuxWorld:
    tick: int
    mission: MissionState
    level: LevelState
    player: PlayerState


def world_from_frame(frame: dict[str, Any]) -> SuperTuxWorld:
    mission = frame.get("mission", {})
    level = frame.get("level", {})
    player = frame.get("player", {})
    return SuperTuxWorld(
        tick=int(frame.get("tick", level.get("elapsed_ticks", 0)) or 0),
        mission=MissionState(
            finished=bool(mission.get("finished", False)),
            failed=bool(mission.get("failed", False)),
        ),
        level=LevelState(
            file=str(level.get("file", "")),
            name=str(level.get("name", "")),
            set=str(level.get("set", "")),
            elapsed_ticks=int(level.get("elapsed_ticks", frame.get("tick", 0)) or 0),
            coins=int(level.get("coins", 0) or 0),
            total_coins=int(level.get("total_coins", 0) or 0),
            secrets=int(level.get("secrets", 0) or 0),
            total_secrets=int(level.get("total_secrets", 0) or 0),
            target_time_seconds=_optional_float(level.get("target_time_seconds")),
        ),
        player=PlayerState(
            x=_optional_float(player.get("x")),
            y=_optional_float(player.get("y")),
            vx=_optional_float(player.get("vx")),
            vy=_optional_float(player.get("vy")),
            coins=int(player.get("coins", 0) or 0),
            bonus=str(player.get("bonus", "")),
            alive=bool(player.get("alive", False)),
            dead=bool(player.get("dead", False)),
            winning=bool(player.get("winning", False)),
        ),
    )


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)
