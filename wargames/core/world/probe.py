from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HiddenStateSnapshot:
    tick: int
    world: Any


class StateProbe(ABC):
    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def next(self) -> HiddenStateSnapshot: ...

    @abstractmethod
    async def latest(self) -> HiddenStateSnapshot | None: ...

    @abstractmethod
    async def close(self) -> None: ...
