from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

from wargames.core.world.probe import HiddenStateSnapshot

RubricFn = Callable[[HiddenStateSnapshot, HiddenStateSnapshot], float | Awaitable[float]]


@dataclass(frozen=True)
class RewardBreakdown:
    total: float
    entries: dict[str, float]


@dataclass(frozen=True)
class RubricEntry:
    id: str
    fn: RubricFn
    weight: float = 1.0


class Rubric:
    def __init__(self, entries: Sequence[RubricEntry]) -> None:
        ids = [entry.id for entry in entries]
        if len(ids) != len(set(ids)):
            raise ValueError("rubric entry ids must be unique")
        self.entries = tuple(entries)

    async def score(self, prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> RewardBreakdown:
        values: dict[str, float] = {}
        total = 0.0
        for entry in self.entries:
            raw = entry.fn(prev, curr)
            value = await raw if inspect.isawaitable(raw) else raw
            weighted = float(value) * entry.weight
            values[entry.id] = weighted
            total += weighted
        return RewardBreakdown(total=total, entries=values)
