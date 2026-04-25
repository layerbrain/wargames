from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from wargames_openreward.env_redalert import WarGamesRedAlert


class OpenRewardConformanceTests(unittest.TestCase):
    def test_lists_splits_tasks_variants_and_cua_tools(self) -> None:
        self.assertIn({"name": "debug", "type": "debug"}, WarGamesRedAlert.list_splits())
        self.assertTrue(WarGamesRedAlert.list_tasks("debug"))
        self.assertIn({"name": "protective"}, WarGamesRedAlert.list_variants())
        self.assertEqual(
            ["click", "move_mouse", "double_click", "drag", "key", "type_text", "scroll", "wait"],
            WarGamesRedAlert.list_tools(),
        )
