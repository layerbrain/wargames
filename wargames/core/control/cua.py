from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

MouseButton: TypeAlias = Literal["left", "right", "middle"]


@dataclass(frozen=True)
class WaitAction:
    id: str
    ticks: int


@dataclass(frozen=True)
class ClickAction:
    id: str
    x: int
    y: int
    button: MouseButton = "left"


@dataclass(frozen=True)
class MoveMouseAction:
    id: str
    x: int
    y: int


@dataclass(frozen=True)
class DoubleClickAction:
    id: str
    x: int
    y: int
    button: MouseButton = "left"


@dataclass(frozen=True)
class DragAction:
    id: str
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    button: MouseButton = "left"


@dataclass(frozen=True)
class KeyAction:
    id: str
    key: str
    modifiers: tuple[str, ...] = ()


@dataclass(frozen=True)
class TypeTextAction:
    id: str
    text: str


@dataclass(frozen=True)
class ScrollAction:
    id: str
    dx: int
    dy: int


ArenaAction: TypeAlias = (
    WaitAction
    | MoveMouseAction
    | ClickAction
    | DoubleClickAction
    | DragAction
    | KeyAction
    | TypeTextAction
    | ScrollAction
)
