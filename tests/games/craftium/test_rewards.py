import asyncio
from unittest import TestCase

from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.craftium.rewards import movement_delta
from wargames.games.craftium.world import world_from_info


class CraftiumRewardTests(TestCase):
    def test_movement_delta_scores_position_change(self) -> None:
        prev = HiddenStateSnapshot(
            tick=1,
            world=world_from_info(
                {"player_pos": [0, 0, 0]},
                tick=1,
                reward=0,
                total_reward=0,
                finished=False,
                failed=False,
                truncated=False,
            ),
        )
        curr = HiddenStateSnapshot(
            tick=2,
            world=world_from_info(
                {"player_pos": [3, 4, 0]},
                tick=2,
                reward=0,
                total_reward=0,
                finished=False,
                failed=False,
                truncated=False,
            ),
        )

        entry = movement_delta()

        self.assertEqual(asyncio.run(entry.fn(prev, curr)), 5.0)
