from __future__ import annotations

import os
from dataclasses import dataclass, fields
from typing import Literal, get_args, get_origin, get_type_hints


def _parse_bool(value: str) -> bool:
    if value.lower() in {"1", "true", "yes", "on"}:
        return True
    if value.lower() in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean: {value!r}")


def _parse_tuple(value: str) -> tuple[int, int]:
    left, sep, right = value.replace("x", ",").partition(",")
    if not sep:
        raise ValueError(f"invalid tuple: {value!r}")
    return int(left.strip()), int(right.strip())


def _parse_field(raw: str, annotation: object) -> object:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Literal:
        if raw not in args:
            raise ValueError(f"{raw!r} is not one of {args!r}")
        return raw
    if annotation is bool:
        return _parse_bool(raw)
    if annotation is int:
        return int(raw)
    if annotation is float:
        return float(raw)
    if annotation is tuple[int, int] or (origin is tuple and args == (int, int)):
        return _parse_tuple(raw)
    return raw


@dataclass(frozen=True)
class WarGamesConfig:
    display_mode: Literal["xvfb"] = "xvfb"
    xvfb_resolution: tuple[int, int] = (1280, 720)
    frame_dir: str = "/tmp/wargames/frames"
    probe_dir: str = "/tmp/wargames/probe"
    injector_transport: Literal["xdotool", "xtest"] = "xdotool"
    capture_frames: bool = False
    step_timeout: float = 30.0
    mission_timeout: float = 1800.0
    max_ticks: int = 36_000
    lobby_port_range: tuple[int, int] = (47_000, 48_000)

    @classmethod
    def from_env(cls) -> "WarGamesConfig":
        return cls.from_env_prefix("LAYERBRAIN_WARGAMES_")

    @classmethod
    def from_env_prefix(cls, prefix: str) -> "WarGamesConfig":
        values: dict[str, object] = {}
        hints = get_type_hints(cls)
        for field in fields(cls):
            raw = os.getenv(f"{prefix}{field.name.upper()}")
            if raw is not None:
                values[field.name] = _parse_field(raw, hints[field.name])
        return cls(**values)
