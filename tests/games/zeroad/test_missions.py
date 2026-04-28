import json
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wargames.games.zeroad.missions import (
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)


class ZeroADMissionTests(TestCase):
    def test_loads_shipped_mission_catalog(self) -> None:
        missions = load_mission_catalog("scenarios/zeroad/missions")
        self.assertEqual(len(missions), 390)
        self.assertEqual(
            Counter({"easy": 130, "normal": 130, "hard": 130}),
            Counter(mission.difficulty for mission in missions),
        )

        by_id = {mission.id: mission for mission in missions}
        mission = by_id["zeroad.scenario.arcadia.normal"]

        self.assertEqual(mission.map, "maps/scenarios/arcadia")
        self.assertEqual(mission.map_type, "scenario")
        self.assertEqual(mission.native_difficulty, "3")
        self.assertEqual(mission.ai_difficulty, 3)
        self.assertIn("conquest", mission.tags)

    def test_scenario_config_normalizes_seeds_ai_and_triggers(self) -> None:
        mission = {
            item.id: item for item in load_mission_catalog("scenarios/zeroad/missions")
        }["zeroad.scenario.arcadia.normal"]

        config = mission.scenario_config(seed=17)
        settings = config["settings"]

        self.assertEqual(config["map"], "maps/scenarios/arcadia")
        self.assertEqual(settings["AISeed"], 17)
        self.assertEqual(settings["Seed"], 17)
        self.assertTrue(settings["CheatsEnabled"])
        self.assertEqual(settings["PlayerData"][0]["AI"], "")
        self.assertEqual(settings["PlayerData"][1]["AI"], "petra")
        self.assertEqual(settings["PlayerData"][1]["AIDiff"], 3)
        self.assertIn("scripts/Conquest.js", settings["TriggerScripts"])

    def test_exports_playable_maps_from_zeroad_data(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "0ad"
            scenarios = root / "binaries" / "data" / "mods" / "public" / "maps" / "scenarios"
            _map(scenarios, "arcadia", "Arcadia", players=2)
            _map(scenarios, "sandbox", "Sandbox", players=1)

            missions = discover(root)

            self.assertEqual(
                [mission.id for mission in missions],
                [
                    "zeroad.scenario.arcadia.easy",
                    "zeroad.scenario.arcadia.normal",
                    "zeroad.scenario.arcadia.hard",
                ],
            )
            self.assertEqual(missions[0].map, "maps/scenarios/arcadia")

            written = extract_mission_catalog(root, Path(temp_dir) / "out")
            self.assertEqual(len(written), 3)
            exported = load_mission_catalog(Path(temp_dir) / "out")
            self.assertEqual(len(exported), 3)

    def test_extract_does_not_clear_catalog_when_no_maps_are_found(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "out"
            stale = output / "normal" / "zeroad.scenario.arcadia.normal.json"
            stale.parent.mkdir(parents=True)
            stale.write_text('{"id": "keep"}\n', encoding="utf-8")

            written = extract_mission_catalog(Path(temp_dir) / "missing", output)

            self.assertEqual(written, ())
            self.assertTrue(stale.exists())


def _map(maps: Path, id: str, title: str, *, players: int) -> None:
    maps.mkdir(parents=True, exist_ok=True)
    player_data = [
        {"Name": f"Player {index}", "Civ": "spart", "Team": -1}
        for index in range(1, players + 1)
    ]
    settings = {
        "Name": title,
        "VictoryConditions": ["conquest"],
        "PlayerData": player_data,
    }
    maps.joinpath(f"{id}.xml").write_text(
        f"""
        <Scenario version="7">
          <ScriptSettings><![CDATA[
            {json.dumps(settings)}
          ]]></ScriptSettings>
        </Scenario>
        """,
        encoding="utf-8",
    )
