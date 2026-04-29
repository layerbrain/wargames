from __future__ import annotations

import sys
import unittest
from pathlib import Path

import verifiers as vf
from verifiers.types import AssistantMessage, State, ToolCall

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tests.games.redalert.doubles import FakeRedAlertBackend
from wargames.core.runtime.arena import GameDescriptor
from wargames.games.redalert.config import RedAlertConfig
from wargames_prime import load_environment


class PrimeConformanceTests(unittest.IsolatedAsyncioTestCase):
    def test_load_environment_returns_multiturn_env(self) -> None:
        env = load_environment(mission="redalert.soviet-01.normal", reward_profile="standard")

        self.assertIsInstance(env, vf.MultiTurnEnv)
        self.assertTrue(env.get_dataset())

    def test_load_environment_selects_flightgear_tasks(self) -> None:
        env = load_environment(
            game="flightgear",
            mission="flightgear.c172p.tutorial.takeoff",
            reward_profile="standard",
            max_steps=7,
        )

        self.assertIsInstance(env, vf.MultiTurnEnv)
        self.assertTrue(
            all(row["info"]["task_spec"]["game"] == "flightgear" for row in env.get_dataset())
        )
        self.assertTrue(
            all(row["info"]["task_spec"]["max_steps"] == 7 for row in env.get_dataset())
        )

    def test_load_environment_selects_supertuxkart_tasks(self) -> None:
        env = load_environment(
            game="supertuxkart",
            mission="supertuxkart.race.lighthouse.normal",
            reward_profile="standard",
            max_steps=9,
        )

        self.assertIsInstance(env, vf.MultiTurnEnv)
        self.assertTrue(
            all(row["info"]["task_spec"]["game"] == "supertuxkart" for row in env.get_dataset())
        )
        self.assertTrue(
            all(row["info"]["task_spec"]["max_steps"] == 9 for row in env.get_dataset())
        )

    def test_load_environment_selects_freeciv_tasks(self) -> None:
        env = load_environment(
            game="freeciv",
            mission="freeciv.duel.tiny.easy",
            reward_profile="standard",
            max_steps=11,
        )

        self.assertIsInstance(env, vf.MultiTurnEnv)
        self.assertTrue(
            all(row["info"]["task_spec"]["game"] == "freeciv" for row in env.get_dataset())
        )
        self.assertTrue(
            all(row["info"]["task_spec"]["max_steps"] == 11 for row in env.get_dataset())
        )

    async def test_setup_response_cleanup_drive_episode_controller(self) -> None:
        game = GameDescriptor(
            id="redalert", backend_cls=FakeRedAlertBackend, config_cls=RedAlertConfig
        )
        env = load_environment(
            mission="redalert.soviet-01.normal",
            reward_profile="standard",
            game_descriptor=game,
            config_factory=lambda: RedAlertConfig(capture_frames=True),
        )
        row = env.get_dataset()[0]
        state = State(info=row["info"], prompt=row["prompt"], trajectory=[])

        await env.setup_state(state)
        response = await env.env_response(
            [
                AssistantMessage(
                    content=None,
                    tool_calls=[ToolCall(id="call-1", name="wait", arguments="{}")],
                )
            ],
            state,
        )
        response = await env.env_response(
            [
                AssistantMessage(
                    content=None,
                    tool_calls=[ToolCall(id="call-2", name="wait", arguments="{}")],
                )
            ],
            state,
        )
        await env.close_wargames(state)

        self.assertIn("ctrl", state)
        self.assertTrue(response)
        self.assertEqual(3, len(state["wargames_trace"]))
        self.assertIn("delta_units_killed", state["ctrl"].total_breakdown)
