from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MissionDifficulty = Literal["easy", "normal", "hard", "extra_hard"]


@dataclass(frozen=True)
class MissionSpec:
    id: str
    title: str
    game: str
    source: Literal["builtin", "skirmish", "custom", "mock"]
    time_limit_ticks: int = 36_000
    difficulty: MissionDifficulty = "normal"
    native_difficulty: str | None = None
    tags: tuple[str, ...] = ()
    estimated_duration_ticks: int = 0
