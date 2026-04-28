from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MissionState:
    finished: bool = False
    failed: bool = False


@dataclass(frozen=True)
class AircraftState:
    id: str
    airport: str
    runway: str | None
    altitude_ft: float | None = None
    airspeed_kt: float | None = None
    pitch_deg: float | None = None
    roll_deg: float | None = None
    heading_deg: float | None = None
    vertical_speed_fps: float | None = None
    throttle: float | None = None
    crashed: bool | None = None


@dataclass(frozen=True)
class FlightGearWorld:
    mission: MissionState
    aircraft: AircraftState
