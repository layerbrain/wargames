from __future__ import annotations

from wargames.core.missions.rubric import RubricEntry
from wargames.core.world.probe import HiddenStateSnapshot


def delta_resources(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(_resource_total(curr) - _resource_total(prev))

    return RubricEntry(id="delta_resources", fn=score, weight=weight)


def delta_population(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(_population(curr) - _population(prev))

    return RubricEntry(id="delta_population", fn=score, weight=weight)


def enemy_damage(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return max(_enemy_hitpoints(prev) - _enemy_hitpoints(curr), 0.0)

    return RubricEntry(id="enemy_damage", fn=score, weight=weight)


def _resource_total(snapshot: HiddenStateSnapshot) -> int:
    player = getattr(snapshot.world, "us", None)
    resources = getattr(player, "resources", None)
    if not isinstance(resources, dict):
        return 0
    return sum(int(value) for value in resources.values())


def _population(snapshot: HiddenStateSnapshot) -> int:
    player = getattr(snapshot.world, "us", None)
    return int(getattr(player, "population", 0) or 0)


def _enemy_hitpoints(snapshot: HiddenStateSnapshot) -> float:
    player_id = int(getattr(snapshot.world, "player_id", 1))
    total = 0.0
    for entity in getattr(snapshot.world, "entities", ()):
        if int(getattr(entity, "owner", -1)) in {0, player_id}:
            continue
        hitpoints = getattr(entity, "hitpoints", None)
        if hitpoints is not None:
            total += float(hitpoints)
    return total
