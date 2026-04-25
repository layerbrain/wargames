from __future__ import annotations

from typing import Literal, TypedDict


SessionMode = Literal["sampled", "streaming"]


class ToolCall(TypedDict):
    name: str
    arguments: dict[str, object]
