from __future__ import annotations

from wargames.core.missions.rubric import RubricEntry
from wargames.core.world.probe import HiddenStateSnapshot


def delta_score(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_score(curr) - _score(prev), 0))

    return RubricEntry(id="delta_score", fn=score, weight=weight)


def delta_hits(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_hits(curr) - _hits(prev), 0))

    return RubricEntry(id="delta_hits", fn=score, weight=weight)


def delta_combo(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_combo(curr) - _combo(prev), 0))

    return RubricEntry(id="delta_combo", fn=score, weight=weight)


def delta_accuracy(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_accuracy(curr) - _accuracy(prev), 0.0))

    return RubricEntry(id="delta_accuracy", fn=score, weight=weight)


def miss_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return -float(max(_misses(curr) - _misses(prev), 0))

    return RubricEntry(id="miss_penalty", fn=score, weight=weight)


def health_loss_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return -float(max(_health(prev) - _health(curr), 0.0))

    return RubricEntry(id="health_loss_penalty", fn=score, weight=weight)


def time_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return -float(max(int(curr.tick) - int(prev.tick), 0))

    return RubricEntry(id="time_penalty", fn=score, weight=weight)


def _score(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(snapshot.world.gameplay, "score", 0) or 0)


def _hits(snapshot: HiddenStateSnapshot) -> int:
    judgements = snapshot.world.judgements
    return int(
        getattr(judgements, "marv", 0)
        + getattr(judgements, "perf", 0)
        + getattr(judgements, "great", 0)
        + getattr(judgements, "good", 0)
        + getattr(judgements, "okay", 0)
    )


def _combo(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(snapshot.world.gameplay, "combo", 0) or 0)


def _accuracy(snapshot: HiddenStateSnapshot) -> float:
    return float(getattr(snapshot.world.gameplay, "accuracy", 0.0) or 0.0)


def _misses(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(snapshot.world.judgements, "miss", 0) or 0)


def _health(snapshot: HiddenStateSnapshot) -> float:
    return float(getattr(snapshot.world.gameplay, "health", 0.0) or 0.0)
