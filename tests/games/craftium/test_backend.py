import asyncio
from unittest import TestCase

from wargames.core.control.cua import KeyDownAction, KeyUpAction, WaitAction
from wargames.games.craftium.backend import CraftiumSession
from wargames.games.craftium.config import CraftiumConfig
from wargames.games.craftium.missions import CraftiumMissionSpec


class FakeCraftiumEnv:
    def __init__(self) -> None:
        self.actions: list[int] = []
        self.closed = False

    def step(self, action: int) -> tuple[object, float, bool, bool, dict[str, object]]:
        self.actions.append(action)
        tick = len(self.actions)
        return (
            [[[0, 0, 0]]],
            0.25,
            False,
            False,
            {"player_pos": [float(tick), 0.0, 0.0], "player_vel": [1.0, 0.0, 0.0]},
        )

    def close(self) -> None:
        self.closed = True


class CraftiumBackendTests(TestCase):
    def test_key_hold_repeats_mapped_action_on_wait(self) -> None:
        env = FakeCraftiumEnv()
        session = _session(env)

        asyncio.run(session.step(KeyDownAction(id="down", key="w")))
        result = asyncio.run(session.step(WaitAction(id="wait", ms=250)))
        asyncio.run(session.step(KeyUpAction(id="up", key="w")))

        self.assertEqual(env.actions[:3], [1, 1, 1])
        self.assertEqual(result.tick, 3)
        self.assertEqual(result.hidden.world.player.position, (3.0, 0.0, 0.0))


def _session(env: FakeCraftiumEnv) -> CraftiumSession:
    return CraftiumSession(
        id="s",
        mission=CraftiumMissionSpec(
            id="craftium.room.normal",
            title="Room",
            game="craftium",
            source="builtin",
            env_id="Craftium/Room-v0",
            action_names=("forward", "mouse x+", "mouse x-"),
        ),
        seed=1,
        env=env,
        observation=[[[0, 0, 0]]],
        info={"player_pos": [0.0, 0.0, 0.0], "player_vel": [0.0, 0.0, 0.0]},
        config=CraftiumConfig(capture_frames=False, wait_step_ms=100, max_wait_steps=3),
    )
