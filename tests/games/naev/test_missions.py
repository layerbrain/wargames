from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase

from wargames.games.naev.missions import discover, extract_mission_catalog, load_mission_catalog


class NaevMissionTests(TestCase):
    def test_discovers_native_mission_xml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = _naev_data_dir(Path(tmp))
            mission = data / "missions" / "pirate" / "raid.lua"
            mission.parent.mkdir(parents=True)
            mission.write_text(
                """--[[
<?xml version='1.0' encoding='utf8'?>
<mission name="Pirate Convoy Raid">
 <location>Computer</location>
 <faction>Pirate</faction>
 <notes><tier>2</tier></notes>
</mission>
--]]
""",
                encoding="utf-8",
            )

            missions = discover(data)

        self.assertEqual(1, len(missions))
        self.assertEqual("Pirate Convoy Raid", missions[0].mission_name)
        self.assertEqual("hard", missions[0].difficulty)
        self.assertEqual("missions/pirate/raid.lua", missions[0].mission_file)

    def test_catalog_round_trip_omits_absolute_data_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _naev_data_dir(root / "runtime")
            mission = data / "missions" / "trader" / "cargo.lua"
            mission.parent.mkdir(parents=True)
            mission.write_text(
                """--[[
<?xml version='1.0' encoding='utf8'?>
<mission name="Cargo Run">
 <location>Computer</location>
 <notes><tier>1</tier></notes>
</mission>
--]]
""",
                encoding="utf-8",
            )

            written = extract_mission_catalog(data, root / "catalog")
            loaded = load_mission_catalog(root / "catalog")

        self.assertEqual(1, len(written))
        self.assertEqual(1, len(loaded))
        self.assertIsNone(loaded[0].data_dir)
        self.assertEqual("Cargo Run", loaded[0].mission_name)


def _naev_data_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "events").mkdir()
    (root / "missions").mkdir()
    (root / "start.xml").write_text("<Start />\n", encoding="utf-8")
    return root
