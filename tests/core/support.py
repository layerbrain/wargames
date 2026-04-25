from __future__ import annotations

from dataclasses import dataclass

from wargames.core.backend.base import Backend, BackendSession
from wargames.core.config import WarGamesConfig
from wargames.core.control.cua import ArenaAction
from wargames.core.missions.spec import MissionSpec
from wargames.core.runtime.arena import GameDescriptor
from wargames.core.runtime.observation import Observation
from wargames.core.runtime.result import MissionSummary, StepResult
from wargames.core.world.probe import HiddenStateSnapshot


@dataclass(frozen=True)
class CoreTestObjective:
    id: str
    description: str
    finished: bool = False
    failed: bool = False


@dataclass(frozen=True)
class CoreTestMissionState:
    elapsed_ticks: int
    objectives: tuple[CoreTestObjective, ...]
    finished: bool = False
    failed: bool = False


@dataclass(frozen=True)
class CoreTestWorld:
    tick: int
    progress: int
    mission: CoreTestMissionState


class CoreTestSession(BackendSession):
    def __init__(self, mission: MissionSpec, seed: int) -> None:
        self.id = f"{mission.id}:{seed}"
        self.mission = mission
        self.seed = seed
        self.tick = 0
        self.progress = 0
        self.closed = False

    async def step(self, action: ArenaAction) -> StepResult:
        self.tick += 1
        self.progress += 1
        hidden = HiddenStateSnapshot(
            tick=self.tick,
            world=CoreTestWorld(
                tick=self.tick,
                progress=self.progress,
                mission=CoreTestMissionState(self.tick, (), finished=self.progress >= 5),
            ),
        )
        return StepResult(
            action=action,
            tick=self.tick,
            frame=None,
            finished=False,
            truncated=False,
            hidden=hidden,
            prev_hidden=None,
            info={},
        )

    async def observe(self) -> Observation:
        return Observation()

    async def summary(self) -> MissionSummary:
        return MissionSummary(
            id=self.id,
            mission=self.mission,
            seed=self.seed,
            finished=False,
            truncated=False,
            duration_ticks=self.tick,
            end_reason=None,
        )

    async def close(self) -> None:
        self.closed = True


class CoreTestBackend(Backend):
    game = "core-test"

    def __init__(self, config: WarGamesConfig) -> None:
        super().__init__(config)
        self.bootstrapped = False
        self.closed = False

    async def bootstrap(self) -> None:
        self.bootstrapped = True

    def missions(self) -> tuple[MissionSpec, ...]:
        return (MissionSpec(id="core-test.scout", title="Scout", game="core-test", source="mock"),)

    def supports(self, mission: MissionSpec) -> bool:
        return mission.game == self.game

    async def start(self, mission: MissionSpec, *, seed: int) -> BackendSession:
        return CoreTestSession(mission, seed)

    async def close(self) -> None:
        self.closed = True


CORE_TEST_GAME = GameDescriptor(id="core-test", backend_cls=CoreTestBackend, config_cls=WarGamesConfig)
