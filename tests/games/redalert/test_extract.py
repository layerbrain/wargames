from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wargames.games.redalert.missions import extract_mission_catalog


class RedAlertExtractTests(TestCase):
    def test_extract_writes_visible_difficulty_folders(self) -> None:
        root = Path(__file__).parent / "fixtures" / "openra_mods"
        with TemporaryDirectory() as tmp:
            written = extract_mission_catalog(root, tmp)
            self.assertTrue((Path(tmp) / "normal").is_dir())
            self.assertTrue((Path(tmp) / "extra_hard").is_dir())
            self.assertTrue(any(path.name == "redalert.soviet-01.normal.json" for path in written))
