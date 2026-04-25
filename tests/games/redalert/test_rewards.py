from unittest import IsolatedAsyncioTestCase

from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.redalert.rewards import delta_cash, delta_units_killed
from wargames.games.redalert.world import MissionState, Player, RedAlertWorld


def world(cash: int, kills: int) -> RedAlertWorld:
    return RedAlertWorld(
        tick=1,
        us=Player(id="p1", cash=cash, units_killed=kills),
        enemy=Player(id="p2"),
        units=(),
        buildings=(),
        resources=(),
        mission=MissionState(elapsed_ticks=1, objectives=()),
    )


class RedAlertRewardTests(IsolatedAsyncioTestCase):
    async def test_delta_rewards_use_hidden_world(self) -> None:
        prev = HiddenStateSnapshot(0, world(100, 0))
        curr = HiddenStateSnapshot(1, world(250, 2))
        self.assertEqual(await delta_cash().fn(prev, curr), 150)
        self.assertEqual(await delta_units_killed().fn(prev, curr), 2)
