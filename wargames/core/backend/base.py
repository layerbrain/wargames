from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar, Protocol

from wargames.core.config import WarGamesConfig
from wargames.core.control.cua import ArenaAction
from wargames.core.missions.spec import MissionSpec
from wargames.core.runtime.observation import Observation
from wargames.core.runtime.result import MissionSummary, StepResult


class BackendSession(Protocol):
    id: str
    mission: MissionSpec
    seed: int

    async def step(self, action: ArenaAction) -> StepResult: ...

    async def observe(self) -> Observation: ...

    async def summary(self) -> MissionSummary: ...

    async def close(self) -> None: ...


class Backend(ABC):
    game: ClassVar[str]

    def __init__(self, config: WarGamesConfig) -> None:
        self.config = config

    async def bootstrap(self) -> None:
        """Prepare game-specific runtime dependencies before sessions start."""

    @abstractmethod
    def missions(self) -> tuple[MissionSpec, ...]: ...

    def export_missions(self, output_dir: str | Path) -> tuple[Path, ...]:
        raise NotImplementedError(f"{self.game} does not support mission export")

    @abstractmethod
    def supports(self, mission: MissionSpec) -> bool: ...

    @abstractmethod
    async def start(self, mission: MissionSpec, *, seed: int) -> BackendSession: ...

    @abstractmethod
    async def close(self) -> None: ...

    async def __aenter__(self) -> "Backend":
        await self.bootstrap()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
