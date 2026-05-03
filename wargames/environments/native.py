from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, replace
from typing import TypeAlias, TypeVar

from wargames.core.capture.frame import Frame
from wargames.core.config import WarGamesConfig
from wargames.core.runtime.arena import GameDescriptor, WarGames
from wargames.episode.controller import EpisodeController, StepOutcome
from wargames.evaluation.task import RunConfig, TaskSpec, canonical_task_id
from wargames.environments.actions import ActionSet, GameAction, action_set_for
from wargames.games.registry import load_game

EnvObservation: TypeAlias = dict[str, object]
EnvInfo: TypeAlias = dict[str, object]
StartResult: TypeAlias = tuple[EnvObservation, EnvInfo]
EnvStepResult: TypeAlias = tuple[EnvObservation, float, bool, bool, EnvInfo]
T = TypeVar("T")


class WarGamesEnv:
    def __init__(
        self,
        *,
        game: str | GameDescriptor,
        mission: str,
        reward_profile: str = "standard",
        seed: int = 0,
        max_steps: int = 512,
        max_wall_seconds: int = 900,
        run_config: RunConfig | None = None,
        config: WarGamesConfig | None = None,
        action_set: ActionSet | None = None,
        tick_rate: int = 30,
    ) -> None:
        self.game = load_game(game) if isinstance(game, str) else game
        self.task = TaskSpec(
            id=canonical_task_id(self.game.id, mission, seed),
            game=self.game.id,
            mission_id=mission,
            seed=seed,
            max_steps=max_steps,
            max_wall_seconds=max_wall_seconds,
            reward_profile=reward_profile,
        )
        self.run_config = run_config or RunConfig(recorder_mode="none", video_mode="none")
        self.config = config or replace(self.game.config_cls.from_env(), capture_frames=True)
        self.action_set = action_set or action_set_for(self.game.id)
        self.tick_rate = tick_rate
        self._wg: WarGames | None = None
        self._controller: EpisodeController | None = None
        self._sync_loop: asyncio.AbstractEventLoop | None = None
        self._sync_lock = threading.RLock()
        self._closed = False
        self._done = False
        self._started_at = 0.0

    @property
    def actions(self) -> tuple[str, ...]:
        return self.action_set.ids()

    def start(self) -> StartResult | Awaitable[StartResult]:
        return self._auto(self._start)

    def step(self, action: int | str) -> EnvStepResult | Awaitable[EnvStepResult]:
        return self._auto(lambda: self._step(action))

    def close(self) -> None | Awaitable[None]:
        async def _close_from_running_loop() -> None:
            await self._close()
            with self._sync_lock:
                self._close_sync_loop()

        if _in_running_loop():
            return _close_from_running_loop()
        with self._sync_lock:
            if self._sync_loop is not None and not self._sync_loop.is_closed():
                self._sync_loop.run_until_complete(self._close())
                self._close_sync_loop()
            else:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(self._close())
                finally:
                    loop.close()
        return None

    async def _start(self) -> StartResult:
        self._ensure_open()
        if self._controller is not None:
            raise RuntimeError("environment has already started")
        self._started_at = time.monotonic()
        self._wg = await WarGames.for_game(self.game, self.config).__aenter__()
        self._controller = EpisodeController(
            task=self.task,
            run_config=self.run_config,
            wg=self._wg,
            tick_rate=self.tick_rate,
        )
        frame = await self._controller.start(agent_id="native-env")
        return self._observation(frame=frame, tick=frame.captured_tick if frame else 0), {
            "game": self.task.game,
            "mission": self.task.mission_id,
            "reward_profile": self.task.reward_profile,
            "actions": self.actions,
        }

    async def _step(self, action: int | str) -> EnvStepResult:
        self._ensure_ready()
        assert self._controller is not None
        selected = self.action_set.resolve(action)
        reward = 0.0
        outcome: StepOutcome | None = None
        end_reason: str | None = None

        for tool_call in selected.tool_calls:
            outcome = await self._controller.apply_tool_call(tool_call.name, tool_call.arguments)
            reward += outcome.reward
            end_reason = self._end_reason(outcome)
            if end_reason is not None:
                break

        if outcome is None:
            raise RuntimeError(f"action has no tool calls: {selected.id}")

        terminated = outcome.finished
        truncated = outcome.truncated
        if not terminated and not truncated:
            end_reason = self._budget_end_reason()
            if end_reason == "max_steps":
                self._controller.truncated = True
                self._controller.end_reason = end_reason
                truncated = True
            elif end_reason == "wall_timeout":
                self._controller.truncated = True
                self._controller.end_reason = end_reason
                truncated = True

        if terminated or truncated:
            final = await self._controller.finish(end_reason)
            reward += final.reward
            outcome = final
            self._done = True

        observation = self._observation(frame=outcome.frame, tick=outcome.tick)
        info = self._info(action=selected, end_reason=end_reason if (terminated or truncated) else None)
        return observation, reward, terminated, truncated, info

    async def _close(self) -> None:
        if self._closed:
            return
        try:
            if self._controller is not None:
                if not self._done:
                    await self._controller.finish("closed")
                await self._controller.close()
            if self._wg is not None:
                await self._wg.__aexit__(None, None, None)
        finally:
            self._controller = None
            self._wg = None
            self._closed = True

    def _auto(self, coro_factory: Callable[[], Awaitable[T]]) -> T | Awaitable[T]:
        self._ensure_open()
        if _in_running_loop():
            return coro_factory()
        with self._sync_lock:
            if self._sync_loop is None or self._sync_loop.is_closed():
                self._sync_loop = asyncio.new_event_loop()
            return self._sync_loop.run_until_complete(coro_factory())

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("environment is closed")

    def _ensure_ready(self) -> None:
        self._ensure_open()
        if self._controller is None:
            raise RuntimeError("environment has not started")
        if self._done:
            raise RuntimeError("episode has ended")

    def _close_sync_loop(self) -> None:
        loop = self._sync_loop
        self._sync_loop = None
        if loop is not None and not loop.is_closed() and not loop.is_running():
            loop.close()

    def _observation(self, *, frame: Frame | None, tick: int) -> EnvObservation:
        step = len(self._controller.public_history) if self._controller is not None else 0
        return {
            "frame": frame,
            "step": step,
            "tick": tick,
            "game_seconds": tick / self.tick_rate,
        }

    def _info(self, *, action: GameAction, end_reason: str | None) -> EnvInfo:
        assert self._controller is not None
        info: EnvInfo = {
            "action": action.id,
            "end_reason": end_reason,
            "total_reward": self._controller.total_reward,
        }
        if end_reason is not None:
            summary = self._controller.summary()
            info["reward_breakdown"] = dict(summary.breakdown)
            info["summary"] = asdict(summary)
        return info

    def _end_reason(self, outcome: StepOutcome) -> str | None:
        if outcome.finished:
            return outcome.end_reason or "finished"
        if outcome.truncated:
            return outcome.end_reason or "truncated"
        return self._budget_end_reason()

    def _budget_end_reason(self) -> str | None:
        assert self._controller is not None
        if len(self._controller.public_history) >= self.task.max_steps:
            return "max_steps"
        if time.monotonic() - self._started_at >= self.task.max_wall_seconds:
            return "wall_timeout"
        return None

    def __enter__(self) -> "WarGamesEnv":
        if _in_running_loop():
            raise RuntimeError("use 'async with WarGamesEnv(...)' inside a running event loop")
        started = self.start()
        assert not hasattr(started, "__await__")
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    async def __aenter__(self) -> "WarGamesEnv":
        await self._start()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._close()
        with self._sync_lock:
            self._close_sync_loop()


def _in_running_loop() -> bool:
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


__all__ = [
    "EnvInfo",
    "EnvObservation",
    "EnvStepResult",
    "StartResult",
    "WarGamesEnv",
]
