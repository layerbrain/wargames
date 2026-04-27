from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

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
from wargames.core.control.keys import normalize_key


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


_ids = itertools.count()
_INTEGER_FIELDS = {"x", "y", "dx", "dy", "ms"}
_BUTTONS = {"left", "right", "middle"}
_ALLOWED_ARGS = {
    "move_mouse": {"id", "x", "y"},
    "mouse_down": {"id", "button"},
    "mouse_up": {"id", "button"},
    "key_down": {"id", "key"},
    "key_up": {"id", "key"},
    "scroll": {"id", "dx", "dy"},
    "wait": {"id", "ms"},
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


def _reject_invalid_wait_args(arguments: dict[str, Any]) -> None:
    if "ms" in arguments and _integer_arg(arguments, "ms") < 0:
        raise ValueError("ms must be >= 0")


def _button_property() -> dict[str, Any]:
    return {"type": "string", "enum": sorted(_BUTTONS)}


CUA_TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="move_mouse",
        description=(
            "Move the visible pointer to a window-local pixel coordinate. "
            "This does not press or release any mouse button."
        ),
        parameters=_object({"x": {"type": "integer"}, "y": {"type": "integer"}}, ["x", "y"]),
    ),
    ToolSpec(
        name="mouse_down",
        description="Press a mouse button at the current pointer position.",
        parameters=_object({"button": _button_property()}, []),
    ),
    ToolSpec(
        name="mouse_up",
        description="Release a mouse button at the current pointer position.",
        parameters=_object({"button": _button_property()}, []),
    ),
    ToolSpec(
        name="key_down",
        description="Press one keyboard key.",
        parameters=_object({"key": {"type": "string"}}, ["key"]),
    ),
    ToolSpec(
        name="key_up",
        description="Release one keyboard key.",
        parameters=_object({"key": {"type": "string"}}, ["key"]),
    ),
    ToolSpec(
        name="scroll",
        description="Scroll the target window.",
        parameters=_object({"dx": {"type": "integer"}, "dy": {"type": "integer"}}, ["dx", "dy"]),
    ),
    ToolSpec(
        name="wait",
        description="Wait without input for `ms` milliseconds (real wall-clock time).",
        parameters=_object({"ms": {"type": "integer"}}, ["ms"]),
    ),
)


def action_from_tool_call(name: str, arguments: dict[str, Any]) -> ArenaAction:
    _reject_unknown_args(name, arguments)
    _reject_invalid_integer_args(arguments)
    _reject_invalid_button_args(arguments)
    if name == "wait":
        _reject_invalid_wait_args(arguments)
    id = str(arguments.get("id") or next_id())
    if name == "move_mouse":
        return MoveMouseAction(
            id=id, x=_integer_arg(arguments, "x"), y=_integer_arg(arguments, "y")
        )
    if name == "mouse_down":
        return MouseDownAction(id=id, button=arguments.get("button", "left"))
    if name == "mouse_up":
        return MouseUpAction(id=id, button=arguments.get("button", "left"))
    if name == "key_down":
        return KeyDownAction(id=id, key=normalize_key(str(arguments["key"])))
    if name == "key_up":
        return KeyUpAction(id=id, key=normalize_key(str(arguments["key"])))
    if name == "scroll":
        return ScrollAction(
            id=id, dx=_integer_arg(arguments, "dx"), dy=_integer_arg(arguments, "dy")
        )
    if name == "wait":
        return WaitAction(id=id, ms=_integer_arg(arguments, "ms") if "ms" in arguments else 0)
    raise ValueError(f"unknown CUA tool: {name}")
