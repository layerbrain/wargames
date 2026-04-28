import asyncio
from pathlib import Path
from unittest import TestCase

from wargames.core.control.cua import WaitAction
from wargames.core.control.events import Target, WindowRect
from wargames.core.control.injector import RecordingInjector, XTestInjector, XdotoolInjector
from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.supertuxkart.backend import (
    SuperTuxKartBackend,
    SuperTuxKartSession,
    _has_visible_pixels,
)
from wargames.games.supertuxkart.config import SuperTuxKartConfig
from wargames.games.supertuxkart.missions import SuperTuxKartMissionSpec
from wargames.games.supertuxkart.world import world_from_frame


class FakeProbe:
    def __init__(self) -> None:
        self.latest_snapshot = HiddenStateSnapshot(
            tick=1,
            world=world_from_frame(
                {
                    "tick": 1,
                    "mission": {"finished": False, "failed": False},
                    "race": {
                        "track": "lighthouse",
                        "laps": 1,
                        "num_karts": 6,
                        "elapsed_ticks": 1,
                    },
                    "player_kart_id": 0,
                    "karts": [{"id": 0, "kart": "tux", "local_player": True, "speed": 12.0}],
                }
            ),
        )

    async def latest(self) -> HiddenStateSnapshot:
        return self.latest_snapshot

    async def next_after(self, tick: int) -> HiddenStateSnapshot:
        self.latest_snapshot = HiddenStateSnapshot(
            tick=tick + 1,
            world=world_from_frame(
                {
                    "tick": tick + 1,
                    "mission": {"finished": False, "failed": False},
                    "race": {
                        "track": "lighthouse",
                        "laps": 1,
                        "num_karts": 6,
                        "elapsed_ticks": tick + 1,
                    },
                    "player_kart_id": 0,
                    "karts": [
                        {
                            "id": 0,
                            "kart": "tux",
                            "local_player": True,
                            "speed": 13.0,
                            "progress": 0.2,
                        }
                    ],
                }
            ),
        )
        return self.latest_snapshot

    async def close(self) -> None:
        pass


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
            probe=FakeProbe(),
            process=None,
            config=SuperTuxKartConfig(),
        )

        result = asyncio.run(session.step(WaitAction(id="a")))

        self.assertEqual(result.tick, 2)
        self.assertFalse(result.finished)
        self.assertIsNotNone(result.hidden)
        self.assertEqual(result.hidden.world.race.track, "lighthouse")
        self.assertEqual(result.hidden.world.player.speed, 13.0)
        self.assertEqual(len(injector.events), 1)
