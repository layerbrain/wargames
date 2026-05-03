from __future__ import annotations

from collections.abc import Iterable

from wargames.harness.agent import ToolCall

MAX_EVENTS_PER_TURN = 64
MAX_TURN_WAIT_MS = 5000


def events_from_payload(payload: object) -> tuple[ToolCall, ...]:
    if isinstance(payload, list):
        return tuple(event_from_mapping(item) for item in payload)
    if isinstance(payload, dict):
        return (event_from_mapping(payload),)
    raise ValueError("turn must be one input event object or an array of input event objects")


def event_from_mapping(value: object) -> ToolCall:
    if not isinstance(value, dict):
        raise ValueError("turn events must be JSON objects")
    name = value.get("name")
    if not isinstance(name, str):
        raise ValueError("turn events must include name")
    arguments = value.get("arguments", {})
    if not isinstance(arguments, dict):
        raise ValueError("turn event arguments must be a JSON object")
    return ToolCall(name=name, arguments=dict(arguments))


def validate_turn(events: Iterable[ToolCall]) -> tuple[ToolCall, ...]:
    parsed = tuple(events)
    if not parsed:
        raise ValueError("turn must contain at least one event")
    if len(parsed) > MAX_EVENTS_PER_TURN:
        raise ValueError(f"turn has {len(parsed)} events; max is {MAX_EVENTS_PER_TURN}")
    wait_ms = sum(_wait_ms(event) for event in parsed)
    if wait_ms > MAX_TURN_WAIT_MS:
        raise ValueError(f"turn waits for {wait_ms}ms; max is {MAX_TURN_WAIT_MS}ms")
    return parsed


def _wait_ms(event: ToolCall) -> int:
    if event.name != "wait":
        return 0
    return int(event.arguments.get("ms", 0))
