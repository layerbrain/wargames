from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from wargames.core.missions.spec import MissionDifficulty


@dataclass(frozen=True)
class MissionSuite:
    id: str
    title: str
    game: str
    split: Literal["train", "eval", "debug", "curriculum"]
    missions: tuple[str, ...]
    difficulty_filter: tuple[MissionDifficulty, ...] = ()
