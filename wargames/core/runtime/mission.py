from __future__ import annotations

from wargames.core.backend.base import BackendSession
from wargames.core.control.cua import ArenaAction
from wargames.core.runtime.observation import Observation
from wargames.core.runtime.result import MissionSummary, StepResult


class Mission:
    def __init__(self, session: BackendSession) -> None:
        self._session = session
        self._closed = False

    @property
    def id(self) -> str:
        return self._session.id

    @property
    def session(self) -> BackendSession:
        return self._session

    async def observe(self) -> Observation:
        return await self._session.observe()

    async def step(self, action: ArenaAction) -> StepResult:
        return await self._session.step(action)

    async def summary(self) -> MissionSummary:
        return await self._session.summary()

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self._session.close()

    async def __aenter__(self) -> "Mission":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
