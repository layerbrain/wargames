from unittest import TestCase

from wargames.games.redalert.catalog import SUITES


class RedAlertCatalogTests(TestCase):
    def test_suites_use_supported_difficulties(self) -> None:
        difficulties = {difficulty for suite in SUITES for difficulty in suite.difficulty_filter}
        self.assertEqual(difficulties, {"easy", "normal", "hard"})
