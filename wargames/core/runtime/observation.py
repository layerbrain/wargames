from __future__ import annotations

from dataclasses import dataclass

from wargames.core.capture.frame import Frame


@dataclass(frozen=True)
class Observation:
    frame: Frame | None = None
