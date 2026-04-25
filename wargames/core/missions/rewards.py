from __future__ import annotations

from wargames.core.missions.rubric import RubricEntry
from wargames.core.world.probe import HiddenStateSnapshot


def _world(snapshot: HiddenStateSnapshot) -> object:
    return snapshot.world


def terminal(weight: float = 1.0, defeat_weight: float = -1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        mission = getattr(_world(curr), "mission", None)
        if mission is None:
            return 0.0
        if getattr(mission, "finished", False):
            return 1.0
        if getattr(mission, "failed", False):
            return defeat_weight / weight if weight else defeat_weight
        return 0.0

    return RubricEntry(id="terminal", fn=score, weight=weight)


def on_objective(id: str, weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        prev_objectives = {getattr(obj, "id", None): obj for obj in getattr(getattr(_world(prev), "mission", None), "objectives", ())}
        curr_objectives = {getattr(obj, "id", None): obj for obj in getattr(getattr(_world(curr), "mission", None), "objectives", ())}
        was_finished = getattr(prev_objectives.get(id), "finished", False)
        is_finished = getattr(curr_objectives.get(id), "finished", False)
        return 1.0 if is_finished and not was_finished else 0.0

    return RubricEntry(id=f"objective.{id}", fn=score, weight=weight)
