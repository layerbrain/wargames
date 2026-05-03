from __future__ import annotations

import unittest
from collections.abc import Awaitable
from typing import cast

from wargames.core.runtime.arena import GameDescriptor
from wargames.environments import EnvStepResult, StartResult, WarGamesEnv
from wargames.environments.actions import ACTION_SETS
from wargames.games.redalert.config import RedAlertConfig
from wargames.games.registry import SUPPORTED_GAMES
from tests.games.redalert.doubles import FakeRedAlertBackend


def _fake_redalert() -> GameDescriptor:
    return GameDescriptor(id="redalert", backend_cls=FakeRedAlertBackend, config_cls=RedAlertConfig)


class NativeEnvironmentSyncTests(unittest.TestCase):
    def test_sync_start_step_and_close(self) -> None:
        env = WarGamesEnv(
            game=_fake_redalert(),
            mission="redalert.soviet-01.normal",
            max_steps=3,
            config=RedAlertConfig(capture_frames=True),
        )

        obs, info = cast(StartResult, env.start())
        self.assertEqual("redalert", info["game"])
        self.assertEqual("redalert.soviet-01.normal", info["mission"])
        self.assertIn("wait", cast(tuple[str, ...], info["actions"]))
        self.assertIsNotNone(obs["frame"])

        obs, reward, terminated, truncated, info = cast(EnvStepResult, env.step("wait"))
        self.assertIsInstance(reward, float)
        self.assertFalse(terminated)
        self.assertFalse(truncated)
        self.assertEqual(1, obs["step"])
        self.assertNotIn("reward_breakdown", info)
        self.assertNotIn("summary", info)
        self.assertNotIn("hidden", repr(obs))
        self.assertNotIn("hidden", repr(info))

        env.close()

    def test_budget_stop_is_truncated_and_includes_final_summary(self) -> None:
        env = WarGamesEnv(
            game=_fake_redalert(),
            mission="redalert.soviet-01.normal",
            max_steps=1,
            config=RedAlertConfig(capture_frames=True),
        )
        cast(StartResult, env.start())

        _, _, terminated, truncated, info = cast(EnvStepResult, env.step("wait"))

        self.assertFalse(terminated)
        self.assertTrue(truncated)
        self.assertEqual("max_steps", info["end_reason"])
        self.assertIn("reward_breakdown", info)
        self.assertIn("summary", info)
        self.assertNotIn("hidden", repr(info))
        env.close()

    def test_every_supported_game_has_an_action_set(self) -> None:
        self.assertEqual(set(SUPPORTED_GAMES), set(ACTION_SETS))
        for game, action_set in ACTION_SETS.items():
            self.assertEqual(game, action_set.game)
            self.assertIn("wait", action_set.ids())
            self.assertGreater(len(action_set.actions), 1)


class NativeEnvironmentAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_start_step_and_close(self) -> None:
        env = WarGamesEnv(
            game=_fake_redalert(),
            mission="redalert.soviet-01.normal",
            max_steps=3,
            config=RedAlertConfig(capture_frames=True),
        )

        obs, info = await cast(Awaitable[StartResult], env.start())
        self.assertEqual("redalert", info["game"])
        self.assertIsNotNone(obs["frame"])

        obs, reward, terminated, truncated, info = await cast(
            Awaitable[EnvStepResult], env.step(0)
        )
        self.assertIsInstance(reward, float)
        self.assertFalse(terminated)
        self.assertFalse(truncated)
        self.assertEqual("wait", info["action"])
        self.assertEqual(1, obs["step"])

        await cast(Awaitable[None], env.close())
