from __future__ import annotations

from wargames.core.missions.rubric import RubricEntry
from wargames.core.world.probe import HiddenStateSnapshot


def delta_city_count(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(_city_count(curr) - _city_count(prev))

    return RubricEntry(id="delta_city_count", fn=score, weight=weight)


def delta_unit_count(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(_unit_count(curr) - _unit_count(prev))

    return RubricEntry(id="delta_unit_count", fn=score, weight=weight)


def delta_gold(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(_gold(curr) - _gold(prev))

    return RubricEntry(id="delta_gold", fn=score, weight=weight)


def delta_known_tiles(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(_known_tiles(curr) - _known_tiles(prev))

    return RubricEntry(id="delta_known_tiles", fn=score, weight=weight)


def turn_progress(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(int(curr.tick) - int(prev.tick), 0))

    return RubricEntry(id="turn_progress", fn=score, weight=weight)


def _player(snapshot: HiddenStateSnapshot) -> object | None:
    return getattr(snapshot.world, "us", None)


def _city_count(snapshot: HiddenStateSnapshot) -> int:
    player = _player(snapshot)
    return int(getattr(player, "city_count", 0) or 0)


def _unit_count(snapshot: HiddenStateSnapshot) -> int:
    player = _player(snapshot)
    return int(getattr(player, "unit_count", 0) or 0)


def _gold(snapshot: HiddenStateSnapshot) -> int:
    player = _player(snapshot)
    return int(getattr(player, "gold", 0) or 0)


def _known_tiles(snapshot: HiddenStateSnapshot) -> int:
    player = _player(snapshot)
    return int(getattr(player, "known_tiles", 0) or 0)
