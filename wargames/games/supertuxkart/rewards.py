from __future__ import annotations

from wargames.core.missions.rubric import RubricEntry
from wargames.core.world.probe import HiddenStateSnapshot


def delta_progress(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        prev_progress = _progress(prev)
        curr_progress = _progress(curr)
        if prev_progress is None or curr_progress is None:
            return 0.0
        return curr_progress - prev_progress

    return RubricEntry(id="delta_progress", fn=score, weight=weight)


def speed(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        player = getattr(curr.world, "player", None)
        value = getattr(player, "speed", None)
        return 0.0 if value is None else max(float(value), 0.0)

    return RubricEntry(id="speed", fn=score, weight=weight)


def rank_gain(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        prev_rank = _rank(prev)
        curr_rank = _rank(curr)
        if prev_rank is None or curr_rank is None:
            return 0.0
        return float(prev_rank - curr_rank)

    return RubricEntry(id="rank_gain", fn=score, weight=weight)


def off_road_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        player = getattr(curr.world, "player", None)
        if getattr(player, "on_road", None) is False:
            return -1.0
        return 0.0

    return RubricEntry(id="off_road_penalty", fn=score, weight=weight)


def _progress(snapshot: HiddenStateSnapshot) -> float | None:
    player = getattr(snapshot.world, "player", None)
    value = getattr(player, "progress", None)
    return None if value is None else float(value)


def _rank(snapshot: HiddenStateSnapshot) -> int | None:
    player = getattr(snapshot.world, "player", None)
    value = getattr(player, "rank", None)
    return None if value is None else int(value)
