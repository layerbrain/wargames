from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RewardIntent = Literal["maximize", "minimize", "track"]
RewardTiming = Literal["per_step", "terminal"]


@dataclass(frozen=True)
class RewardField:
    path: str
    type: str
    intent: RewardIntent
    description: str


@dataclass(frozen=True)
class RewardPrimitiveSpec:
    id: str
    source_fields: tuple[str, ...]
    default_weight: float
    when: RewardTiming
    description: str


@dataclass(frozen=True)
class GameRewardSchema:
    game: str
    world_type: str
    tick_rate: int
    fields: dict[str, RewardField]
    primitives: dict[str, RewardPrimitiveSpec]

    def primitive(self, id: str) -> RewardPrimitiveSpec:
        if id in self.primitives:
            return self.primitives[id]
        if id.startswith("objective.") and "objective.<id>" in self.primitives:
            return self.primitives["objective.<id>"]
        raise ValueError(f"unknown reward primitive for {self.game}: {id}")

    def validate_primitive(self, id: str) -> None:
        self.primitive(id)
