from unittest import IsolatedAsyncioTestCase

from wargames.core.missions.rubric import Rubric, RubricEntry
from wargames.core.world.probe import HiddenStateSnapshot


class RubricTests(IsolatedAsyncioTestCase):
    async def test_scores_adjacent_hidden_snapshots(self) -> None:
        async def delta(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
            return curr.world - prev.world

        rubric = Rubric((RubricEntry(id="delta", fn=delta, weight=0.5),))
        score = await rubric.score(HiddenStateSnapshot(0, 2), HiddenStateSnapshot(1, 6))
        self.assertEqual(score.entries, {"delta": 2.0})
        self.assertEqual(score.total, 2.0)

    def test_rejects_duplicate_entry_ids(self) -> None:
        async def zero(prev: HiddenStateSnapshot, curr: HiddenStateSnapshot) -> float:
            return 0.0

        with self.assertRaises(ValueError):
            Rubric((RubricEntry(id="x", fn=zero), RubricEntry(id="x", fn=zero)))
