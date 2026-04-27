from __future__ import annotations

import unittest
import os
from pathlib import Path
from unittest import mock

from wargames.harness.agent_loader import create_agent, load_agent_spec
from wargames.harness.agent_spec import AgentSpec
from wargames.harness.openai_agent import OpenAICompatibleAgent


class AgentSpecTests(unittest.TestCase):
    def test_loads_named_python_agent(self) -> None:
        spec = load_agent_spec("scripted-wait", (Path("agents"),))

        self.assertEqual("scripted-wait", spec.id)
        self.assertEqual("scripted-wait", spec.kind)

    def test_creates_builtin_wait_agent(self) -> None:
        spec = load_agent_spec("scripted-wait", (Path("agents"),))

        agent = create_agent(spec)

        self.assertEqual("scripted-wait", agent.id)

    def test_config_expands_environment_variables(self) -> None:
        with mock.patch.dict(os.environ, {"WARGAMES_TEST_THINKING": "true"}):
            spec = AgentSpec.from_mapping(
                {
                    "id": "custom",
                    "kind": "python",
                    "entrypoint": "tests.harness.agents:scripted_wait_agent",
                    "config": {"extra_body": {"enable_thinking": "${WARGAMES_TEST_THINKING}"}},
                }
            )

        self.assertEqual("true", spec.config["extra_body"]["enable_thinking"])

    def test_openai_agent_passes_custom_provider_options(self) -> None:
        spec = AgentSpec.from_mapping(
            {
                "id": "custom-openai",
                "kind": "openai",
                "model": "kimi-k2.5",
                "api_key_env": "OPENAI_API_KEY",
                "config": {
                    "temperature": 0.4,
                    "top_p": 0.8,
                    "max_tokens": 123,
                    "disable_reasoning": False,
                    "reasoning_effort": "medium",
                    "extra_body": {
                        "enable_thinking": True,
                        "chat_template_kwargs": {"enable_thinking": True},
                    },
                },
            }
        )
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            agent = OpenAICompatibleAgent(spec)

        options = agent._completion_options(include_reasoning_disable=False)

        self.assertEqual(0.4, options["temperature"])
        self.assertEqual(0.8, options["top_p"])
        self.assertEqual(123, options["max_tokens"])
        self.assertEqual(True, options["extra_body"]["enable_thinking"])
        self.assertEqual("medium", options["extra_body"]["reasoning"]["effort"])
