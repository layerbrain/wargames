from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from wargames.core.capture.frame import Frame
from wargames.core.control.cua import ArenaAction
from wargames.core.missions.spec import MissionSpec
from wargames.core.world.probe import HiddenStateSnapshot

MissionEndReason = Literal["objective_complete", "victory", "defeat", "timeout", "aborted"]


@dataclass(frozen=True)
class StepResult:
    action: ArenaAction
    tick: int
    frame: Frame | None
    finished: bool
    truncated: bool
    hidden: HiddenStateSnapshot | None
    prev_hidden: HiddenStateSnapshot | None = None
    info: dict[str, object] | None = None
    end_reason: MissionEndReason | None = None


@dataclass(frozen=True)
class MissionSummary:
    id: str
    mission: MissionSpec
    seed: int
    finished: bool
    truncated: bool
    duration_ticks: int
    end_reason: MissionEndReason | None
