import os
from unittest import TestCase

from wargames.games.redalert.config import RedAlertConfig


class RedAlertConfigTests(TestCase):
    def test_default_window_size_is_hd_widescreen(self) -> None:
        self.assertEqual(RedAlertConfig().openra_window_size, (1280, 720))

    def test_reads_game_specific_env(self) -> None:
        os.environ["LAYERBRAIN_WARGAMES_REDALERT_OPENRA_BINARY"] = "/tmp/openra"
        os.environ["LAYERBRAIN_WARGAMES_REDALERT_OPENRA_WINDOW_SIZE"] = "1280x720"
        try:
            config = RedAlertConfig.from_env()
            self.assertEqual(config.openra_binary, "/tmp/openra")
            self.assertEqual(config.openra_window_size, (1280, 720))
        finally:
            os.environ.pop("LAYERBRAIN_WARGAMES_REDALERT_OPENRA_BINARY", None)
            os.environ.pop("LAYERBRAIN_WARGAMES_REDALERT_OPENRA_WINDOW_SIZE", None)
