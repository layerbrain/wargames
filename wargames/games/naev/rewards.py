from __future__ import annotations

from wargames.core.missions.rubric import RubricEntry
from wargames.core.world.probe import HiddenStateSnapshot


def delta_credits(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return max(_credits(curr) - _credits(prev), 0.0)

    return RubricEntry(id="delta_credits", fn=score, weight=weight)


def delta_wealth(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return max(_wealth(curr) - _wealth(prev), 0.0)

    return RubricEntry(id="delta_wealth", fn=score, weight=weight)


def delta_mission_completed(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        before = int(getattr(prev.world.mission, "completed_count", 0) or 0)
        after = int(getattr(curr.world.mission, "completed_count", 0) or 0)
        return float(max(after - before, 0))

    return RubricEntry(id="delta_mission_completed", fn=score, weight=weight)


def damage_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        before = _health(prev)
        after = _health(curr)
        if before is None or after is None:
            return 0.0
        return -max(before - after, 0.0)

    return RubricEntry(id="damage_penalty", fn=score, weight=weight)


def fuel_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        before = getattr(prev.world.player, "fuel", None)
        after = getattr(curr.world.player, "fuel", None)
        if before is None or after is None:
            return 0.0
        return -max(float(before) - float(after), 0.0)

    return RubricEntry(id="fuel_penalty", fn=score, weight=weight)


def time_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return -float(max(int(curr.tick) - int(prev.tick), 0))

    return RubricEntry(id="time_penalty", fn=score, weight=weight)


def _credits(snapshot: HiddenStateSnapshot) -> float:
    return float(getattr(snapshot.world.player, "credits", 0.0) or 0.0)


def _wealth(snapshot: HiddenStateSnapshot) -> float:
    return float(getattr(snapshot.world.player, "wealth", _credits(snapshot)) or 0.0)


def _health(snapshot: HiddenStateSnapshot) -> float | None:
    armour = getattr(snapshot.world.player, "armour", None)
    shield = getattr(snapshot.world.player, "shield", None)
    if armour is None and shield is None:
        return None
    return float(armour or 0.0) + float(shield or 0.0)
