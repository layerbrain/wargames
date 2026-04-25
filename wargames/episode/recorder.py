from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from wargames.core.runtime.result import StepResult
from wargames.evaluation.task import RunConfig, TaskSpec
from wargames.harness.agent import PublicEvent
from wargames.episode.serialization import breakdown_to_dict, frame_to_dict, public_value
from wargames.core.missions.rubric import RewardBreakdown


class Recorder:
    def __init__(self, *, run_id: str, task: TaskSpec, run_config: RunConfig) -> None:
        self.run_id = run_id
        self.task = task
        self.run_config = run_config
        self.root = Path(run_config.out_dir) / run_id
        self.frames = self.root / "frames"
        self._events = None
        self._rewards = None
        self._trace = None

    def start(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "task.json").write_text(json.dumps(self.task.to_mapping(), indent=2, sort_keys=True), encoding="utf-8")
        (self.root / "run_config.json").write_text(
            json.dumps(self.run_config.to_mapping(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        if self.run_config.recorder_mode == "full":
            self._events = (self.root / "events.jsonl").open("a", encoding="utf-8")
            self._rewards = (self.root / "rewards.jsonl").open("a", encoding="utf-8")
        if self.run_config.write_trace:
            self._trace = (self.root / "trace.jsonl").open("a", encoding="utf-8")
        if self.run_config.video_mode == "frames":
            self.frames.mkdir(exist_ok=True)

    def record_agent(self, agent_id: str, config: dict[str, Any] | None = None) -> None:
        payload = {"id": agent_id, "config": config or {}}
        (self.root / "agent.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def record_initial_frame(self, frame: object | None) -> None:
        if self.run_config.video_mode == "frames":
            self._write_frame(0, frame)

    def record_step(self, *, result: StepResult, public_event: PublicEvent, breakdown: RewardBreakdown) -> None:
        if self._events is not None:
            self._events.write(json.dumps(public_value(public_event), sort_keys=True) + "\n")
            self._events.flush()
        if self._rewards is not None:
            payload = {"step": public_event.step, "tick": result.tick, **breakdown_to_dict(breakdown)}
            self._rewards.write(json.dumps(payload, sort_keys=True) + "\n")
            self._rewards.flush()
        if self._trace is not None:
            self._trace.write(json.dumps(asdict(result), sort_keys=True, default=str) + "\n")
            self._trace.flush()
        if self.run_config.video_mode == "frames" and public_event.step % self.run_config.frame_sample_rate == 0:
            self._write_frame(public_event.step + 1, result.frame)

    def write_summary(self, summary: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "summary.json").write_text(json.dumps(public_value(summary), indent=2, sort_keys=True), encoding="utf-8")
        end_state = {
            "run_id": summary.get("run_id"),
            "task_id": summary.get("task_id"),
            "end_reason": summary.get("end_reason"),
            "finished": summary.get("finished"),
            "truncated": summary.get("truncated"),
            "steps": summary.get("steps"),
            "total_reward": summary.get("total_reward"),
            "breakdown": summary.get("breakdown", {}),
        }
        (self.root / "end_state.json").write_text(json.dumps(end_state, indent=2, sort_keys=True), encoding="utf-8")

    def close(self) -> None:
        for handle in (self._events, self._rewards, self._trace):
            if handle is not None:
                handle.close()

    def _write_frame(self, index: int, frame: object | None) -> None:
        data = frame_to_dict(frame) if frame is not None else None
        if not data:
            return
        image_b64 = data.get("image_b64")
        image_path = data.get("image_path")
        if image_path:
            source = Path(str(image_path))
            if source.exists():
                target = self.frames / f"{index:06d}{source.suffix or '.png'}"
                target.write_bytes(source.read_bytes())
                return
        if image_b64:
            import base64

            (self.frames / f"{index:06d}.png").write_bytes(base64.b64decode(str(image_b64)))
