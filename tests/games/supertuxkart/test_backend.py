import asyncio
from pathlib import Path
from unittest import TestCase

from wargames.core.control.cua import WaitAction
from wargames.core.control.events import Target, WindowRect
from wargames.core.control.injector import RecordingInjector, XTestInjector, XdotoolInjector
from wargames.games.supertuxkart.backend import (
    SuperTuxKartBackend,
    SuperTuxKartSession,
    _has_visible_pixels,
)
from wargames.games.supertuxkart.config import SuperTuxKartConfig
from wargames.games.supertuxkart.missions import SuperTuxKartMissionSpec


class SuperTuxKartBackendTests(TestCase):
    def test_visible_frame_rejects_missing_file(self) -> None:
        self.assertFalse(_has_visible_pixels(Path("/missing"), "/usr/bin/identify"))

    def test_default_injector_is_xdotool(self) -> None:
        backend = SuperTuxKartBackend(SuperTuxKartConfig())
        target = Target(pid=1, window_id=2, rect=WindowRect(0, 0, 100, 100), display=":99")
        self.assertIsInstance(backend._injector_for(target), XdotoolInjector)

    def test_xtest_injector_is_explicit_native_path(self) -> None:
        backend = SuperTuxKartBackend(SuperTuxKartConfig(injector_transport="xtest"))
        target = Target(pid=1, window_id=2, rect=WindowRect(0, 0, 100, 100), display=":99")
        self.assertIsInstance(backend._injector_for(target), XTestInjector)


class SuperTuxKartSessionTests(TestCase):
    def test_step_uses_same_cua_and_capture_contract_as_other_games(self) -> None:
        injector = RecordingInjector()
        session = SuperTuxKartSession(
            id="s",
            mission=SuperTuxKartMissionSpec(
                id="supertuxkart.test",
                title="T",
                game="supertuxkart",
                source="builtin",
                track="lighthouse",
                laps=1,
            ),
            seed=1,
            target=Target(pid=1, window_id=2, rect=WindowRect(0, 0, 1280, 720), display=":99"),
            injector=injector,
            process=None,
            config=SuperTuxKartConfig(),
        )

        result = asyncio.run(session.step(WaitAction(id="a")))

        self.assertEqual(result.tick, 1)
        self.assertFalse(result.finished)
        self.assertIsNotNone(result.hidden)
        self.assertEqual(result.hidden.world.race.track, "lighthouse")
        self.assertEqual(len(injector.events), 1)
