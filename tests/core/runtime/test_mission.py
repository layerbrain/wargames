from unittest import IsolatedAsyncioTestCase

from wargames import WarGames, WarGamesConfig
from tests.core.support import CORE_TEST_GAME


class MissionTests(IsolatedAsyncioTestCase):
    async def test_observation_is_agent_visible_only(self) -> None:
        async with WarGames.for_game(CORE_TEST_GAME, WarGamesConfig()) as wg:
            async with wg.mission("core-test.scout", seed=1) as mission:
                observation = await mission.observe()
                self.assertIsNone(observation.frame)
                self.assertFalse(hasattr(observation, "prompt"))
                self.assertFalse(hasattr(observation, "metadata"))
                self.assertFalse(hasattr(observation, "tools"))
