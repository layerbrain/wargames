from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from wargames.core.backend.base import Backend
from wargames.core.config import WarGamesConfig
from wargames.core.control.cua import ArenaAction
from wargames.core.control.tools import CUA_TOOL_SPECS, ToolSpec, action_from_tool_call
from wargames.core.errors import MissionNotFound
from wargames.core.missions.spec import MissionSpec
from wargames.core.runtime.mission import Mission


@dataclass(frozen=True)
class GameDescriptor:
    id: str
    backend_cls: type[Backend]
    config_cls: type[WarGamesConfig]
    tools: tuple[ToolSpec, ...] = CUA_TOOL_SPECS
    action_from_tool_call: Callable[[str, dict], ArenaAction] = action_from_tool_call


class _MissionCtx:
    def __init__(self, arena: "WarGames", id: str, seed: int) -> None:
        self._arena = arena
        self._id = id
        self._seed = seed
        self._mission: Mission | None = None

    async def __aenter__(self) -> Mission:
        self._mission = await self._arena.start_mission(self._id, seed=self._seed)
        return self._mission

    async def __aexit__(self, *args: object) -> None:
        if self._mission is not None:
            await self._mission.close()


class WarGames:
    @classmethod
    def for_game(cls, game: GameDescriptor, config: WarGamesConfig) -> "WarGames":
        return cls(game.backend_cls(config), game=game)

    def __init__(self, backend: Backend, game: GameDescriptor | None = None) -> None:
        self._backend = backend
        self._game = game

    @property
    def tools(self) -> tuple[ToolSpec, ...]:
        return self._game.tools if self._game is not None else CUA_TOOL_SPECS

    def action_from_tool_call(self, name: str, arguments: dict) -> ArenaAction:
        if self._game is not None:
            return self._game.action_from_tool_call(name, arguments)
        return action_from_tool_call(name, arguments)

    def missions(self) -> tuple[MissionSpec, ...]:
        return self._backend.missions()

    async def start_mission(self, id: str, *, seed: int) -> Mission:
        for mission in self._backend.missions():
            if mission.id == id:
                return Mission(await self._backend.start(mission, seed=seed))
        raise MissionNotFound(id)

    def mission(self, id: str, *, seed: int) -> _MissionCtx:
        return _MissionCtx(self, id, seed)

    async def close(self) -> None:
        await self._backend.close()

    async def __aenter__(self) -> "WarGames":
        await self._backend.__aenter__()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
