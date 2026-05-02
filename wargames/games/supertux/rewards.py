from __future__ import annotations

from wargames.core.missions.rubric import RubricEntry
from wargames.core.world.probe import HiddenStateSnapshot


def delta_coins(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_coins(curr) - _coins(prev), 0))

    return RubricEntry(id="delta_coins", fn=score, weight=weight)


def delta_secrets(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_secrets(curr) - _secrets(prev), 0))

    return RubricEntry(id="delta_secrets", fn=score, weight=weight)


def progress_x(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        before = _x(prev)
        after = _x(curr)
        if before is None or after is None:
            return 0.0
        return max(after - before, 0.0)

    return RubricEntry(id="progress_x", fn=score, weight=weight)


def velocity_x(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        value = getattr(curr.world.player, "vx", None)
        return max(float(value or 0.0), 0.0)

    return RubricEntry(id="velocity_x", fn=score, weight=weight)


def death_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        was_dead = bool(getattr(prev.world.player, "dead", False))
        is_dead = bool(getattr(curr.world.player, "dead", False))
        return -1.0 if is_dead and not was_dead else 0.0

    return RubricEntry(id="death_penalty", fn=score, weight=weight)


def time_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return -float(max(int(curr.tick) - int(prev.tick), 0))

    return RubricEntry(id="time_penalty", fn=score, weight=weight)


def _coins(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(snapshot.world.level, "coins", 0) or 0)


def _secrets(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(snapshot.world.level, "secrets", 0) or 0)


def _x(snapshot: HiddenStateSnapshot) -> float | None:
    value = getattr(snapshot.world.player, "x", None)
    return None if value is None else float(value)
