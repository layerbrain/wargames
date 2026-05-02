from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wargames.games.supertux.missions import (
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)


class SuperTuxMissionTests(TestCase):
    def test_exports_level_files_as_difficulty_variants(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "data"
            level = root / "levels" / "world1" / "hello_world.stl"
            level.parent.mkdir(parents=True)
            level.write_text(
                '(supertux-level\n  (name (_ "Hello World"))\n  (target-time 80)\n)\n',
                encoding="utf-8",
            )

            missions = discover(root)

            self.assertEqual(
                [mission.id for mission in missions],
                [
                    "supertux.level.world1.hello-world.easy",
                    "supertux.level.world1.hello-world.normal",
                    "supertux.level.world1.hello-world.hard",
                ],
            )
            self.assertEqual(missions[0].level_file, "levels/world1/hello_world.stl")
            self.assertEqual(missions[0].target_time_seconds, 80)
            self.assertIn("platformer", missions[0].tags)

            written = extract_mission_catalog(root, Path(temp_dir) / "out")
            self.assertEqual(len(written), 3)
            self.assertEqual(len(load_mission_catalog(Path(temp_dir) / "out")), 3)

    def test_ignores_menu_misc_levels(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "data"
            level = root / "levels" / "misc" / "menu.stl"
            level.parent.mkdir(parents=True)
            level.write_text('(supertux-level (name "Menu"))\n', encoding="utf-8")

            self.assertEqual(discover(root), ())
