from __future__ import annotations

import base64
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from wargames.core.capture.frame import Frame
from wargames.core.missions.rubric import RewardBreakdown
from wargames.harness.agent import PublicEvent, ToolCall


def frame_to_dict(frame: Frame | None) -> dict[str, Any] | None:
    if frame is None:
        return None
    return asdict(frame)


def public_frame_to_dict(frame: Frame | None) -> dict[str, Any] | None:
    if frame is None:
        return None
    payload: dict[str, Any] = {
        "id": frame.id,
        "width": frame.width,
        "height": frame.height,
        "captured_tick": frame.captured_tick,
        "mime": frame.mime,
    }
    if frame.image_b64:
        payload["image_b64"] = frame.image_b64
    elif frame.image_path:
        payload["image_b64"] = base64.b64encode(Path(frame.image_path).read_bytes()).decode()
    return payload


def agent_observation_to_dict(observation: Any) -> dict[str, Any]:
    return {
        "task": public_value(observation.task),
        "frame": public_frame_to_dict(observation.frame),
        "history": [public_event_to_dict(event) for event in observation.history],
        "step_index": observation.step_index,
        "elapsed_seconds": observation.elapsed_seconds,
    }


def tool_call_to_dict(tool_call: ToolCall) -> dict[str, Any]:
    return {"name": tool_call.name, "arguments": public_value(tool_call.arguments)}


def public_event_to_dict(event: PublicEvent) -> dict[str, Any]:
    payload: dict[str, Any] = {"step": event.step, "action": tool_call_to_dict(event.tool_call)}
    if event.reward is not None:
        payload["reward"] = event.reward
    if event.tick is not None:
        payload["tick"] = event.tick
    return payload


def breakdown_to_dict(breakdown: RewardBreakdown | None) -> dict[str, Any]:
    if breakdown is None:
        return {"total": 0.0, "entries": {}}
    return {"total": breakdown.total, "entries": dict(breakdown.entries)}


def public_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {key: public_value(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {
            str(key): public_value(item) for key, item in value.items() if not _hidden_key(str(key))
        }
    if isinstance(value, (list, tuple)):
        return [public_value(item) for item in value]
    return value


def _hidden_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in {
        "hidden",
        "prev_hidden",
        "world",
        "units",
        "buildings",
        "resources",
        "visible_tiles",
    }
