from unittest import TestCase

from wargames.core.missions.catalog import MissionSuite


class MissionCatalogTests(TestCase):
    def test_suite_carries_difficulty_filter(self) -> None:
        suite = MissionSuite(
            id="suite",
            title="Suite",
            game="redalert",
            split="curriculum",
            missions=("m1",),
            difficulty_filter=("easy", "normal"),
        )
        self.assertEqual(suite.difficulty_filter, ("easy", "normal"))
