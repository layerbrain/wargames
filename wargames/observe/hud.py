from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def render_event(event: dict[str, Any]) -> str:
    name = event.get("event", "event")
    step = event.get("step")
    if name == "reward":
        return f"[{step}] reward={event.get('value', 0.0):.3f} total={event.get('total', 0.0):.3f}"
    if name == "action":
        action = event.get("action", {})
        return f"[{step}] action={action.get('name', '?')}"
    if name == "run_finished":
        summary = event.get("summary", {})
        return f"finished end={summary.get('end_reason')} reward={summary.get('total_reward')}"
    return str(name)


def render_events(events: Iterable[dict[str, Any]]) -> str:
    return "\n".join(render_event(event) for event in events)
