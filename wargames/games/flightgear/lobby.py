from __future__ import annotations

from collections.abc import Callable

from wargames.core.backend.base import Backend
from wargames.core.runtime.lobby import Lobby, LobbySpec
from wargames.games.flightgear.backend import FlightGearBackend
from wargames.games.flightgear.config import FlightGearConfig
from wargames.games.flightgear.missions import FlightGearMissionSpec


class FlightGearLobby(Lobby):
    def __init__(
        self,
        *,
        config: FlightGearConfig,
        mission: FlightGearMissionSpec,
        seed: int,
        backend_factory: Callable[[FlightGearConfig], Backend] = FlightGearBackend,
    ) -> None:
        super().__init__(
            spec=LobbySpec(id=f"{mission.id}:{seed}", mission=mission, seed=seed, slots=1)
        )
        self.config = config
        self.mission = mission
        self.seed = seed
        self.backend = backend_factory(config)

    async def _start_sessions(self) -> None:
        session = await self.backend.start(self.mission, seed=self.seed)
        self.sessions["p1"] = session

    async def close(self) -> None:
        await super().close()
        await self.backend.close()

    async def __aenter__(self) -> "FlightGearLobby":
        return await self.start()
