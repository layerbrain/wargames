from __future__ import annotations

import unittest

from tests.games.redalert.doubles import FakeRedAlertBackend
from wargames.core.runtime.arena import GameDescriptor, WarGames
from wargames.evaluation.task import RunConfig, TaskSpec
from wargames.games.redalert.config import RedAlertConfig
from wargames.harness.builtin_agents import WaitAgent
from wargames.harness.lobby import run_lobby


class LobbyRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_slot_lobby_runs_independent_summaries(self) -> None:
        game = GameDescriptor(id="redalert", backend_cls=FakeRedAlertBackend, config_cls=RedAlertConfig)
        task = TaskSpec(
            id="redalert.debug.smoke.seed-000000",
            game="redalert",
            mission_id="redalert.soviet-01.normal",
            seed=0,
            split="debug",
            max_steps=2,
            reward_profile="standard",
        )
        async with WarGames.for_game(game, RedAlertConfig(capture_frames=True)) as wg1:
            async with WarGames.for_game(game, RedAlertConfig(capture_frames=True)) as wg2:
                summary = await run_lobby(
                    lobby_id="test-lobby",
                    tasks={"slot-1": task, "slot-2": task},
                    agents={"slot-1": WaitAgent(max_steps=1), "slot-2": WaitAgent(max_steps=1)},
                    war_games={"slot-1": wg1, "slot-2": wg2},
                    run_config=RunConfig(recorder_mode="none"),
                )

        self.assertEqual({"slot-1", "slot-2"}, set(summary.slots))
