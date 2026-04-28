import asyncio
from pathlib import Path
from unittest import TestCase

from wargames.core.control.cua import WaitAction
from wargames.core.control.events import Target, WindowRect
from wargames.core.control.injector import RecordingInjector, XTestInjector, XdotoolInjector
from wargames.games.zeroad.backend import ZeroADBackend, ZeroADSession, _has_visible_pixels
from wargames.games.zeroad.config import ZeroADConfig
from wargames.games.zeroad.missions import ZeroADMissionSpec


class FakeClient:
    async def step(self) -> dict[str, object]:
        return {
            "timeElapsed": 200,
            "players": [
                {},
                {"state": "active", "popCount": 10, "resourceCounts": {"wood": 100}},
                {"state": "active"},
            ],
            "entities": {},
        }


class ZeroADBackendTests(TestCase):
    def test_visible_frame_rejects_missing_file(self) -> None:
        self.assertFalse(_has_visible_pixels(Path("/missing"), "/usr/bin/identify"))

    def test_default_injector_is_xdotool(self) -> None:
        backend = ZeroADBackend(ZeroADConfig())
        target = Target(pid=1, window_id=2, rect=WindowRect(0, 0, 100, 100), display=":99")
        self.assertIsInstance(backend._injector_for(target), XdotoolInjector)

    def test_xtest_injector_is_explicit_native_path(self) -> None:
        backend = ZeroADBackend(ZeroADConfig(injector_transport="xtest"))
        target = Target(pid=1, window_id=2, rect=WindowRect(0, 0, 100, 100), display=":99")
        self.assertIsInstance(backend._injector_for(target), XTestInjector)


class ZeroADSessionTests(TestCase):
    def test_step_advances_rl_state_after_cua_input(self) -> None:
        injector = RecordingInjector()
        session = ZeroADSession(
            id="s",
            mission=ZeroADMissionSpec(
                id="zeroad.test",
                title="T",
                game="zeroad",
                source="builtin",
                map="maps/scenarios/arcadia",
            ),
            seed=1,
            target=Target(pid=1, window_id=2, rect=WindowRect(0, 0, 1280, 720), display=":99"),
            injector=injector,
            client=FakeClient(),
            process=None,
            config=ZeroADConfig(),
            initial_state={"timeElapsed": 0, "players": [{}, {"state": "active"}]},
        )

        result = asyncio.run(session.step(WaitAction(id="a")))

        self.assertEqual(result.tick, 1)
        self.assertFalse(result.finished)
        self.assertIsNotNone(result.hidden)
        self.assertEqual(result.hidden.world.us.population, 10)
        self.assertEqual(len(injector.events), 1)
