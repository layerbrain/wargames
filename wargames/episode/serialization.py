from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from wargames.core.capture.frame import Frame
from wargames.core.missions.rubric import RewardBreakdown


def frame_to_dict(frame: Frame | None) -> dict[str, Any] | None:
    if frame is None:
        return None
    return asdict(frame)


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
        return {str(key): public_value(item) for key, item in value.items() if not _hidden_key(str(key))}
    if isinstance(value, (list, tuple)):
        return [public_value(item) for item in value]
    return value


def _hidden_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in {"hidden", "prev_hidden", "world", "units", "buildings", "resources", "visible_tiles"}
