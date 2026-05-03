from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MissionState:
    name: str
    finished: bool = False
    failed: bool = False
    completed_count: int = 0
    failed_count: int = 0
    last_completed: str = ""
    last_failed: str = ""


@dataclass(frozen=True)
class PlayerState:
    name: str
    ship: str
    system: str
    landed: bool
    x: float | None
    y: float | None
    vx: float | None
    vy: float | None
    speed: float | None
    direction: float | None
    credits: float
    wealth: float
    fuel: float | None
    jumps: int
    armour: float | None
    shield: float | None
    stress: float | None
    disabled: bool
    energy: float | None
    target: str
    target_distance: float | None


@dataclass(frozen=True)
class NavigationState:
    system: str
    landed: bool
    jumps_available: int
    autonav: bool


@dataclass(frozen=True)
class NaevWorld:
    tick: int
    mission: MissionState
    player: PlayerState
    navigation: NavigationState


def world_from_frame(frame: dict[str, Any]) -> NaevWorld:
    mission = frame.get("mission", {})
    player = frame.get("player", {})
    navigation = frame.get("navigation", {})
    system = str(player.get("system", navigation.get("system", "")))
    landed = bool(player.get("landed", navigation.get("landed", False)))
    jumps = _optional_int(player.get("jumps"))
    return NaevWorld(
        tick=int(frame.get("tick", 0) or 0),
        mission=MissionState(
            name=str(mission.get("name", "")),
            finished=bool(mission.get("finished", False)),
            failed=bool(mission.get("failed", False)),
            completed_count=int(mission.get("completed_count", 0) or 0),
            failed_count=int(mission.get("failed_count", 0) or 0),
            last_completed=str(mission.get("last_completed", "")),
            last_failed=str(mission.get("last_failed", "")),
        ),
        player=PlayerState(
            name=str(player.get("name", "")),
            ship=str(player.get("ship", "")),
            system=system,
            landed=landed,
            x=_optional_float(player.get("x")),
            y=_optional_float(player.get("y")),
            vx=_optional_float(player.get("vx")),
            vy=_optional_float(player.get("vy")),
            speed=_optional_float(player.get("speed")),
            direction=_optional_float(player.get("direction")),
            credits=float(player.get("credits", 0.0) or 0.0),
            wealth=float(player.get("wealth", player.get("credits", 0.0)) or 0.0),
            fuel=_optional_float(player.get("fuel")),
            jumps=int(jumps or 0),
            armour=_optional_float(player.get("armour")),
            shield=_optional_float(player.get("shield")),
            stress=_optional_float(player.get("stress")),
            disabled=bool(player.get("disabled", False)),
            energy=_optional_float(player.get("energy")),
            target=str(player.get("target", "")),
            target_distance=_optional_float(player.get("target_distance")),
        ),
        navigation=NavigationState(
            system=str(navigation.get("system", system)),
            landed=bool(navigation.get("landed", landed)),
            jumps_available=int(navigation.get("jumps_available", jumps or 0) or 0),
            autonav=bool(navigation.get("autonav", False)),
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
