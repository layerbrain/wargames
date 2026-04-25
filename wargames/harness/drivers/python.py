from __future__ import annotations

import importlib

from wargames.harness.agent import Agent
from wargames.harness.agent_spec import AgentSpec


def create_python_agent(spec: AgentSpec) -> Agent:
    if spec.factory is None:
        raise ValueError(f"agent {spec.id}: missing factory")
    module_name, sep, attr = spec.factory.partition(":")
    if not sep:
        module_name, _, attr = spec.factory.rpartition(".")
    if not module_name or not attr:
        raise ValueError(f"invalid agent factory: {spec.factory}")
    factory = getattr(importlib.import_module(module_name), attr)
    agent = factory(spec)
    return agent
