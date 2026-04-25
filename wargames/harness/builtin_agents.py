from __future__ import annotations

from wargames.harness.agent import AgentDecision, AgentObservation, ToolCall
from wargames.harness.agent_spec import AgentSpec


class WaitAgent:
    id = "scripted-wait"

    def __init__(self, max_steps: int = 10) -> None:
        self.max_steps = max_steps

    async def start(self, task: object) -> None:
        return None

    async def decide(self, obs: AgentObservation) -> AgentDecision:
        if obs.step_index >= self.max_steps:
            return AgentDecision(tool_call=None, stop=True, reason="scripted_wait_complete")
        return AgentDecision(tool_call=ToolCall("wait", {}))

    async def close(self) -> None:
        return None


def create_wait_agent(spec: AgentSpec) -> WaitAgent:
    return WaitAgent(max_steps=int(spec.config.get("max_steps", 10)))
