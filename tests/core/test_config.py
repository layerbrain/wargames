import os
from unittest import TestCase

from wargames import WarGamesConfig


class ConfigTests(TestCase):
    def test_defaults_to_linux_xvfb(self) -> None:
        config = WarGamesConfig()
        self.assertEqual(config.display_mode, "xvfb")
        self.assertEqual(config.xvfb_resolution, (1280, 720))

    def test_from_env_parses_core_values(self) -> None:
        os.environ["LAYERBRAIN_WARGAMES_CAPTURE_FRAMES"] = "true"
        os.environ["LAYERBRAIN_WARGAMES_XVFB_RESOLUTION"] = "1280x720"
        try:
            config = WarGamesConfig.from_env()
            self.assertTrue(config.capture_frames)
            self.assertEqual(config.xvfb_resolution, (1280, 720))
        finally:
            os.environ.pop("LAYERBRAIN_WARGAMES_CAPTURE_FRAMES", None)
            os.environ.pop("LAYERBRAIN_WARGAMES_XVFB_RESOLUTION", None)
