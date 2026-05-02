import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase

from wargames.core.control.cua import WaitAction
from wargames.core.control.events import Target, WindowRect
from wargames.core.control.injector import RecordingInjector, XTestInjector, XdotoolInjector
from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.doom.backend import DoomBackend, DoomSession, _has_visible_pixels
from wargames.games.doom.config import DoomConfig
from wargames.games.doom.missions import DoomMissionSpec
from wargames.games.doom.world import world_from_frame


class FakeProbe:
    def __init__(self) -> None:
        self.latest_snapshot = HiddenStateSnapshot(
            tick=1,
            world=world_from_frame(
                {
                    "tick": 1,
                    "mission": {"finished": False, "failed": False},
                    "level": {"map": "MAP01", "elapsed_ticks": 1},
                    "player": {"health": 100},
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
                    "level": {
                        "map": "MAP01",
                        "map_number": 1,
                        "skill": 3,
                        "elapsed_ticks": tick + 1,
                        "kills": 1,
                    },
                    "player": {"health": 96, "damage_taken": 4},
                }
            ),
        )
        return self.latest_snapshot

    async def close(self) -> None:
        pass


class DoomBackendTests(TestCase):
    def test_visible_frame_rejects_missing_file(self) -> None:
        self.assertFalse(_has_visible_pixels(Path("/missing"), "/usr/bin/identify"))

    def test_no_fallback_missions_without_catalog_or_runtime_data(self) -> None:
        backend = DoomBackend(DoomConfig(missions_dir="/missing", root="/missing"))
        self.assertEqual(backend.missions(), ())

    def test_default_injector_is_xdotool(self) -> None:
        backend = DoomBackend(DoomConfig())
        target = Target(pid=1, window_id=2, rect=WindowRect(0, 0, 100, 100), display=":99")
        self.assertIsInstance(backend._injector_for(target), XdotoolInjector)

    def test_xtest_injector_is_explicit_native_path(self) -> None:
        backend = DoomBackend(DoomConfig(injector_transport="xtest"))
        target = Target(pid=1, window_id=2, rect=WindowRect(0, 0, 100, 100), display=":99")
        self.assertIsInstance(backend._injector_for(target), XTestInjector)


class DoomSessionTests(TestCase):
    def test_step_uses_same_cua_and_capture_contract_as_other_games(self) -> None:
        injector = RecordingInjector()
        session = DoomSession(
            id="s",
            mission=DoomMissionSpec(
                id="doom.map.map01.normal",
                title="MAP01",
                game="doom",
                source="builtin",
                iwad="/tmp/freedoom2.wad",
                map="MAP01",
                skill=3,
                map_number=1,
            ),
            seed=1,
            target=Target(pid=1, window_id=2, rect=WindowRect(0, 0, 1280, 720), display=":99"),
            injector=injector,
            probe=FakeProbe(),
            process=SimpleNamespace(process=SimpleNamespace(returncode=None)),
            config=DoomConfig(),
        )

        result = asyncio.run(session.step(WaitAction(id="a")))

        self.assertEqual(result.tick, 2)
        self.assertFalse(result.finished)
        self.assertIsNotNone(result.hidden)
        self.assertEqual(result.hidden.world.level.map, "MAP01")
        self.assertEqual(result.hidden.world.level.kills, 1)
        self.assertEqual(result.hidden.world.player.health, 96)
        self.assertEqual(len(injector.events), 1)
