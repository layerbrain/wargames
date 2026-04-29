import gzip
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wargames.games.freeciv.missions import discover, extract_mission_catalog, load_mission_catalog


class FreeCivMissionTests(TestCase):
    def test_loads_shipped_mission_catalog(self) -> None:
        missions = load_mission_catalog("scenarios/freeciv/missions")

        self.assertEqual(len(missions), 12)
        self.assertEqual(
            Counter({"easy": 3, "normal": 8, "hard": 1}),
            Counter(mission.difficulty for mission in missions),
        )

        by_id = {mission.id: mission for mission in missions}
        mission = by_id["freeciv.scenario.earth-small"]

        self.assertEqual(mission.title, "Earth (classic/small)")
        self.assertEqual(mission.ruleset, "classic")
        self.assertEqual(mission.players, 50)
        self.assertEqual(mission.scenario_file, "earth-small.sav.gz")
        self.assertIn("scenario", mission.tags)

    def test_scenario_startup_script_keeps_game_asset_as_source(self) -> None:
        mission = {
            item.id: item for item in load_mission_catalog("scenarios/freeciv/missions")
        }["freeciv.scenario.earth-small"]

        script = mission.startup_script()

        self.assertIn("set saveturns 0", script)
        self.assertNotIn("set generator", script)
        self.assertNotIn("set size", script)
        self.assertNotIn("set aifill", script)

    def test_extract_writes_only_installed_game_scenarios(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "freeciv"
            scenarios = root / "scenarios"
            scenarios.mkdir(parents=True)
            scenario = scenarios / "earth-test.sav.gz"
            scenario.write_bytes(gzip.compress(_scenario_save().encode("utf-8")))

            discovered = discover(root)
            self.assertEqual([mission.id for mission in discovered], ["freeciv.scenario.earth-test"])

            written = extract_mission_catalog(root, Path(temp_dir) / "out")

            self.assertEqual(len(written), 1)
            loaded = load_mission_catalog(Path(temp_dir) / "out")
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].scenario_file, "earth-test.sav.gz")

    def test_extract_does_not_clear_catalog_when_no_scenarios_are_found(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "out"
            stale = output / "normal" / "freeciv.scenario.earth-small.json"
            stale.parent.mkdir(parents=True)
            stale.write_text('{"id": "keep"}\n', encoding="utf-8")

            written = extract_mission_catalog(Path(temp_dir) / "missing", output)

            self.assertEqual(written, ())
            self.assertTrue(stale.exists())


def _scenario_save() -> str:
    return """
[scenario]
name=_(\"Earth Test\")
description=_(\"A test scenario from Freeciv data.\")
startpos_count=4

[savefile]
reason=\"Scenario\"
rulesetdir=\"classic\"

[game]
level=\"Normal\"
"""
