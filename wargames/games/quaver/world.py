from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MissionState:
    finished: bool = False
    failed: bool = False


@dataclass(frozen=True)
class ChartState:
    map_id: int
    mapset_id: int | None
    title: str
    artist: str
    difficulty_name: str
    mode: str
    key_count: int
    song_length_ms: int
    hit_objects: int
    long_notes: int
    mines: int
    total_judgements: int


@dataclass(frozen=True)
class GameplayState:
    song_time_ms: float
    song_time_seconds: float
    started: bool
    paused: bool
    completed: bool
    failed: bool
    health: float
    score: int
    accuracy: float
    combo: int
    max_combo: int
    total_judgement_count: int
    stats_count: int


@dataclass(frozen=True)
class JudgementState:
    marv: int = 0
    perf: int = 0
    great: int = 0
    good: int = 0
    okay: int = 0
    miss: int = 0


@dataclass(frozen=True)
class QuaverWorld:
    tick: int
    mission: MissionState
    chart: ChartState
    gameplay: GameplayState
    judgements: JudgementState


def world_from_frame(frame: dict[str, Any]) -> QuaverWorld:
    mission = frame.get("mission", {})
    chart = frame.get("chart", {})
    gameplay = frame.get("gameplay", {})
    judgements = frame.get("judgements", {})
    song_time_ms = float(gameplay.get("song_time_ms", 0.0) or 0.0)
    return QuaverWorld(
        tick=int(frame.get("tick", 0) or 0),
        mission=MissionState(
            finished=bool(mission.get("finished", False)),
            failed=bool(mission.get("failed", False)),
        ),
        chart=ChartState(
            map_id=int(chart.get("map_id", -1) or -1),
            mapset_id=_optional_int(chart.get("mapset_id")),
            title=str(chart.get("title", "")),
            artist=str(chart.get("artist", "")),
            difficulty_name=str(chart.get("difficulty_name", "")),
            mode=str(chart.get("mode", "")),
            key_count=int(chart.get("key_count", 0) or 0),
            song_length_ms=int(chart.get("song_length_ms", 0) or 0),
            hit_objects=int(chart.get("hit_objects", 0) or 0),
            long_notes=int(chart.get("long_notes", 0) or 0),
            mines=int(chart.get("mines", 0) or 0),
            total_judgements=int(chart.get("total_judgements", 0) or 0),
        ),
        gameplay=GameplayState(
            song_time_ms=song_time_ms,
            song_time_seconds=song_time_ms / 1000.0,
            started=bool(gameplay.get("started", False)),
            paused=bool(gameplay.get("paused", False)),
            completed=bool(gameplay.get("completed", False)),
            failed=bool(gameplay.get("failed", False)),
            health=float(gameplay.get("health", 0.0) or 0.0),
            score=int(gameplay.get("score", 0) or 0),
            accuracy=float(gameplay.get("accuracy", 0.0) or 0.0),
            combo=int(gameplay.get("combo", 0) or 0),
            max_combo=int(gameplay.get("max_combo", 0) or 0),
            total_judgement_count=int(gameplay.get("total_judgement_count", 0) or 0),
            stats_count=int(gameplay.get("stats_count", 0) or 0),
        ),
        judgements=JudgementState(
            marv=int(judgements.get("marv", 0) or 0),
            perf=int(judgements.get("perf", 0) or 0),
            great=int(judgements.get("great", 0) or 0),
            good=int(judgements.get("good", 0) or 0),
            okay=int(judgements.get("okay", 0) or 0),
            miss=int(judgements.get("miss", 0) or 0),
        ),
    )


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)
