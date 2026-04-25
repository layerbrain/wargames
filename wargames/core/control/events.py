from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from wargames.core.control.cua import MouseButton

MouseEventKind: TypeAlias = Literal["move", "down", "up"]
KeyEventKind: TypeAlias = Literal["down", "up", "type"]


@dataclass(frozen=True)
class WindowRect:
    x: int
    y: int
    width: int
    height: int

    def screen_point(self, x: int, y: int) -> tuple[int, int]:
        return self.x + x, self.y + y


@dataclass(frozen=True)
class Target:
    pid: int | None
    window_id: int | str | None
    rect: WindowRect
    display: str | None = None


@dataclass(frozen=True)
class MouseEvent:
    kind: MouseEventKind
    x: int
    y: int
    button: MouseButton = "left"


@dataclass(frozen=True)
class KeyEvent:
    kind: KeyEventKind
    key: str
    modifiers: tuple[str, ...] = ()
    text: str | None = None


@dataclass(frozen=True)
class ScrollEvent:
    dx: int
    dy: int


@dataclass(frozen=True)
class WaitEvent:
    ticks: int


InputEvent: TypeAlias = MouseEvent | KeyEvent | ScrollEvent | WaitEvent


def x11_button(button: MouseButton) -> int:
    return {"left": 1, "middle": 2, "right": 3}[button]
