from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from openreward.environments import Environment, Server, ToolOutput

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tests.games.redalert.doubles import FakeRedAlertBackend
from wargames.core.runtime.arena import GameDescriptor
from wargames.games.redalert.config import RedAlertConfig
from wargames_openreward.env_redalert import WarGamesRedAlert, WarGamesRedAlertDense


class TestableWarGamesRedAlert(WarGamesRedAlert):
    game_descriptor = GameDescriptor(
        id="redalert",
        backend_cls=FakeRedAlertBackend,
        config_cls=RedAlertConfig,
    )


class OpenRewardConformanceTests(unittest.IsolatedAsyncioTestCase):
    def test_environment_is_real_openreward_environment(self) -> None:
        self.assertTrue(issubclass(WarGamesRedAlert, Environment))
        self.assertEqual(
            {"click", "move_mouse", "double_click", "drag", "key", "type_text", "scroll", "wait"},
            {tool.name for tool in WarGamesRedAlert.list_tools().tools},
        )
        self.assertIn("debug", {split.name for split in WarGamesRedAlert.list_splits()})
        self.assertEqual("dense", WarGamesRedAlertDense.list_tasks("train")[0]["reward_profile"])

    async def test_tool_call_returns_tool_output_reward_and_finished(self) -> None:
        task_spec = TestableWarGamesRedAlert.list_tasks("debug")[0]
        env = TestableWarGamesRedAlert(task_spec=task_spec)
        await env.setup()
        try:
            prompt = env.get_prompt()
            output = await env.wait()
        finally:
            await env.teardown()

        self.assertTrue(prompt)
        self.assertIsInstance(output, ToolOutput)
        self.assertIsInstance(output.reward, float)
        self.assertFalse(output.finished)
        self.assertIsNotNone(output.metadata)
        assert output.metadata is not None
        self.assertIn("breakdown", output.metadata)

    async def test_train_only_profile_rejected_on_test_split(self) -> None:
        task_spec = WarGamesRedAlertDense.list_tasks("test")[0]
        env = TestableWarGamesRedAlert(task_spec=task_spec)
        env.reward_profile = "dense"

        with self.assertRaises(ValueError):
            await env.setup()

    def test_openreward_server_protocol_exposes_prompt_and_tool_call(self) -> None:
        app = Server([TestableWarGamesRedAlert], return_errors="exception").app
        client = TestClient(app)
        task_spec = TestableWarGamesRedAlert.list_tasks("debug")[0]
        headers = {"X-Session-ID": "test-session"}

        created = client.post(
            "/create",
            headers=headers,
            json={"env_name": "standard", "task_spec": task_spec},
        )
        prompt = client.get("/standard/prompt", headers=headers)
        called = client.post("/standard/call", headers=headers, json={"name": "wait", "input": {}})
        deleted = client.post("/delete", headers=headers)

        self.assertEqual(200, created.status_code)
        self.assertEqual(200, prompt.status_code)
        self.assertEqual(200, called.status_code)
        self.assertIn('"reward"', called.text)
        self.assertEqual(200, deleted.status_code)
