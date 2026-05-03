from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase

from wargames.games.opensurge.missions import discover, extract_mission_catalog, load_mission_catalog


class OpenSurgeMissionTests(TestCase):
    def test_exports_level_files_as_difficulty_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            levels = root / "levels"
            levels.mkdir()
            (levels / "sunshine-1.lev").write_text(
                '\n'.join(
                    [
                        'name "Sunshine Paradise"',
                        "act 1",
                        "brick tile 0 0",
                        "object goal 22000 0",
                    ]
                ),
                encoding="utf-8",
            )

            missions = discover(root)

        self.assertEqual(3, len(missions))
        self.assertEqual(
            {
                "opensurge.level.sunshine-1.easy",
                "opensurge.level.sunshine-1.normal",
                "opensurge.level.sunshine-1.hard",
            },
            {mission.id for mission in missions},
        )
        self.assertTrue(
            all(mission.level_file == "levels/sunshine-1.lev" for mission in missions)
        )

    def test_catalog_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            levels = root / "levels"
            out = root / "catalog"
            levels.mkdir()
            (levels / "demo-1.lev").write_text(
                'name "Demo Level"\nact 2\nobject goal 12000 0\n',
                encoding="utf-8",
            )

            written = extract_mission_catalog(root, out)
            loaded = load_mission_catalog(out)

        self.assertEqual(3, len(written))
        self.assertEqual(3, len(loaded))
        self.assertIn("Demo Level Act 2 (Hard)", {mission.title for mission in loaded})
