from pathlib import Path
from unittest import TestCase

from wargames.games.redalert.missions import discover


class RedAlertMissionTests(TestCase):
    def test_discovers_builtin_and_directory_maps(self) -> None:
        root = Path(__file__).parent / "fixtures" / "openra_mods"
        ids = [mission.id for mission in discover(root)]
        self.assertIn("redalert.soviet-01.normal", ids)
        self.assertIn("redalert.allies01.normal", ids)
        self.assertIn("redalert.skirmish.oasis", ids)
