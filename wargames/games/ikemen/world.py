from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MissionState:
    finished: bool = False
    failed: bool = False


@dataclass(frozen=True)
class MatchState:
    round_state: int
    round_no: int
    fight_time: int
    match_over: bool
    winner_team: int


@dataclass(frozen=True)
class PlayerState:
    slot: int
    exists: bool
    name: str
    life: int
    life_max: int
    power: int
    power_max: int
    x: float | None
    y: float | None
    vx: float | None
    vy: float | None
    state_no: int
    move_type: str
    control: bool
    alive: bool
    ai_level: float
    hit_count: int


@dataclass(frozen=True)
class IkemenWorld:
    tick: int
    mission: MissionState
    match: MatchState
    p1: PlayerState
    p2: PlayerState
    players: tuple[PlayerState, ...]


def world_from_frame(frame: dict[str, Any]) -> IkemenWorld:
    match = frame.get("match", {})
    players = tuple(_player(item) for item in frame.get("players", ()))
    p1 = _player_at(players, 1)
    p2 = _player_at(players, 2)
    mission = frame.get("mission", {})
    return IkemenWorld(
        tick=int(frame.get("tick", 0) or 0),
        mission=MissionState(
            finished=bool(mission.get("finished", False)),
            failed=bool(mission.get("failed", False)),
        ),
        match=MatchState(
            round_state=int(match.get("round_state", 0) or 0),
            round_no=int(match.get("round_no", 0) or 0),
            fight_time=int(match.get("fight_time", 0) or 0),
            match_over=bool(match.get("match_over", False)),
            winner_team=int(match.get("winner_team", -1) or -1),
        ),
        p1=p1,
        p2=p2,
        players=players,
    )


def _player(data: Mapping[str, Any]) -> PlayerState:
    return PlayerState(
        slot=int(data.get("slot", 0) or 0),
        exists=bool(data.get("exists", False)),
        name=str(data.get("name", "")),
        life=int(data.get("life", 0) or 0),
        life_max=int(data.get("life_max", 0) or 0),
        power=int(data.get("power", 0) or 0),
        power_max=int(data.get("power_max", 0) or 0),
        x=_optional_float(data.get("x")),
        y=_optional_float(data.get("y")),
        vx=_optional_float(data.get("vx")),
        vy=_optional_float(data.get("vy")),
        state_no=int(data.get("state_no", 0) or 0),
        move_type=str(data.get("move_type", "")),
        control=bool(data.get("control", False)),
        alive=bool(data.get("alive", False)),
        ai_level=float(data.get("ai_level", 0.0) or 0.0),
        hit_count=int(data.get("hit_count", 0) or 0),
    )


def _player_at(players: tuple[PlayerState, ...], slot: int) -> PlayerState:
    return next((player for player in players if player.slot == slot), _player({"slot": slot}))


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)
