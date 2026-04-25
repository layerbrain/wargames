from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from wargames.core.capture.frame import Frame
from wargames.core.control.tools import ToolSpec
from wargames.evaluation.task import TaskSpec


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, object]


@dataclass(frozen=True)
class PublicEvent:
    step: int
    tool_call: ToolCall
    reward: float | None = None
    tick: int | None = None

    def action_only(self) -> "PublicEvent":
        return PublicEvent(step=self.step, tool_call=self.tool_call, tick=self.tick)


@dataclass(frozen=True)
class AgentObservation:
    task: TaskSpec
    frame: Frame | None
    tools: tuple[ToolSpec, ...]
    history: tuple[PublicEvent, ...]
    step_index: int
    elapsed_seconds: float


@dataclass(frozen=True)
class AgentDecision:
    tool_call: ToolCall | None
    stop: bool = False
    reason: str | None = None


class Agent(Protocol):
    id: str

    async def start(self, task: TaskSpec) -> None:
        ...

    async def decide(self, obs: AgentObservation) -> AgentDecision:
        ...

    async def close(self) -> None:
        ...
