from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wargames.games.freeciv.missions import extract_mission_catalog, load_mission_catalog


class FreeCivMissionTests(TestCase):
    def test_loads_shipped_mission_catalog(self) -> None:
        missions = load_mission_catalog("scenarios/freeciv/missions")

        self.assertEqual(len(missions), 6)
        self.assertEqual(
            Counter({"easy": 2, "normal": 2, "hard": 2}),
            Counter(mission.difficulty for mission in missions),
        )

        by_id = {mission.id: mission for mission in missions}
        mission = by_id["freeciv.duel.tiny.easy"]

        self.assertEqual(mission.ruleset, "civ2civ3")
        self.assertEqual(mission.players, 2)
        self.assertEqual(mission.map_size, 4)
        self.assertEqual(mission.time_limit_ticks, 120)
        self.assertIn("strategy", mission.tags)

    def test_startup_script_sets_small_low_memory_game(self) -> None:
        mission = {
            item.id: item for item in load_mission_catalog("scenarios/freeciv/missions")
        }["freeciv.builder.tiny.easy"]

        script = mission.startup_script()

        self.assertIn("set aifill 2", script)
        self.assertIn("set size 4", script)
        self.assertIn("set xsize 44", script)
        self.assertIn("set ysize 34", script)
        self.assertIn("set saveturns 0", script)
        self.assertIn("set startunits cwsxx", script)
        self.assertIn("easy AI*1", script)

    def test_extract_writes_curated_catalog(self) -> None:
        with TemporaryDirectory() as temp_dir:
            written = extract_mission_catalog(Path(temp_dir) / "out")

            self.assertEqual(len(written), 6)
            loaded = load_mission_catalog(Path(temp_dir) / "out")
            self.assertEqual(len(loaded), 6)
