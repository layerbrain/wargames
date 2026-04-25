from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

from wargames.core.backend.base import BackendSession
from wargames.core.errors import LobbyFull, LobbyStateError
from wargames.core.missions.spec import MissionSpec


LobbyState = Literal["open", "starting", "ready", "running", "closed"]


@dataclass(frozen=True)
class WorldSetup:
    slot: str
    faction: str | None
    seed: int


@dataclass(frozen=True)
class SessionSpec:
    slot: str
    setup: WorldSetup


@dataclass(frozen=True)
class LobbySpec:
    id: str
    mission: MissionSpec
    seed: int
    slots: int


@dataclass(frozen=True)
class LobbyPlayer:
    slot: str
    name: str
    faction: str | None = None
    ready: bool = False


class Lobby:
    def __init__(self, *, spec: LobbySpec, faction_choices: tuple[str, ...] = ()) -> None:
        self.spec = spec
        self.slots = spec.slots
        self.faction_choices = faction_choices
        self.sessions: dict[str, BackendSession] = {}
        self._players: dict[str, LobbyPlayer] = {}
        self._state: LobbyState = "open"

    @property
    def players(self) -> dict[str, LobbyPlayer]:
        return dict(self._players)

    def state(self) -> LobbyState:
        return self._state

    def join(self, name: str, faction: str | None = None) -> str:
        self._require_state("open")
        if faction is not None:
            self._validate_faction(faction)
        for index in range(1, self.slots + 1):
            slot = f"p{index}"
            if slot not in self._players:
                self._players[slot] = LobbyPlayer(slot=slot, name=name, faction=faction)
                return slot
        raise LobbyFull(f"lobby {self.spec.id} is full")

    def leave(self, slot: str) -> None:
        self._require_state("open")
        self._players.pop(slot, None)

    def select_faction(self, slot: str, faction: str) -> None:
        self._require_state("open")
        self._validate_faction(faction)
        player = self._player(slot)
        self._players[slot] = LobbyPlayer(
            slot=player.slot,
            name=player.name,
            faction=faction,
            ready=player.ready,
        )

    def set_ready(self, slot: str, ready: bool) -> None:
        self._require_state("open")
        player = self._player(slot)
        self._players[slot] = LobbyPlayer(
            slot=player.slot,
            name=player.name,
            faction=player.faction,
            ready=ready,
        )

    def can_start(self) -> bool:
        min_players = getattr(self.spec.mission, "min_players", self.slots)
        return (
            self._state == "open"
            and len(self._players) == self.slots
            and len(self._players) >= min_players
            and all(player.ready for player in self._players.values())
        )

    async def start(self) -> "Lobby":
        if not self.can_start():
            raise LobbyStateError("lobby cannot start until every slot is joined and ready")
        self._state = "starting"
        await self._start_sessions()
        self._state = "ready"
        return self

    async def begin(self) -> None:
        self._require_state("ready")
        self._state = "running"

    async def ticks(self) -> AsyncIterator[int]:
        tick = 0
        while True:
            yield tick
            tick += 1

    async def close(self) -> None:
        self._state = "closed"
        for session in tuple(self.sessions.values()):
            await session.close()
        self.sessions.clear()

    def snapshot(self) -> dict[str, object]:
        return {
            "id": self.spec.id,
            "mission": self.spec.mission.id,
            "seed": self.spec.seed,
            "slots": self.slots,
            "state": self._state,
            "players": [
                {
                    "slot": player.slot,
                    "name": player.name,
                    "faction": player.faction,
                    "ready": player.ready,
                }
                for player in sorted(self._players.values(), key=lambda p: p.slot)
            ],
            "sessions": {slot: session.id for slot, session in sorted(self.sessions.items())},
        }

    async def _start_sessions(self) -> None:
        raise NotImplementedError

    def _player(self, slot: str) -> LobbyPlayer:
        try:
            return self._players[slot]
        except KeyError as exc:
            raise LobbyStateError(f"unknown lobby slot: {slot}") from exc

    def _validate_faction(self, faction: str) -> None:
        if self.faction_choices and faction not in self.faction_choices:
            raise ValueError(f"unknown faction: {faction}")

    def _require_state(self, state: LobbyState) -> None:
        if self._state != state:
            raise LobbyStateError(f"expected lobby state {state}, got {self._state}")

    async def __aenter__(self) -> "Lobby":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
