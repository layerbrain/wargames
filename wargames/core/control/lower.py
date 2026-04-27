from __future__ import annotations

from collections.abc import Iterable

from wargames.core.control.cua import (
    ArenaAction,
    KeyDownAction,
    KeyUpAction,
    MoveMouseAction,
    MouseDownAction,
    MouseUpAction,
    ScrollAction,
    WaitAction,
)
from wargames.core.control.events import (
    InputEvent,
    KeyEvent,
    MouseEvent,
    ScrollEvent,
    WaitEvent,
    WindowRect,
)
from wargames.core.errors import UnsupportedAction


def _point(win: WindowRect, x: int, y: int) -> tuple[int, int]:
    return win.screen_point(x, y)


def lower_cua(action: ArenaAction, win: WindowRect) -> Iterable[InputEvent]:
    if isinstance(action, WaitAction):
        return (WaitEvent(ms=action.ms),)
    if isinstance(action, MoveMouseAction):
        x, y = _point(win, action.x, action.y)
        return (MouseEvent(kind="move", x=x, y=y),)
    if isinstance(action, MouseDownAction):
        return (MouseEvent(kind="down", button=action.button),)
    if isinstance(action, MouseUpAction):
        return (MouseEvent(kind="up", button=action.button),)
    if isinstance(action, KeyDownAction):
        return (KeyEvent(kind="down", key=action.key),)
    if isinstance(action, KeyUpAction):
        return (KeyEvent(kind="up", key=action.key),)
    if isinstance(action, ScrollAction):
        return (ScrollEvent(dx=action.dx, dy=action.dy),)
    raise UnsupportedAction(f"unsupported action: {action!r}")
