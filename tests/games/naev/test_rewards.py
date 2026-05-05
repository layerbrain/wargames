from __future__ import annotations

import asyncio
from unittest import TestCase

from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.naev.rewards import damage_penalty, delta_credits, delta_mission_completed
from wargames.games.naev.world import world_from_frame


class NaevRewardTests(TestCase):
    def test_rewards_score_resource_and_completion_changes(self) -> None:
        prev = _snapshot(credits=30_000, completed=0, armour=100, shield=100)
        curr = _snapshot(credits=31_500, completed=1, armour=90, shield=80)

        self.assertEqual(1500.0, asyncio.run(delta_credits().fn(prev, curr)))
        self.assertEqual(1.0, asyncio.run(delta_mission_completed().fn(prev, curr)))
        self.assertEqual(-30.0, asyncio.run(damage_penalty().fn(prev, curr)))


def _snapshot(*, credits: float, completed: int, armour: float, shield: float) -> HiddenStateSnapshot:
    world = world_from_frame(
        {
            "tick": completed,
            "mission": {"completed_count": completed},
            "player": {"credits": credits, "wealth": credits, "armour": armour, "shield": shield},
        }
    )
    return HiddenStateSnapshot(tick=world.tick, world=world)
