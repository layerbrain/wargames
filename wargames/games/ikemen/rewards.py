from __future__ import annotations

from wargames.core.missions.rubric import RubricEntry
from wargames.core.world.probe import HiddenStateSnapshot


def damage_dealt(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_life(prev, 2) - _life(curr, 2), 0))

    return RubricEntry(id="damage_dealt", fn=score, weight=weight)


def damage_taken(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return -float(max(_life(prev, 1) - _life(curr, 1), 0))

    return RubricEntry(id="damage_taken", fn=score, weight=weight)


def power_gain(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_power(curr, 1) - _power(prev, 1), 0))

    return RubricEntry(id="power_gain", fn=score, weight=weight)


def time_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return -float(max(int(curr.tick) - int(prev.tick), 0))

    return RubricEntry(id="time_penalty", fn=score, weight=weight)


def _life(snapshot: HiddenStateSnapshot, slot: int) -> int:
    player = snapshot.world.p1 if slot == 1 else snapshot.world.p2
    return int(getattr(player, "life", 0) or 0)


def _power(snapshot: HiddenStateSnapshot, slot: int) -> int:
    player = snapshot.world.p1 if slot == 1 else snapshot.world.p2
    return int(getattr(player, "power", 0) or 0)
