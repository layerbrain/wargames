from __future__ import annotations

from collections.abc import Callable

from wargames.core.backend.base import Backend
from wargames.core.runtime.lobby import Lobby, LobbySpec
from wargames.games.redalert.backend import RedAlertBackend
from wargames.games.redalert.config import RedAlertConfig
from wargames.games.redalert.missions import RedAlertMissionSpec


class RedAlertLobby(Lobby):
    MIN_SLOTS = 2
    MAX_SLOTS = 8
    FACTIONS = ("allies", "soviet", "random")

    def __init__(
        self,
        *,
        config: RedAlertConfig,
        mission: RedAlertMissionSpec,
        seed: int,
        backend_factory: Callable[[RedAlertConfig], Backend] = RedAlertBackend,
    ) -> None:
        if mission.player_slots < self.MIN_SLOTS or mission.player_slots > self.MAX_SLOTS:
            raise ValueError(
                f"RedAlert lobby slots must be between {self.MIN_SLOTS} and {self.MAX_SLOTS}"
            )
        super().__init__(
            spec=LobbySpec(
                id=f"{mission.id}:{seed}", mission=mission, seed=seed, slots=mission.player_slots
            ),
            faction_choices=self.FACTIONS,
        )
        self.config = config
        self.mission = mission
        self.seed = seed
        self.backend = backend_factory(config)

    async def _start_sessions(self) -> None:
        for index in range(self.slots):
            slot = f"p{index + 1}"
            session = await self.backend.start(self.mission, seed=self.seed + index)
            self.sessions[slot] = session

    async def close(self) -> None:
        await super().close()
        await self.backend.close()

    async def __aenter__(self) -> "RedAlertLobby":
        return await self.start()
