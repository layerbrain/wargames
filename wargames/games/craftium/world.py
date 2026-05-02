from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MissionState:
    finished: bool = False
    failed: bool = False
    truncated: bool = False


@dataclass(frozen=True)
class PlayerState:
    position: tuple[float, float, float] | None
    velocity: tuple[float, float, float] | None
    pitch: float | None
    yaw: float | None


@dataclass(frozen=True)
class VoxelState:
    available: bool
    shape: tuple[int, ...]
    nonzero_nodes: int


@dataclass(frozen=True)
class CraftiumWorld:
    tick: int
    mission: MissionState
    player: PlayerState
    voxel: VoxelState
    reward: float
    total_reward: float
    mt_dtime: float | None


def world_from_info(
    info: Mapping[str, Any],
    *,
    tick: int,
    reward: float,
    total_reward: float,
    finished: bool,
    failed: bool,
    truncated: bool,
) -> CraftiumWorld:
    return CraftiumWorld(
        tick=tick,
        mission=MissionState(finished=finished, failed=failed, truncated=truncated),
        player=PlayerState(
            position=_triple(info.get("player_pos")),
            velocity=_triple(info.get("player_vel")),
            pitch=_optional_float(info.get("player_pitch")),
            yaw=_optional_float(info.get("player_yaw")),
        ),
        voxel=_voxel(info.get("voxel_obs")),
        reward=float(reward),
        total_reward=float(total_reward),
        mt_dtime=_optional_float(info.get("mt_dtime")),
    )


def _triple(value: object) -> tuple[float, float, float] | None:
    if value is None:
        return None
    values = _sequence(value)
    if len(values) < 3:
        return None
    return float(values[0]), float(values[1]), float(values[2])


def _sequence(value: object) -> Sequence[Any]:
    if hasattr(value, "tolist"):
        converted = value.tolist()
        if isinstance(converted, list):
            return converted
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    return ()


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _voxel(value: object) -> VoxelState:
    if value is None:
        return VoxelState(available=False, shape=(), nonzero_nodes=0)
    shape = tuple(int(part) for part in getattr(value, "shape", ()))
    if hasattr(value, "__getitem__") and len(shape) >= 4:
        try:
            nodes = value[..., 0]
            nonzero = int((nodes != 0).sum())
        except Exception:
            nonzero = 0
    else:
        nonzero = 0
    return VoxelState(available=bool(shape), shape=shape, nonzero_nodes=nonzero)
