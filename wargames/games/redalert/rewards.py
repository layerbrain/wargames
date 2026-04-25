from __future__ import annotations

import math

from wargames.core.missions.rubric import RubricEntry
from wargames.core.world.probe import HiddenStateSnapshot


def delta_cash(weight: float = 0.001) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return curr.world.us.cash - prev.world.us.cash

    return RubricEntry(id="delta_cash", fn=score, weight=weight)


def delta_units_killed(weight: float = 0.01) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return curr.world.us.units_killed - prev.world.us.units_killed

    return RubricEntry(id="delta_units_killed", fn=score, weight=weight)


def delta_buildings_lost(weight: float = -0.02) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return curr.world.us.buildings_lost - prev.world.us.buildings_lost

    return RubricEntry(id="delta_buildings_lost", fn=score, weight=weight)


def scout_distance(weight: float = 0.0001) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        prev_tiles = set(prev.world.visible_tiles)
        curr_tiles = set(curr.world.visible_tiles)
        if curr_tiles:
            return float(len(curr_tiles - prev_tiles))
        visible_enemy = [unit for unit in curr.world.units if unit.owner.id == curr.world.enemy.id and unit.visible]
        if not visible_enemy:
            return 0.0
        own = [unit for unit in curr.world.units if unit.owner.id == curr.world.us.id]
        if not own:
            return 0.0
        best = min(math.dist((a.x, a.y), (b.x, b.y)) for a in own for b in visible_enemy)
        return 1.0 / max(best, 1.0)

    return RubricEntry(id="scout_distance", fn=score, weight=weight)
