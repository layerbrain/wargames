from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wargames.games.ikemen.missions import (
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)


class IkemenMissionTests(TestCase):
    def test_exports_builtin_quick_match_difficulties(self) -> None:
        missions = discover()

        self.assertEqual(len(missions), 9)
        self.assertEqual(missions[0].id, "ikemen.vs.kfm.easy")
        self.assertEqual(missions[0].p1, "kfm")
        self.assertEqual(missions[0].p2, "kfm")
        self.assertEqual(missions[-1].ai_level, 8)

    def test_catalog_round_trip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            written = extract_mission_catalog(None, Path(temp_dir) / "out")

            self.assertEqual(len(written), 9)
            self.assertEqual(len(load_mission_catalog(Path(temp_dir) / "out")), 9)
