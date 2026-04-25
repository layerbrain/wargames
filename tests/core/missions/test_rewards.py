from unittest import IsolatedAsyncioTestCase

from wargames.core.missions.rewards import on_objective, terminal
from wargames.core.world.probe import HiddenStateSnapshot
from tests.core.support import CoreTestMissionState, CoreTestObjective, CoreTestWorld


class RewardPrimitiveTests(IsolatedAsyncioTestCase):
    async def test_terminal_scores_finished_world(self) -> None:
        prev = HiddenStateSnapshot(0, CoreTestWorld(0, 0, CoreTestMissionState(0, ())))
        curr = HiddenStateSnapshot(1, CoreTestWorld(1, 0, CoreTestMissionState(1, (), finished=True)))
        self.assertEqual(await terminal().fn(prev, curr), 1.0)

    async def test_on_objective_scores_transition_once(self) -> None:
        prev = HiddenStateSnapshot(0, CoreTestWorld(0, 0, CoreTestMissionState(0, (CoreTestObjective("o", "O"),))))
        curr = HiddenStateSnapshot(1, CoreTestWorld(1, 0, CoreTestMissionState(1, (CoreTestObjective("o", "O", finished=True),))))
        self.assertEqual(await on_objective("o").fn(prev, curr), 1.0)
