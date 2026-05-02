from __future__ import annotations

from wargames.core.missions.rubric import RubricEntry
from wargames.core.world.probe import HiddenStateSnapshot


def delta_kills(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_kills(curr) - _kills(prev), 0))

    return RubricEntry(id="delta_kills", fn=score, weight=weight)


def delta_items(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_items(curr) - _items(prev), 0))

    return RubricEntry(id="delta_items", fn=score, weight=weight)


def delta_secrets(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return float(max(_secrets(curr) - _secrets(prev), 0))

    return RubricEntry(id="delta_secrets", fn=score, weight=weight)


def health_preservation(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return max(float(_health(curr)), 0.0) / 100.0

    return RubricEntry(id="health_preservation", fn=score, weight=weight)


def damage_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return -float(max(_damage(curr) - _damage(prev), 0))

    return RubricEntry(id="damage_penalty", fn=score, weight=weight)


def time_penalty(weight: float = 1.0) -> RubricEntry:
    async def score(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
        return -float(max(int(curr.tick) - int(prev.tick), 0))

    return RubricEntry(id="time_penalty", fn=score, weight=weight)


def _level(snapshot: HiddenStateSnapshot) -> object:
    return snapshot.world.level


def _player(snapshot: HiddenStateSnapshot) -> object:
    return snapshot.world.player


def _kills(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(_level(snapshot), "kills", 0) or 0)


def _items(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(_level(snapshot), "items", 0) or 0)


def _secrets(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(_level(snapshot), "secrets", 0) or 0)


def _health(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(_player(snapshot), "health", 0) or 0)


def _damage(snapshot: HiddenStateSnapshot) -> int:
    return int(getattr(_player(snapshot), "damage_taken", 0) or 0)
