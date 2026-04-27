from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from wargames.core.runtime.arena import GameDescriptor, WarGames
from wargames.evaluation.task import RunConfig, TaskSpec
from wargames.games.redalert.config import RedAlertConfig
from wargames.harness.agent import AgentDecision, AgentObservation, ToolCall
from wargames.harness.builtin_agents import WaitAgent
from wargames.harness.runner import run_task
from tests.games.redalert.doubles import FakeRedAlertBackend


class BatchAgent:
    id = "batch"

    async def start(self, task: object) -> None:
        return None

    async def decide(self, obs: AgentObservation) -> AgentDecision:
        if obs.step_index:
            return AgentDecision(stop=True, reason="batch_complete")
        return AgentDecision(
            events=(
                ToolCall("move_mouse", {"x": 10, "y": 10}),
                ToolCall("mouse_down", {"button": "left"}),
                ToolCall("mouse_up", {"button": "left"}),
            )
        )

    async def close(self) -> None:
        return None


class RunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_scripted_wait_agent_runs_against_fake_backend(self) -> None:
        game = GameDescriptor(
            id="redalert", backend_cls=FakeRedAlertBackend, config_cls=RedAlertConfig
        )
        task = TaskSpec(
            id="redalert.debug.quickstart.seed-000000",
            game="redalert",
            mission_id="redalert.soviet-01.normal",
            seed=0,
            max_steps=3,
            reward_profile="standard",
        )
        async with WarGames.for_game(game, RedAlertConfig(capture_frames=True)) as wg:
            summary = await run_task(
                task=task,
                run_config=RunConfig(recorder_mode="none", video_mode="none"),
                wg=wg,
                agent=WaitAgent(max_steps=2),
            )

        self.assertEqual("scripted_wait_complete", summary.end_reason)
        self.assertEqual(2, summary.steps)
        self.assertIn("delta_units_killed", summary.breakdown)

    async def test_sampled_agent_can_return_event_array_for_one_turn(self) -> None:
        game = GameDescriptor(
            id="redalert", backend_cls=FakeRedAlertBackend, config_cls=RedAlertConfig
        )
        task = TaskSpec(
            id="redalert.debug.quickstart.seed-000000",
            game="redalert",
            mission_id="redalert.soviet-01.normal",
            seed=0,
            max_steps=10,
            reward_profile="standard",
        )
        async with WarGames.for_game(game, RedAlertConfig(capture_frames=True)) as wg:
            summary = await run_task(
                task=task,
                run_config=RunConfig(recorder_mode="none", video_mode="none"),
                wg=wg,
                agent=BatchAgent(),
            )

        self.assertEqual("batch_complete", summary.end_reason)
        self.assertEqual(3, summary.steps)

    async def test_full_recorder_writes_public_files_without_hidden_state(self) -> None:
        game = GameDescriptor(
            id="redalert", backend_cls=FakeRedAlertBackend, config_cls=RedAlertConfig
        )
        task = TaskSpec(
            id="redalert.debug.quickstart.seed-000000",
            game="redalert",
            mission_id="redalert.soviet-01.normal",
            seed=0,
            max_steps=3,
            reward_profile="standard",
        )
        with tempfile.TemporaryDirectory() as tmp:
            async with WarGames.for_game(game, RedAlertConfig(capture_frames=True)) as wg:
                summary = await run_task(
                    task=task,
                    run_config=RunConfig(recorder_mode="full", video_mode="frames", out_dir=tmp),
                    wg=wg,
                    agent=WaitAgent(max_steps=2),
                )

            run_dir = Path(tmp) / summary.run_id
            events = (run_dir / "events.jsonl").read_text(encoding="utf-8")
            rewards = (run_dir / "rewards.jsonl").read_text(encoding="utf-8")

        self.assertNotIn("hidden", events)
        self.assertNotIn("world", events)
        self.assertIn("delta_units_killed", rewards)
