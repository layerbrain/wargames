from __future__ import annotations

from wargames.core.backend.base import Backend, BackendSession
from wargames.core.capture.frame import Frame
from wargames.core.config import WarGamesConfig
from wargames.core.control.cua import ArenaAction
from wargames.core.missions.spec import MissionSpec
from wargames.core.runtime.observation import Observation
from wargames.core.runtime.result import MissionSummary, StepResult
from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.redalert.config import RedAlertConfig
from wargames.games.redalert.missions import RedAlertMissionSpec, fallback_missions
from wargames.games.redalert.world import MissionState, Player, RedAlertWorld

PNG_1X1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def _world(tick: int, finished: bool = False) -> RedAlertWorld:
    return RedAlertWorld(
        tick=tick,
        us=Player(id="p1", faction="soviet", cash=1000 + tick),
        enemy=Player(id="p2", faction="allies"),
        units=(),
        buildings=(),
        resources=(),
        mission=MissionState(elapsed_ticks=tick, objectives=(), finished=finished),
    )


class FakeRedAlertSession(BackendSession):
    def __init__(self, mission: RedAlertMissionSpec, seed: int) -> None:
        self.id = f"{mission.id}:{seed}"
        self.mission = mission
        self.seed = seed
        self.tick = 0
        self.closed = False
        self.last_action: ArenaAction | None = None
        self._last_hidden: HiddenStateSnapshot | None = None

    async def step(self, action: ArenaAction) -> StepResult:
        prev = self._last_hidden
        self.tick += 1
        self.last_action = action
        hidden = HiddenStateSnapshot(tick=self.tick, world=_world(self.tick))
        self._last_hidden = hidden
        return StepResult(
            action=action,
            tick=self.tick,
            frame=self._frame(),
            finished=False,
            truncated=False,
            hidden=hidden,
            prev_hidden=prev,
            info={"action": action.id},
        )

    async def observe(self) -> Observation:
        return Observation(frame=self._frame())

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

    def _frame(self) -> Frame:
        return Frame(
            id=f"fake-{self.tick}",
            width=1280,
            height=720,
            captured_tick=self.tick,
            image_b64=PNG_1X1,
        )


class FakeRedAlertBackend(Backend):
    game = "redalert"

    def __init__(self, config: WarGamesConfig | None = None) -> None:
        if config is None:
            config = RedAlertConfig(capture_frames=True)
        super().__init__(config)
        self.config = config
        self.sessions: list[FakeRedAlertSession] = []

    def missions(self) -> tuple[MissionSpec, ...]:
        return fallback_missions()

    def supports(self, mission: MissionSpec) -> bool:
        return isinstance(mission, RedAlertMissionSpec)

    async def start(self, mission: MissionSpec, *, seed: int) -> BackendSession:
        session = FakeRedAlertSession(mission, seed)
        self.sessions.append(session)
        return session

    async def close(self) -> None:
        for session in tuple(self.sessions):
            await session.close()
        self.sessions.clear()


def make_test_backend(config: RedAlertConfig | None = None) -> FakeRedAlertBackend:
    return FakeRedAlertBackend(config)
