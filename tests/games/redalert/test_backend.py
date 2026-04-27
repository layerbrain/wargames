import asyncio
from unittest import IsolatedAsyncioTestCase, TestCase

from wargames.core.control.events import MouseEvent, Target, WindowRect
from wargames.core.control.injector import RecordingInjector, XTestInjector, XdotoolInjector
from wargames.core.control.cua import WaitAction
from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.redalert.backend import RedAlertBackend, RedAlertSession
from wargames.games.redalert.config import RedAlertConfig
from wargames.games.redalert.missions import RedAlertMissionSpec
from wargames.games.redalert.world import MissionState, Player, RedAlertWorld


class RedAlertBackendTests(TestCase):
    def test_fallback_missions_exist_without_openra(self) -> None:
        backend = RedAlertBackend(RedAlertConfig())
        self.assertIn("redalert.soviet-01.normal", [mission.id for mission in backend.missions()])

    def test_default_injector_is_working_xdotool_path(self) -> None:
        backend = RedAlertBackend(RedAlertConfig())
        target = Target(pid=1, window_id=2, rect=WindowRect(0, 0, 100, 100), display=":99")
        self.assertIsInstance(backend._injector_for(target), XdotoolInjector)

    def test_xtest_injector_is_explicit_native_path(self) -> None:
        backend = RedAlertBackend(RedAlertConfig(injector_transport="xtest"))
        target = Target(pid=1, window_id=2, rect=WindowRect(0, 0, 100, 100), display=":99")
        self.assertIsInstance(backend._injector_for(target), XTestInjector)


class RedAlertSessionTests(TestCase):
    def test_center_pointer_moves_to_target_center(self) -> None:
        injector = RecordingInjector()
        session = RedAlertSession(
            id="s",
            mission=RedAlertMissionSpec(
                id="redalert.soviet-01.normal", title="S", game="redalert", source="builtin"
            ),
            seed=1,
            target=Target(pid=1, window_id=2, rect=WindowRect(10, 20, 1280, 720), display=":99"),
            injector=injector,
            probe=None,  # type: ignore[arg-type]
            process=None,
            config=RedAlertConfig(),
        )

        import asyncio

        asyncio.run(session.center_pointer())

        self.assertEqual(injector.events[-1][1], MouseEvent(kind="move", x=650, y=380))


class PausedProbe:
    def __init__(self) -> None:
        world = RedAlertWorld(
            tick=5,
            us=Player(id="p1", faction="soviet"),
            enemy=Player(id="p2", faction="allies"),
            units=(),
            buildings=(),
            resources=(),
            mission=MissionState(elapsed_ticks=5, objectives=(), finished=False),
        )
        self.snapshot = HiddenStateSnapshot(tick=5, world=world)

    async def latest(self) -> HiddenStateSnapshot:
        return self.snapshot

    async def next_after(self, tick: int) -> HiddenStateSnapshot:
        await asyncio.sleep(10)
        return self.snapshot

    async def close(self) -> None:
        pass


class RedAlertPausedStepTests(IsolatedAsyncioTestCase):
    async def test_step_returns_latest_snapshot_when_menu_pauses_probe_ticks(self) -> None:
        session = RedAlertSession(
            id="s",
            mission=RedAlertMissionSpec(
                id="redalert.soviet-01.normal", title="S", game="redalert", source="builtin"
            ),
            seed=1,
            target=Target(pid=1, window_id=None, rect=WindowRect(0, 0, 1280, 720), display=":99"),
            injector=RecordingInjector(),
            probe=PausedProbe(),  # type: ignore[arg-type]
            process=None,
            config=RedAlertConfig(),
        )

        result = await session.step(WaitAction(id="a"))

        self.assertEqual(result.tick, 5)
        self.assertIs(result.hidden, session._last_hidden)
