from unittest import TestCase

from wargames.core.errors import GameNotInstalled, WarGamesError


class ErrorTests(TestCase):
    def test_errors_share_base_class(self) -> None:
        self.assertTrue(issubclass(GameNotInstalled, WarGamesError))
