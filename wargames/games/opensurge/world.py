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
    act: int
    elapsed_ticks: int
    elapsed_seconds: float
    width: float
    height: float
    target_time_seconds: float | None


@dataclass(frozen=True)
class PlayerState:
    x: float | None
    y: float | None
    xsp: float | None
    ysp: float | None
    gsp: float | None
    speed: float | None
    rings: int
    score: int
    lives: int
    alive: bool
    dying: bool
    winning: bool
    rolling: bool
    jumping: bool


@dataclass(frozen=True)
class OpenSurgeWorld:
    tick: int
    mission: MissionState
    level: LevelState
    player: PlayerState


def world_from_frame(frame: dict[str, Any]) -> OpenSurgeWorld:
    mission = frame.get("mission", {})
    level = frame.get("level", {})
    player = frame.get("player", {})
    return OpenSurgeWorld(
        tick=int(frame.get("tick", level.get("elapsed_ticks", 0)) or 0),
        mission=MissionState(
            finished=bool(mission.get("finished", False)),
            failed=bool(mission.get("failed", False)),
        ),
        level=LevelState(
            file=str(level.get("file", "")),
            name=str(level.get("name", "")),
            act=int(level.get("act", 1) or 1),
            elapsed_ticks=int(level.get("elapsed_ticks", frame.get("tick", 0)) or 0),
            elapsed_seconds=float(level.get("elapsed_seconds", 0.0) or 0.0),
            width=float(level.get("width", 0.0) or 0.0),
            height=float(level.get("height", 0.0) or 0.0),
            target_time_seconds=_optional_float(level.get("target_time_seconds")),
        ),
        player=PlayerState(
            x=_optional_float(player.get("x")),
            y=_optional_float(player.get("y")),
            xsp=_optional_float(player.get("xsp")),
            ysp=_optional_float(player.get("ysp")),
            gsp=_optional_float(player.get("gsp")),
            speed=_optional_float(player.get("speed")),
            rings=int(player.get("rings", 0) or 0),
            score=int(player.get("score", 0) or 0),
            lives=int(player.get("lives", 0) or 0),
            alive=bool(player.get("alive", False)),
            dying=bool(player.get("dying", False)),
            winning=bool(player.get("winning", False)),
            rolling=bool(player.get("rolling", False)),
            jumping=bool(player.get("jumping", False)),
        ),
    )


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)
