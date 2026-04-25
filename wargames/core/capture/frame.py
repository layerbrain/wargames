from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Frame:
    id: str
    width: int
    height: int
    captured_tick: int
    image_path: str | None = None
    image_b64: str | None = None
    mime: str = "image/png"
