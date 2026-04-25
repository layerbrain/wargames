from __future__ import annotations

from dataclasses import dataclass

from wargames.core.runtime.result import StepResult


@dataclass(frozen=True)
class TraceEvent:
    id: str
    result: StepResult


class TraceStore:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def append(self, result: StepResult) -> str:
        id = f"trace-{len(self.events)}"
        self.events.append(TraceEvent(id=id, result=result))
        return id
