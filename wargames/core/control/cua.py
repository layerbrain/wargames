from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

MouseButton: TypeAlias = Literal["left", "right", "middle"]


@dataclass(frozen=True)
class WaitAction:
    id: str
    ms: int = 0


@dataclass(frozen=True)
class MoveMouseAction:
    id: str
    x: int
    y: int


@dataclass(frozen=True)
class MouseDownAction:
    id: str
    button: MouseButton = "left"


@dataclass(frozen=True)
class MouseUpAction:
    id: str
    button: MouseButton = "left"


@dataclass(frozen=True)
class KeyDownAction:
    id: str
    key: str


@dataclass(frozen=True)
class KeyUpAction:
    id: str
    key: str


@dataclass(frozen=True)
class ScrollAction:
    id: str
    dx: int
    dy: int


ArenaAction: TypeAlias = (
    WaitAction
    | MoveMouseAction
    | MouseDownAction
    | MouseUpAction
    | KeyDownAction
    | KeyUpAction
    | ScrollAction
)
