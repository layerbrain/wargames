from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Literal

SplitName = Literal["debug", "train", "validation", "test", "curriculum"]
LaunchMode = Literal["direct", "menu"]
PlayMode = Literal["sampled", "streaming"]
RecorderMode = Literal["none", "summary_only", "full"]
VideoMode = Literal["none", "frames"]

SPLITS: tuple[SplitName, ...] = ("debug", "train", "validation", "test", "curriculum")


@dataclass(frozen=True)
class TaskSpec:
    id: str
    game: str
    mission_id: str
    seed: int
    split: SplitName
    launch_mode: LaunchMode = "direct"
    play_mode: PlayMode = "sampled"
    max_steps: int = 512
    max_wall_seconds: int = 900
    reward_profile: str = "standard"
    prompt: str = ""
    tags: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, data: dict[str, Any], *, split: SplitName | None = None) -> "TaskSpec":
        game = str(data["game"])
        mission_id = str(data["mission_id"])
        seed = int(data["seed"])
        active_split = split or _split(str(data["split"]))
        task_id = str(data.get("id") or canonical_task_id(game, mission_id, seed))
        tags = tuple(str(tag) for tag in data.get("tags", ()))
        return cls(
            id=task_id,
            game=game,
            mission_id=mission_id,
            seed=seed,
            split=active_split,
            launch_mode=_launch_mode(str(data.get("launch_mode", "direct"))),
            play_mode=_play_mode(str(data.get("play_mode", "sampled"))),
            max_steps=int(data.get("max_steps", 512)),
            max_wall_seconds=int(data.get("max_wall_seconds", 900)),
            reward_profile=str(data.get("reward_profile", "standard")),
            prompt=str(data.get("prompt", "")),
            tags=tags,
        )

    def with_reward_profile(self, reward_profile: str) -> "TaskSpec":
        return replace(self, reward_profile=reward_profile)

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunConfig:
    recorder_mode: RecorderMode = "summary_only"
    video_mode: VideoMode = "none"
    frame_sample_rate: int = 1
    write_trace: bool = False
    out_dir: str = "runs"

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "RunConfig":
        return cls(
            recorder_mode=_recorder_mode(str(data.get("recorder_mode", "summary_only"))),
            video_mode=_video_mode(str(data.get("video_mode", "none"))),
            frame_sample_rate=max(1, int(data.get("frame_sample_rate", 1))),
            write_trace=bool(data.get("write_trace", False)),
            out_dir=str(data.get("out_dir", "runs")),
        )

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)


def canonical_task_id(game: str, mission_id: str, seed: int) -> str:
    return f"{game}.{mission_id}.seed-{seed:06d}"


def _split(value: str) -> SplitName:
    if value not in SPLITS:
        raise ValueError(f"invalid split: {value}")
    return value  # type: ignore[return-value]


def _launch_mode(value: str) -> LaunchMode:
    if value not in {"direct", "menu"}:
        raise ValueError(f"invalid launch mode: {value}")
    return value  # type: ignore[return-value]


def _play_mode(value: str) -> PlayMode:
    if value not in {"sampled", "streaming"}:
        raise ValueError(f"invalid play mode: {value}")
    return value  # type: ignore[return-value]


def _recorder_mode(value: str) -> RecorderMode:
    if value not in {"none", "summary_only", "full"}:
        raise ValueError(f"invalid recorder mode: {value}")
    return value  # type: ignore[return-value]


def _video_mode(value: str) -> VideoMode:
    if value not in {"none", "frames"}:
        raise ValueError(f"invalid video mode: {value}")
    return value  # type: ignore[return-value]
