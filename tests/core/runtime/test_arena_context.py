from unittest import IsolatedAsyncioTestCase

from wargames import WarGames, WarGamesConfig
from tests.core.support import CORE_TEST_GAME


class ArenaContextTests(IsolatedAsyncioTestCase):
    async def test_lists_missions(self) -> None:
        async with WarGames.for_game(CORE_TEST_GAME, WarGamesConfig()) as wg:
            self.assertEqual([mission.id for mission in wg.missions()], ["core-test.scout"])
