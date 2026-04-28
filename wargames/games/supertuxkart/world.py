from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MissionState:
    finished: bool = False
    failed: bool = False


@dataclass(frozen=True)
class RaceState:
    track: str
    laps: int
    num_karts: int
    elapsed_ticks: int
    elapsed_seconds: float = 0.0
    phase: str = ""


@dataclass(frozen=True)
class KartState:
    id: int
    kart: str
    local_player: bool
    rank: int | None = None
    lap: int | None = None
    distance: float | None = None
    distance_down_track: float | None = None
    progress: float | None = None
    x: float | None = None
    y: float | None = None
    z: float | None = None
    velocity_x: float | None = None
    velocity_y: float | None = None
    velocity_z: float | None = None
    speed: float | None = None
    heading: float | None = None
    pitch: float | None = None
    roll: float | None = None
    steering: float | None = None
    throttle: float | None = None
    braking: bool | None = None
    nitro: bool | None = None
    energy: float | None = None
    powerup: str | None = None
    powerup_count: int | None = None
    on_ground: bool | None = None
    on_road: bool | None = None
    finished: bool = False
    eliminated: bool = False
    rescue: bool | None = None


@dataclass(frozen=True)
class SuperTuxKartWorld:
    tick: int
    mission: MissionState
    race: RaceState
    karts: tuple[KartState, ...]
    player: KartState | None = None


def world_from_frame(frame: dict[str, Any]) -> SuperTuxKartWorld:
    race = frame.get("race", {})
    mission = frame.get("mission", {})
    tick = int(frame.get("tick", race.get("elapsed_ticks", 0)))
    karts = tuple(_kart(item) for item in frame.get("karts", ()))
    player = _player(frame, karts)
    return SuperTuxKartWorld(
        tick=tick,
        mission=MissionState(
            finished=bool(mission.get("finished", player.finished if player else False)),
            failed=bool(mission.get("failed", False)),
        ),
        race=RaceState(
            track=str(race.get("track", "")),
            laps=int(race.get("laps", 0)),
            num_karts=int(race.get("num_karts", race.get("numKarts", len(karts)))),
            elapsed_ticks=int(race.get("elapsed_ticks", race.get("elapsedTicks", tick))),
            elapsed_seconds=float(race.get("elapsed_seconds", race.get("elapsedSeconds", 0.0))),
            phase=str(race.get("phase", "")),
        ),
        karts=karts,
        player=player,
    )


def _player(frame: dict[str, Any], karts: tuple[KartState, ...]) -> KartState | None:
    player_id = frame.get("player_kart_id", frame.get("playerKartId"))
    if player_id is not None:
        for kart in karts:
            if kart.id == int(player_id):
                return kart
    for kart in karts:
        if kart.local_player:
            return kart
    return karts[0] if karts else None


def _kart(data: dict[str, Any]) -> KartState:
    return KartState(
        id=int(data.get("id", data.get("world_kart_id", data.get("worldKartId", 0)))),
        kart=str(data.get("kart", data.get("ident", ""))),
        local_player=bool(data.get("local_player", data.get("localPlayer", False))),
        rank=_optional_int(data.get("rank", data.get("position"))),
        lap=_optional_int(data.get("lap")),
        distance=_optional_float(data.get("distance")),
        distance_down_track=_optional_float(
            data.get("distance_down_track", data.get("distanceDownTrack"))
        ),
        progress=_optional_float(data.get("progress")),
        x=_optional_float(data.get("x")),
        y=_optional_float(data.get("y")),
        z=_optional_float(data.get("z")),
        velocity_x=_optional_float(data.get("velocity_x", data.get("velocityX"))),
        velocity_y=_optional_float(data.get("velocity_y", data.get("velocityY"))),
        velocity_z=_optional_float(data.get("velocity_z", data.get("velocityZ"))),
        speed=_optional_float(data.get("speed")),
        heading=_optional_float(data.get("heading")),
        pitch=_optional_float(data.get("pitch")),
        roll=_optional_float(data.get("roll")),
        steering=_optional_float(data.get("steering")),
        throttle=_optional_float(data.get("throttle")),
        braking=_optional_bool(data.get("braking")),
        nitro=_optional_bool(data.get("nitro")),
        energy=_optional_float(data.get("energy")),
        powerup=_optional_str(data.get("powerup")),
        powerup_count=_optional_int(data.get("powerup_count", data.get("powerupCount"))),
        on_ground=_optional_bool(data.get("on_ground", data.get("onGround"))),
        on_road=_optional_bool(data.get("on_road", data.get("onRoad"))),
        finished=bool(data.get("finished", False)),
        eliminated=bool(data.get("eliminated", False)),
        rescue=_optional_bool(data.get("rescue")),
    )


def _optional_bool(value: object) -> bool | None:
    return None if value is None else bool(value)


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)
