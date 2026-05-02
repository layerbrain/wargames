from __future__ import annotations

from wargames.core.missions.rubric import RubricEntry
from wargames.core.world.probe import HiddenStateSnapshot


def delta_wave(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_wave(curr) - _wave(prev), 0))

    return RubricEntry(id="delta_wave", fn=score, weight=weight)


def delta_items(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_items(curr) - _items(prev), 0))

    return RubricEntry(id="delta_items", fn=score, weight=weight)


def delta_buildings(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_buildings(curr) - _buildings(prev), 0))

    return RubricEntry(id="delta_buildings", fn=score, weight=weight)


def core_health(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return max(float(getattr(curr.world.us, "core_health", 0.0) or 0.0), 0.0)

    return RubricEntry(id="core_health", fn=score, weight=weight)


def enemy_pressure(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return -float(max(int(getattr(curr.world.game, "enemies", 0) or 0), 0))

    return RubricEntry(id="enemy_pressure", fn=score, weight=weight)


def time_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return -float(max(int(curr.tick) - int(prev.tick), 0))

    return RubricEntry(id="time_penalty", fn=score, weight=weight)


def _wave(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(snapshot.world.game, "wave", 0) or 0)


def _items(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(snapshot.world.us, "items", 0) or 0)


def _buildings(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(snapshot.world.us, "buildings", 0) or 0)
