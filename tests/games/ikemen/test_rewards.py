import asyncio
from unittest import TestCase

from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.ikemen.rewards import damage_dealt
from wargames.games.ikemen.world import world_from_frame


class IkemenRewardTests(TestCase):
    def test_damage_dealt_scores_opponent_life_drop(self) -> None:
        prev = HiddenStateSnapshot(
            tick=1,
            world=world_from_frame({"players": [{"slot": 2, "exists": True, "life": 1000}]}),
        )
        curr = HiddenStateSnapshot(
            tick=2,
            world=world_from_frame({"players": [{"slot": 2, "exists": True, "life": 850}]}),
        )

        entry = damage_dealt()

        self.assertEqual(asyncio.run(entry.fn(prev, curr)), 150.0)
