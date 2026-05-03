from __future__ import annotations

import unittest

from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.quaver.rewards import (
    delta_hits,
    delta_score,
    health_loss_penalty,
    miss_penalty,
)
from wargames.games.quaver.world import world_from_frame


class QuaverRewardTests(unittest.IsolatedAsyncioTestCase):
    async def test_scores_hits_misses_and_health_loss(self) -> None:
        prev = _snapshot(score=100, marv=1, perf=1, miss=0, health=100)
        curr = _snapshot(score=500, marv=2, perf=2, miss=1, health=94)

        self.assertEqual(400.0, await delta_score().fn(prev, curr))
        self.assertEqual(2.0, await delta_hits().fn(prev, curr))
        self.assertEqual(-1.0, await miss_penalty().fn(prev, curr))
        self.assertEqual(-6.0, await health_loss_penalty().fn(prev, curr))


def _snapshot(*, score: int, marv: int, perf: int, miss: int, health: int) -> HiddenStateSnapshot:
    world = world_from_frame(
        {
            "tick": score,
            "chart": {"key_count": 4, "total_judgements": 10},
            "gameplay": {"score": score, "health": health},
            "judgements": {"marv": marv, "perf": perf, "miss": miss},
        }
    )
    return HiddenStateSnapshot(tick=score, world=world)
