from __future__ import annotations

from pathlib import Path

from wargames.harness.agent import Agent
from wargames.harness.agent_spec import AgentSpec


def load_agent_spec(id: str, dirs: tuple[Path, ...] = ()) -> AgentSpec:
    for directory in (*dirs, Path("agents")):
        path = directory / f"{id}.yaml"
        if path.exists():
            return AgentSpec.from_file(path)
    raise FileNotFoundError(f"agent config not found: {id}")


def create_agent(spec: AgentSpec) -> Agent:
    if spec.driver == "python":
        from wargames.harness.drivers.python import create_python_agent

        return create_python_agent(spec)
    if spec.driver == "subprocess":
        from wargames.harness.drivers.subprocess import SubprocessAgent

        return SubprocessAgent(spec)
    if spec.driver == "websocket":
        from wargames.harness.drivers.websocket import WebSocketAgent

        return WebSocketAgent(spec)
    raise ValueError(f"unsupported agent driver: {spec.driver}")


def list_agent_specs(dirs: tuple[Path, ...] = ()) -> tuple[AgentSpec, ...]:
    specs: dict[str, AgentSpec] = {}
    for directory in (Path("agents"), *dirs):
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.yaml")):
            spec = AgentSpec.from_file(path)
            specs[spec.id] = spec
    return tuple(sorted(specs.values(), key=lambda spec: spec.id))
