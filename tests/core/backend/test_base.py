from unittest import TestCase

from wargames import WarGamesConfig
from tests.core.support import CoreTestBackend


class BackendBaseTests(TestCase):
    def test_backend_keeps_config(self) -> None:
        config = WarGamesConfig(max_ticks=10)
        self.assertIs(CoreTestBackend(config).config, config)
