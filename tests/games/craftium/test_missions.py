from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wargames.games.craftium.missions import (
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)


class CraftiumMissionTests(TestCase):
    def test_exports_builtin_environment_difficulties(self) -> None:
        missions = discover()

        self.assertEqual(len(missions), 21)
        self.assertEqual(missions[0].id, "craftium.room.easy")
        self.assertEqual(missions[0].env_id, "Craftium/Room-v0")
        self.assertIn("forward", missions[0].action_names)

    def test_catalog_round_trip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            written = extract_mission_catalog(None, Path(temp_dir) / "out")

            self.assertEqual(len(written), 21)
            self.assertEqual(len(load_mission_catalog(Path(temp_dir) / "out")), 21)
