from unittest import IsolatedAsyncioTestCase

from wargames import WarGames, WarGamesConfig
from wargames.core.control.cua import MouseDownAction
from tests.core.support import CORE_TEST_GAME


class ActionDispatchTests(IsolatedAsyncioTestCase):
    async def test_mission_dispatches_arena_action_to_backend(self) -> None:
        async with WarGames.for_game(CORE_TEST_GAME, WarGamesConfig()) as wg:
            async with wg.mission("core-test.scout", seed=1) as mission:
                result = await mission.step(MouseDownAction(id="mouse-down"))
                self.assertEqual(result.action.id, "mouse-down")
                self.assertGreater(result.hidden.world.progress, 0)
