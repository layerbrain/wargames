import asyncio
from unittest import TestCase

from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.doom.rewards import damage_penalty, delta_items, delta_kills, time_penalty
from wargames.games.doom.world import world_from_frame


class DoomRewardTests(TestCase):
    def test_step_primitives_score_deltas(self) -> None:
        previous = _snapshot(tick=10, kills=1, items=0, damage=2)
        current = _snapshot(tick=15, kills=3, items=1, damage=5)

        self.assertEqual(asyncio.run(delta_kills().fn(previous, current)), 2.0)
        self.assertEqual(asyncio.run(delta_items().fn(previous, current)), 1.0)
        self.assertEqual(asyncio.run(damage_penalty().fn(previous, current)), -3.0)
        self.assertEqual(asyncio.run(time_penalty().fn(previous, current)), -5.0)


def _snapshot(*, tick: int, kills: int, items: int, damage: int) -> HiddenStateSnapshot:
    return HiddenStateSnapshot(
        tick=tick,
        world=world_from_frame(
            {
                "tick": tick,
                "level": {"kills": kills, "items": items},
                "player": {"damage_taken": damage, "health": 100 - damage},
            }
        ),
    )
