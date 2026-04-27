from __future__ import annotations

import importlib

from wargames.harness.agent import Agent
from wargames.harness.agent_spec import AgentSpec


def create_python_agent(spec: AgentSpec) -> Agent:
    if spec.entrypoint is None:
        raise ValueError(f"agent {spec.id}: missing entrypoint")
    module_name, sep, attr = spec.entrypoint.partition(":")
    if not sep:
        module_name, _, attr = spec.entrypoint.rpartition(".")
    if not module_name or not attr:
        raise ValueError(f"invalid agent entrypoint: {spec.entrypoint}")
    create = getattr(importlib.import_module(module_name), attr)
    agent = create(spec)
    return agent
