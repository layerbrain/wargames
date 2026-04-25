from __future__ import annotations

import unittest
from pathlib import Path

from wargames.harness.agent_loader import create_agent, load_agent_spec


class AgentSpecTests(unittest.TestCase):
    def test_loads_named_python_agent(self) -> None:
        spec = load_agent_spec("scripted-wait", (Path("agents"),))

        self.assertEqual("scripted-wait", spec.id)
        self.assertEqual("python", spec.driver)

    def test_creates_builtin_wait_agent(self) -> None:
        spec = load_agent_spec("scripted-wait", (Path("agents"),))

        agent = create_agent(spec)

        self.assertEqual("scripted-wait", agent.id)
