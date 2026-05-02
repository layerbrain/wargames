from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wargames.games.mindustry.missions import (
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)


class MindustryMissionTests(TestCase):
    def test_exports_builtin_survival_map_difficulties(self) -> None:
        missions = discover()

        self.assertEqual(len(missions), 27)
        self.assertEqual(missions[0].id, "mindustry.survival.veins.easy")
        self.assertEqual(missions[0].map_name, "Veins")
        self.assertEqual(missions[0].win_wave, 10)

    def test_catalog_round_trip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            written = extract_mission_catalog(None, Path(temp_dir) / "out")

            self.assertEqual(len(written), 27)
            self.assertEqual(len(load_mission_catalog(Path(temp_dir) / "out")), 27)
