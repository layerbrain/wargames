from __future__ import annotations

from math import sqrt

from wargames.core.missions.rubric import RubricEntry
from wargames.core.world.probe import HiddenStateSnapshot


def delta_reward(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(getattr(curr.world, "reward", 0.0) or 0.0)

    return RubricEntry(id="delta_reward", fn=score, weight=weight)


def total_reward(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(getattr(curr.world, "total_reward", 0.0) or 0.0)

    return RubricEntry(id="total_reward", fn=score, weight=weight)


def movement_delta(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        before = _position(prev)
        after = _position(curr)
        if before is None or after is None:
            return 0.0
        return sqrt(sum((after[index] - before[index]) ** 2 for index in range(3)))

    return RubricEntry(id="movement_delta", fn=score, weight=weight)


def voxel_discovery(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_nonzero_nodes(curr) - _nonzero_nodes(prev), 0))

    return RubricEntry(id="voxel_discovery", fn=score, weight=weight)


def time_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return -float(max(int(curr.tick) - int(prev.tick), 0))

    return RubricEntry(id="time_penalty", fn=score, weight=weight)


def _position(snapshot: HiddenStateSnapshot) -> tuple[float, float, float] | None:
    return getattr(snapshot.world.player, "position", None)


def _nonzero_nodes(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(snapshot.world.voxel, "nonzero_nodes", 0) or 0)
