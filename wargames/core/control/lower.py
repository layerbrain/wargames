from __future__ import annotations

from collections.abc import Iterable

from wargames.core.control.cua import (
    ArenaAction,
    ClickAction,
    DoubleClickAction,
    DragAction,
    KeyAction,
    MoveMouseAction,
    ScrollAction,
    TypeTextAction,
    WaitAction,
)
from wargames.core.control.events import InputEvent, KeyEvent, MouseEvent, ScrollEvent, WaitEvent, WindowRect
from wargames.core.errors import UnsupportedAction


def _point(win: WindowRect, x: int, y: int) -> tuple[int, int]:
    return win.screen_point(x, y)


def _drag_points(start: tuple[int, int], end: tuple[int, int], *, segments: int = 8) -> tuple[tuple[int, int], ...]:
    sx, sy = start
    ex, ey = end
    return tuple(
        (
            round(sx + ((ex - sx) * step / segments)),
            round(sy + ((ey - sy) * step / segments)),
        )
        for step in range(1, segments + 1)
    )


def lower_cua(action: ArenaAction, win: WindowRect) -> Iterable[InputEvent]:
    if isinstance(action, WaitAction):
        return (WaitEvent(ticks=action.ticks),)
    if isinstance(action, MoveMouseAction):
        x, y = _point(win, action.x, action.y)
        return (MouseEvent(kind="move", x=x, y=y),)
    if isinstance(action, ClickAction):
        x, y = _point(win, action.x, action.y)
        return (
            MouseEvent(kind="move", x=x, y=y, button=action.button),
            MouseEvent(kind="down", x=x, y=y, button=action.button),
            MouseEvent(kind="up", x=x, y=y, button=action.button),
        )
    if isinstance(action, DoubleClickAction):
        x, y = _point(win, action.x, action.y)
        return (
            MouseEvent(kind="move", x=x, y=y, button=action.button),
            MouseEvent(kind="down", x=x, y=y, button=action.button),
            MouseEvent(kind="up", x=x, y=y, button=action.button),
            MouseEvent(kind="down", x=x, y=y, button=action.button),
            MouseEvent(kind="up", x=x, y=y, button=action.button),
        )
    if isinstance(action, DragAction):
        sx, sy = _point(win, action.start_x, action.start_y)
        ex, ey = _point(win, action.end_x, action.end_y)
        return (
            MouseEvent(kind="move", x=sx, y=sy, button=action.button),
            MouseEvent(kind="down", x=sx, y=sy, button=action.button),
            *(MouseEvent(kind="move", x=x, y=y, button=action.button) for x, y in _drag_points((sx, sy), (ex, ey))),
            MouseEvent(kind="up", x=ex, y=ey, button=action.button),
        )
    if isinstance(action, KeyAction):
        return (
            KeyEvent(kind="down", key=action.key, modifiers=action.modifiers),
            KeyEvent(kind="up", key=action.key, modifiers=action.modifiers),
        )
    if isinstance(action, TypeTextAction):
        return (KeyEvent(kind="type", key="", text=action.text),)
    if isinstance(action, ScrollAction):
        return (ScrollEvent(dx=action.dx, dy=action.dy),)
    raise UnsupportedAction(f"unsupported action: {action!r}")
