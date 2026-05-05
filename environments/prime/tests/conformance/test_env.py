from __future__ import annotations

import sys
import tomllib
import unittest
from pathlib import Path

import verifiers as vf
from verifiers.types import AssistantMessage, State, ToolCall

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tests.games.redalert.doubles import FakeRedAlertBackend
from wargames.core.runtime.arena import GameDescriptor
from wargames.games.redalert.config import RedAlertConfig
from wargames.games.registry import SUPPORTED_GAMES
from wargames_prime import load_environment


CONFIG_ROOT = Path(__file__).resolve().parents[2] / "configs"
SCENARIO_ROOT = Path(__file__).resolve().parents[4] / "scenarios"

SAMPLE_MISSIONS = {
    "redalert": "redalert.soviet-01.normal",
    "flightgear": "flightgear.c172p.tutorial.takeoff",
    "supertuxkart": "supertuxkart.race.lighthouse.normal",
    "zeroad": "zeroad.scenario.arcadia.normal",
    "freeciv": "freeciv.scenario.earth-small",
    "doom": "doom.map.map01.easy",
    "supertux": "supertux.level.world1.welcome-antarctica.normal",
    "mindustry": "mindustry.survival.veins.normal",
    "craftium": "craftium.chop-tree.normal",
    "ikemen": "ikemen.vs.kfm.normal",
    "opensurge": "opensurge.level.sunshine-1.normal",
    "quaver": "quaver.chart.hyun-feat-lyuu-crossover-beginner.1159.easy",
    "naev": "naev.mission.missions-tutorial-tutorial.easy",
}


class PrimeConformanceTests(unittest.IsolatedAsyncioTestCase):
    def test_load_environment_returns_multiturn_env(self) -> None:
        env = load_environment(mission="redalert.soviet-01.normal", reward_profile="standard")

        self.assertIsInstance(env, vf.MultiTurnEnv)
        self.assertTrue(env.get_dataset())

    def test_load_environment_selects_every_supported_game(self) -> None:
        self.assertEqual(set(SUPPORTED_GAMES), set(SAMPLE_MISSIONS))

        for index, game in enumerate(SUPPORTED_GAMES, start=1):
            with self.subTest(game=game):
                env = load_environment(
                    game=game,
                    mission=SAMPLE_MISSIONS[game],
                    reward_profile="standard",
                    max_steps=index,
                )
                row = env.get_dataset()[0]

                self.assertIsInstance(env, vf.MultiTurnEnv)
                self.assertEqual(game, row["info"]["task_spec"]["game"])
                self.assertEqual(index, row["info"]["task_spec"]["max_steps"])

    def test_prime_configs_cover_every_supported_game(self) -> None:
        for game in SUPPORTED_GAMES:
            with self.subTest(game=game):
                configs = sorted((CONFIG_ROOT / game).glob("*.toml"))
                self.assertTrue(any(path.name.startswith("eval-") for path in configs))
                self.assertTrue(any(path.name.startswith("rl-") for path in configs))
                for path in configs:
                    data = tomllib.loads(path.read_text(encoding="utf-8"))
                    self.assertEqual(game, data["game"])
                    mission = data["mission"]
                    self.assertTrue(
                        any(
                            mission_file.stem == mission
                            for mission_file in (SCENARIO_ROOT / game / "missions").glob(
                                "**/*.json"
                            )
                        )
                    )
                    self.assertIn("reward_profile", data)

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
