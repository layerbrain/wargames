from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

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


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


_ids = itertools.count()
_INTEGER_FIELDS = {"x", "y", "start_x", "start_y", "end_x", "end_y", "dx", "dy"}
_BUTTONS = {"left", "right", "middle"}
_ALLOWED_ARGS = {
    "click": {"id", "x", "y", "button"},
    "move_mouse": {"id", "x", "y"},
    "double_click": {"id", "x", "y", "button"},
    "drag": {"id", "start_x", "start_y", "end_x", "end_y", "button"},
    "key": {"id", "key", "modifiers"},
    "type_text": {"id", "text"},
    "scroll": {"id", "dx", "dy"},
    "wait": {"id"},
}


def next_id() -> str:
    return f"a{next(_ids)}"


def _object(properties: dict[str, dict[str, Any]], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _integer_arg(arguments: dict[str, Any], name: str) -> int:
    value = arguments[name]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _reject_invalid_integer_args(arguments: dict[str, Any]) -> None:
    for name in _INTEGER_FIELDS & arguments.keys():
        _integer_arg(arguments, name)


def _reject_unknown_args(name: str, arguments: dict[str, Any]) -> None:
    allowed = _ALLOWED_ARGS.get(name)
    if allowed is None:
        return
    unknown = set(arguments) - allowed
    if unknown:
        raise ValueError(f"{name} does not accept arguments: {', '.join(sorted(unknown))}")


def _reject_invalid_button_args(arguments: dict[str, Any]) -> None:
    if "button" in arguments and arguments["button"] not in _BUTTONS:
        raise ValueError("button must be one of: left, middle, right")


def _button_property() -> dict[str, Any]:
    return {"type": "string", "enum": sorted(_BUTTONS)}


CUA_TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="click",
        description="Click a window-local pixel coordinate.",
        parameters=_object(
            {"x": {"type": "integer"}, "y": {"type": "integer"}, "button": _button_property()},
            ["x", "y"],
        ),
    ),
    ToolSpec(
        name="move_mouse",
        description=(
            "Move the visible pointer to a window-local pixel coordinate without clicking. "
            "Use edge positions only when deliberately edge-panning."
        ),
        parameters=_object({"x": {"type": "integer"}, "y": {"type": "integer"}}, ["x", "y"]),
    ),
    ToolSpec(
        name="double_click",
        description="Double-click a window-local pixel coordinate.",
        parameters=_object(
            {"x": {"type": "integer"}, "y": {"type": "integer"}, "button": _button_property()},
            ["x", "y"],
        ),
    ),
    ToolSpec(
        name="drag",
        description="Drag between two window-local pixel coordinates.",
        parameters=_object(
            {
                "start_x": {"type": "integer"},
                "start_y": {"type": "integer"},
                "end_x": {"type": "integer"},
                "end_y": {"type": "integer"},
                "button": _button_property(),
            },
            ["start_x", "start_y", "end_x", "end_y"],
        ),
    ),
    ToolSpec(
        name="key",
        description="Press a key.",
        parameters=_object({"key": {"type": "string"}, "modifiers": {"type": "array"}}, ["key"]),
    ),
    ToolSpec(
        name="type_text",
        description="Type text into the target window.",
        parameters=_object({"text": {"type": "string"}}, ["text"]),
    ),
    ToolSpec(
        name="scroll",
        description="Scroll the target window.",
        parameters=_object({"dx": {"type": "integer"}, "dy": {"type": "integer"}}, ["dx", "dy"]),
    ),
    ToolSpec(
        name="wait",
        description="Wait for exactly one game tick.",
        parameters=_object({}, []),
    ),
)


def action_from_tool_call(name: str, arguments: dict[str, Any]) -> ArenaAction:
    _reject_unknown_args(name, arguments)
    _reject_invalid_integer_args(arguments)
    _reject_invalid_button_args(arguments)
    id = str(arguments.get("id") or next_id())
    if name == "click":
        return ClickAction(
            id=id,
            x=_integer_arg(arguments, "x"),
            y=_integer_arg(arguments, "y"),
            button=arguments.get("button", "left"),
        )
    if name == "move_mouse":
        return MoveMouseAction(id=id, x=_integer_arg(arguments, "x"), y=_integer_arg(arguments, "y"))
    if name == "double_click":
        return DoubleClickAction(
            id=id,
            x=_integer_arg(arguments, "x"),
            y=_integer_arg(arguments, "y"),
            button=arguments.get("button", "left"),
        )
    if name == "drag":
        return DragAction(
            id=id,
            start_x=_integer_arg(arguments, "start_x"),
            start_y=_integer_arg(arguments, "start_y"),
            end_x=_integer_arg(arguments, "end_x"),
            end_y=_integer_arg(arguments, "end_y"),
            button=arguments.get("button", "left"),
        )
    if name == "key":
        return KeyAction(id=id, key=str(arguments["key"]), modifiers=tuple(arguments.get("modifiers", ())))
    if name == "type_text":
        return TypeTextAction(id=id, text=str(arguments["text"]))
    if name == "scroll":
        return ScrollAction(id=id, dx=_integer_arg(arguments, "dx"), dy=_integer_arg(arguments, "dy"))
    if name == "wait":
        return WaitAction(id=id, ticks=1)
    raise ValueError(f"unknown CUA tool: {name}")
