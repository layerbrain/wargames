from __future__ import annotations

from unittest import IsolatedAsyncioTestCase

from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.opensurge.rewards import death_penalty, progress_x
from wargames.games.opensurge.world import world_from_frame


class OpenSurgeRewardTests(IsolatedAsyncioTestCase):
    async def test_progress_x_scores_forward_motion(self) -> None:
        score = await progress_x().fn(_snapshot(x=10), _snapshot(x=25))

        self.assertEqual(15.0, score)

    async def test_death_penalty_scores_death_transition(self) -> None:
        score = await death_penalty().fn(_snapshot(dying=False), _snapshot(dying=True))

        self.assertEqual(-1.0, score)


def _snapshot(*, x: float = 0.0, dying: bool = False) -> HiddenStateSnapshot:
    world = world_from_frame(
        {
            "tick": 1,
            "mission": {},
            "level": {"file": "levels/sunshine-1.lev", "elapsed_ticks": 1},
            "player": {"x": x, "dying": dying},
        }
    )
    return HiddenStateSnapshot(tick=world.tick, world=world)
