import asyncio
from types import SimpleNamespace
from unittest import TestCase

from wargames.core.control.cua import KeyDownAction, WaitAction
from wargames.core.control.events import Target, WindowRect
from wargames.core.control.injector import RecordingInjector
from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.mindustry.backend import MindustrySession
from wargames.games.mindustry.config import MindustryConfig
from wargames.games.mindustry.missions import MindustryMissionSpec
from wargames.games.mindustry.world import world_from_frame


class FakeProbe:
    def __init__(self) -> None:
        self.latest_snapshot = HiddenStateSnapshot(
            tick=1,
            world=world_from_frame(
                {
                    "tick": 1,
                    "mission": {"finished": False, "failed": False},
                    "game": {"map": "Veins", "wave": 1},
                    "teams": [{"id": 1, "name": "sharded", "cores": 1}],
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
                    "game": {"map": "Veins", "wave": 2},
                    "teams": [{"id": 1, "name": "sharded", "cores": 1, "items": 25}],
                }
            ),
        )
        return self.latest_snapshot

    async def close(self) -> None:
        pass


class MindustryBackendTests(TestCase):
    def test_wait_step_advances_from_probe(self) -> None:
        session = _session()

        result = asyncio.run(session.step(WaitAction(id="a", ms=0)))

        self.assertEqual(result.tick, 2)
        self.assertEqual(result.hidden.world.game.wave, 2)

    def test_space_key_is_real_pixel_window_input(self) -> None:
        session = _session()

        result = asyncio.run(session.step(KeyDownAction(id="a", key="Space")))

        self.assertEqual(result.tick, 2)
        event = session.injector.events[0][1]
        self.assertEqual(event.kind, "down")
        self.assertEqual(event.key, "Space")


def _session() -> MindustrySession:
    return MindustrySession(
        id="s",
        mission=MindustryMissionSpec(
            id="mindustry.survival.veins.normal",
            title="Veins",
            game="mindustry",
            source="builtin",
            map_name="Veins",
        ),
        seed=1,
        target=Target(pid=1, window_id=None, rect=WindowRect(0, 0, 1, 1), display=None),
        injector=RecordingInjector(),
        probe=FakeProbe(),
        process=SimpleNamespace(process=SimpleNamespace(returncode=None)),
        config=MindustryConfig(action_settle_seconds=0),
    )
