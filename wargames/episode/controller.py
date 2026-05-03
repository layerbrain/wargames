from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from wargames.core.capture.audio import AudioChunk
from wargames.core.capture.frame import Frame
from wargames.core.missions.rubric import RewardBreakdown
from wargames.core.runtime.arena import WarGames
from wargames.core.runtime.mission import Mission
from wargames.core.runtime.observation import Observation
from wargames.core.runtime.result import StepResult
from wargames.core.world.probe import HiddenStateSnapshot
from wargames.evaluation.profile import profile_registry
from wargames.evaluation.task import RunConfig, TaskSpec
from wargames.episode.evaluator import RewardEvaluator, ZERO_BREAKDOWN
from wargames.episode.recorder import Recorder
from wargames.episode.serialization import frame_to_dict, public_value, tool_call_to_dict
from wargames.harness.agent import PublicEvent, ToolCall
from wargames.runs.bus import run_bus


@dataclass(frozen=True)
class StepOutcome:
    step: int
    tick: int
    game_seconds: float
    frame: Frame | None
    audio: AudioChunk | None
    breakdown: RewardBreakdown
    reward: float
    finished: bool
    truncated: bool
    end_reason: str | None
    metadata: dict[str, object]


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    task_id: str
    total_reward: float
    breakdown: dict[str, float]
    finished: bool
    truncated: bool
    end_reason: str
    steps: int
    duration_seconds: float


class EpisodeController:
    def __init__(
        self,
        *,
        task: TaskSpec,
        run_config: RunConfig,
        wg: WarGames,
        recorder: Recorder | None = None,
        tick_rate: int = 30,
    ) -> None:
        self.task = task
        self.run_config = run_config
        self.wg = wg
        self.run_id = f"{task.id}.{uuid.uuid4().hex[:8]}"
        self.recorder = recorder or Recorder(run_id=self.run_id, task=task, run_config=run_config)
        self.tick_rate = tick_rate
        self.profile = profile_registry.get(task.game, task.reward_profile)
        self.evaluator = RewardEvaluator(self.profile)
        self.mission: Mission | None = None
        self.public_history: tuple[PublicEvent, ...] = ()
        self.latest_hidden: HiddenStateSnapshot | None = None
        self.latest_audio: AudioChunk | None = None
        self.initial_hidden: HiddenStateSnapshot | None = None
        self.last_result: StepResult | None = None
        self.total_breakdown: dict[str, float] = {}
        self.total_reward = 0.0
        self.started_at = 0.0
        self.finished = False
        self.truncated = False
        self.end_reason = "unknown"
        self._terminal_scored = False

    async def start(self, *, agent_id: str | None = None) -> Frame | None:
        self.started_at = time.monotonic()
        self.recorder.start()
        if agent_id is not None:
            self.recorder.record_agent(agent_id)
        self.mission = await self.wg.start_mission(self.task.mission_id, seed=self.task.seed)
        observation = await self.mission.observe()
        hidden = await _latest_hidden(self.mission)
        self.initial_hidden = hidden
        self.latest_hidden = hidden
        self.latest_audio = observation.audio
        self.recorder.record_initial_frame(observation.frame)
        self.recorder.record_initial_audio(observation.audio)
        self._publish("run_started", {"task": self.task.to_mapping(), "agent": {"id": agent_id}})
        if observation.frame is not None:
            self._publish(
                "frame",
                {
                    "step": 0,
                    "tick": observation.frame.captured_tick,
                    "frame": frame_to_dict(observation.frame),
                },
            )
        return observation.frame

    async def observe_public(self) -> Observation:
        if self.mission is None:
            raise RuntimeError("episode has not started")
        observation = await self.mission.observe()
        self.latest_audio = observation.audio
        return observation

    async def observe(self) -> Frame | None:
        return (await self.observe_public()).frame

    async def apply_tool_call(self, name: str, arguments: dict[str, object]) -> StepOutcome:
        if self.mission is None:
            raise RuntimeError("episode has not started")
        step = len(self.public_history)
        result = await self.mission.step(self.wg.action_from_tool_call(name, dict(arguments)))
        self.last_result = result
        self.latest_hidden = result.hidden or self.latest_hidden
        self.latest_audio = result.audio
        breakdown = await self.evaluator.score_step(result.prev_hidden, result.hidden)
        self._accumulate(breakdown)
        self.finished = result.finished
        self.truncated = result.truncated
        if result.end_reason:
            self.end_reason = result.end_reason
        elif result.finished:
            self.end_reason = "finished"
        elif result.truncated:
            self.end_reason = "truncated"
        tool_call = ToolCall(name=name, arguments=dict(arguments))
        public_event = PublicEvent(
            step=step, tool_call=tool_call, reward=breakdown.total, tick=result.tick
        )
        self.public_history = (*self.public_history, public_event)
        self.recorder.record_step(result=result, public_event=public_event, breakdown=breakdown)
        self._publish(
            "action", {"step": step, "action": tool_call_to_dict(tool_call), "tick": result.tick}
        )
        self._publish(
            "reward",
            {
                "step": step,
                "value": breakdown.total,
                "total": self.total_reward,
                "breakdown": dict(breakdown.entries),
            },
        )
        if result.frame is not None:
            self._publish(
                "frame",
                {"step": step + 1, "tick": result.tick, "frame": frame_to_dict(result.frame)},
            )
        return StepOutcome(
            step=step,
            tick=result.tick,
            game_seconds=result.tick / self.tick_rate,
            frame=result.frame,
            audio=result.audio,
            breakdown=breakdown,
            reward=breakdown.total,
            finished=result.finished,
            truncated=result.truncated,
            end_reason=self.end_reason
            if (result.finished or result.truncated)
            else result.end_reason,
            metadata=dict(result.info or {}),
        )

    async def finish(self, end_reason: str | None = None) -> StepOutcome:
        if self._terminal_scored:
            return self._outcome(ZERO_BREAKDOWN)
        self._terminal_scored = True
        prev = (
            self.last_result.prev_hidden
            if self.last_result and self.last_result.prev_hidden
            else self.initial_hidden
        )
        breakdown = await self.evaluator.score_terminal(prev, self.latest_hidden)
        self._accumulate(breakdown)
        if end_reason:
            self.end_reason = end_reason
        outcome = self._outcome(breakdown)
        self._publish("run_finished", {"summary": asdict(self.summary())})
        return outcome

    async def close(self) -> None:
        if self.mission is not None:
            await self.mission.close()
        self.recorder.write_summary(asdict(self.summary()))
        self.recorder.close()

    def summary(self) -> RunSummary:
        return RunSummary(
            run_id=self.run_id,
            task_id=self.task.id,
            total_reward=self.total_reward,
            breakdown=dict(self.total_breakdown),
            finished=self.finished,
            truncated=self.truncated,
            end_reason=self.end_reason,
            steps=len(self.public_history),
            duration_seconds=time.monotonic() - self.started_at if self.started_at else 0.0,
        )

    def _accumulate(self, breakdown: RewardBreakdown) -> None:
        self.total_reward += breakdown.total
        for key, value in breakdown.entries.items():
            self.total_breakdown[key] = self.total_breakdown.get(key, 0.0) + value

    def _outcome(self, breakdown: RewardBreakdown) -> StepOutcome:
        tick = self.latest_hidden.tick if self.latest_hidden is not None else 0
        frame = self.last_result.frame if self.last_result is not None else None
        audio = self.last_result.audio if self.last_result is not None else self.latest_audio
        return StepOutcome(
            step=len(self.public_history),
            tick=tick,
            game_seconds=tick / self.tick_rate,
            frame=frame,
            audio=audio,
            breakdown=breakdown,
            reward=breakdown.total,
            finished=self.finished,
            truncated=self.truncated,
            end_reason=self.end_reason,
            metadata={},
        )

    def _publish(self, event: str, payload: dict[str, Any]) -> None:
        run_bus.publish(
            self.run_id, {"event": event, "run_id": self.run_id, **public_value(payload)}
        )


async def _latest_hidden(mission: Mission) -> HiddenStateSnapshot | None:
    latest = getattr(mission.session, "latest_hidden", None)
    if callable(latest):
        value = latest()
        return await value if hasattr(value, "__await__") else value
    latest_probe = getattr(mission.session, "probe", None)
    if latest_probe is not None and hasattr(latest_probe, "latest"):
        return await latest_probe.latest()
    return None
