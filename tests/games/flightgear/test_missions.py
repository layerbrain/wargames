from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wargames.games.flightgear.missions import (
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)


class FlightGearMissionTests(TestCase):
    def test_loads_shipped_missions(self) -> None:
        missions = load_mission_catalog("scenarios/flightgear/missions")
        self.assertEqual(len(missions), 14)

        by_id = {mission.id: mission for mission in missions}
        mission = by_id["flightgear.c172p.tutorial.takeoff"]

        self.assertEqual(mission.aircraft, "c172p")
        self.assertEqual(mission.airport, "PHTO")
        self.assertEqual(mission.tutorial_file, "takeoff.xml")
        self.assertIn("--disable-freeze", mission.startup_args)

        engine_failure = by_id["flightgear.c172p.tutorial.engine-failure"]
        self.assertEqual(engine_failure.difficulty, "hard")
        self.assertEqual(engine_failure.native_difficulty, "tutorial")

    def test_exports_tutorials_from_flightgear_data(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "fgdata"
            tutorials = root / "Aircraft" / "c172p" / "Tutorials"
            tutorials.mkdir(parents=True)
            (tutorials / "c172-tutorials.xml").write_text(
                """
                <PropertyList>
                  <tutorial include="takeoff.xml"/>
                  <tutorial include="engine-failure.xml"/>
                </PropertyList>
                """,
                encoding="utf-8",
            )
            (tutorials / "takeoff.xml").write_text(
                _tutorial("Takeoff", "PHTO", "morning"), encoding="utf-8"
            )
            (tutorials / "engine-failure.xml").write_text(
                _tutorial("Engine Failure", "PHTO", "dusk"),
                encoding="utf-8",
            )

            missions = discover(root)
            self.assertEqual(
                [mission.id for mission in missions],
                [
                    "flightgear.c172p.tutorial.takeoff",
                    "flightgear.c172p.tutorial.engine-failure",
                ],
            )

            written = extract_mission_catalog(root, Path(temp_dir) / "out")
            self.assertEqual(len(written), 2)
            exported = load_mission_catalog(Path(temp_dir) / "out")
            self.assertEqual(len(exported), 2)


def _tutorial(name: str, airport: str, timeofday: str) -> str:
    return f"""
    <PropertyList>
      <name>{name}</name>
      <description>{name} description.</description>
      <timeofday>{timeofday}</timeofday>
      <presets>
        <airport-id>{airport}</airport-id>
      </presets>
    </PropertyList>
    """
