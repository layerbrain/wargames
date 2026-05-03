from __future__ import annotations

from wargames.core.missions.rubric import RubricEntry
from wargames.core.world.probe import HiddenStateSnapshot


def delta_rings(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_rings(curr) - _rings(prev), 0))

    return RubricEntry(id="delta_rings", fn=score, weight=weight)


def delta_score(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_score(curr) - _score(prev), 0))

    return RubricEntry(id="delta_score", fn=score, weight=weight)


def progress_x(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        before = _x(prev)
        after = _x(curr)
        if before is None or after is None:
            return 0.0
        return max(after - before, 0.0)

    return RubricEntry(id="progress_x", fn=score, weight=weight)


def speed(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        value = getattr(curr.world.player, "speed", None)
        return max(float(value or 0.0), 0.0)

    return RubricEntry(id="speed", fn=score, weight=weight)


def death_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        was_dying = bool(getattr(prev.world.player, "dying", False))
        is_dying = bool(getattr(curr.world.player, "dying", False))
        return -1.0 if is_dying and not was_dying else 0.0

    return RubricEntry(id="death_penalty", fn=score, weight=weight)


def time_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return -float(max(int(curr.tick) - int(prev.tick), 0))

    return RubricEntry(id="time_penalty", fn=score, weight=weight)


def _rings(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(snapshot.world.player, "rings", 0) or 0)


def _score(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(snapshot.world.player, "score", 0) or 0)


def _x(snapshot: HiddenStateSnapshot) -> float | None:
    value = getattr(snapshot.world.player, "x", None)
    return None if value is None else float(value)
