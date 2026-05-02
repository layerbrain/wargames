import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase

from wargames.core.control.cua import WaitAction
from wargames.core.control.events import Target, WindowRect
from wargames.core.control.injector import RecordingInjector
from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.supertux.backend import SuperTuxSession, _has_visible_pixels
from wargames.games.supertux.config import SuperTuxConfig
from wargames.games.supertux.missions import SuperTuxMissionSpec
from wargames.games.supertux.world import world_from_frame


class FakeProbe:
    def __init__(self) -> None:
        self.latest_snapshot = HiddenStateSnapshot(
            tick=1,
            world=world_from_frame(
                {
                    "tick": 1,
                    "mission": {"finished": False, "failed": False},
                    "level": {"file": "levels/world1/a.stl", "name": "A"},
                    "player": {"alive": True},
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
                    "level": {"file": "levels/world1/a.stl", "coins": 1},
                    "player": {"x": 10.0, "vx": 100.0, "alive": True},
                }
            ),
        )
        return self.latest_snapshot

    async def close(self) -> None:
        pass


class SuperTuxBackendTests(TestCase):
    def test_visible_frame_rejects_missing_file(self) -> None:
        self.assertFalse(_has_visible_pixels(Path("/missing"), "/usr/bin/identify"))

    def test_step_uses_cua_contract(self) -> None:
        injector = RecordingInjector()
        session = SuperTuxSession(
            id="s",
            mission=SuperTuxMissionSpec(
                id="supertux.level.world1.a.normal",
                title="A",
                game="supertux",
                source="builtin",
                level_file="levels/world1/a.stl",
                level_set="world1",
            ),
            seed=1,
            target=Target(pid=1, window_id=2, rect=WindowRect(0, 0, 1280, 720), display=":99"),
            injector=injector,
            probe=FakeProbe(),
            process=SimpleNamespace(process=SimpleNamespace(returncode=None)),
            config=SuperTuxConfig(),
        )

        result = asyncio.run(session.step(WaitAction(id="a")))

        self.assertEqual(result.tick, 2)
        self.assertEqual(result.hidden.world.level.coins, 1)
        self.assertEqual(result.hidden.world.player.vx, 100.0)
        self.assertEqual(len(injector.events), 1)
