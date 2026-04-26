from __future__ import annotations

import os
import tempfile
import unittest

from wargames.evaluation.splits import TaskCatalog
from wargames.evaluation.task import TaskSpec
from wargames.games.redalert import GAME


class TaskCatalogTests(unittest.TestCase):
    def test_loads_debug_tasks(self) -> None:
        _ = GAME
        catalog = TaskCatalog.load("scenarios")

        tasks = catalog.tasks(game="redalert", split="debug")

        self.assertEqual(["redalert.debug.smoke.seed-000000"], [task.id for task in tasks])

    def test_default_catalog_load_does_not_depend_on_cwd(self) -> None:
        _ = GAME
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                catalog = TaskCatalog.load()
            finally:
                os.chdir(cwd)

        tasks = catalog.tasks(game="redalert", split="debug")

        self.assertEqual(["redalert.debug.smoke.seed-000000"], [task.id for task in tasks])

    def test_rejects_cross_split_duplicate_seed(self) -> None:
        with self.assertRaises(ValueError):
            TaskCatalog.from_tasks(
                [
                    TaskSpec(id="a", game="redalert", mission_id="m", seed=1, split="train"),
                    TaskSpec(id="b", game="redalert", mission_id="m", seed=1, split="test"),
                ]
            )

    def test_rejects_train_only_profile_on_test_split(self) -> None:
        _ = GAME
        with self.assertRaises(ValueError):
            TaskCatalog.from_tasks(
                [
                    TaskSpec(
                        id="redalert.bad.seed-000001",
                        game="redalert",
                        mission_id="redalert.soviet-01",
                        seed=1,
                        split="test",
                        reward_profile="dense",
                    )
                ]
            )
