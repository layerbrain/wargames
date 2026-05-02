from __future__ import annotations

import asyncio
import base64
import io
import sys
import uuid
from pathlib import Path
from typing import Any, Protocol

from wargames.core.backend.base import Backend, BackendSession
from wargames.core.capture.frame import Frame
from wargames.core.config import WarGamesConfig
from wargames.core.control.cua import (
    ArenaAction,
    KeyDownAction,
    KeyUpAction,
    MouseDownAction,
    MoveMouseAction,
    ScrollAction,
    WaitAction,
)
from wargames.core.errors import GameNotInstalled
from wargames.core.missions.spec import MissionSpec
from wargames.core.runtime.observation import Observation
from wargames.core.runtime.result import MissionSummary, StepResult
from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.craftium.config import CraftiumConfig
from wargames.games.craftium.missions import (
    CraftiumMissionSpec,
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)
from wargames.games.craftium.world import world_from_info


class CraftiumEnv(Protocol):
    action_space: object

    def reset(self, *, seed: int | None = None) -> tuple[object, dict[str, Any]]: ...

    def step(self, action: int) -> tuple[object, float, bool, bool, dict[str, Any]]: ...

    def close(self) -> None: ...


class CraftiumSession(BackendSession):
    def __init__(
        self,
        *,
        id: str,
        mission: CraftiumMissionSpec,
        seed: int,
        env: CraftiumEnv,
        observation: object,
        info: dict[str, Any],
        config: CraftiumConfig,
    ) -> None:
        self.id = id
        self.mission = mission
        self.seed = seed
        self.env = env
        self.config = config
        self._observation = observation
        self._tick = 0
        self._total_reward = 0.0
        self._pressed: set[str] = set()
        self._last_hidden = self._snapshot(
            info,
            reward=0.0,
            finished=False,
            failed=False,
            truncated=False,
        )

    async def step(self, action: ArenaAction) -> StepResult:
        prev = self._last_hidden
        repeat = self._repeat_count(action)
        reward = 0.0
        terminated = False
        env_truncated = False
        info: dict[str, Any] = {}
        for _ in range(repeat):
            action_index = self._action_index(action)
            observation, reward, terminated, env_truncated, info = await asyncio.to_thread(
                self.env.step, action_index
            )
            self._observation = observation
            self._tick += 1
            self._total_reward += float(reward)
            if terminated or env_truncated:
                break
        finished = bool(terminated and reward >= self.mission.success_reward)
        failed = bool(terminated and not finished)
        truncated = bool(env_truncated or self._tick >= self.mission.time_limit_ticks)
        hidden = self._snapshot(
            info,
            reward=float(reward),
            finished=finished,
            failed=failed,
            truncated=truncated,
        )
        self._last_hidden = hidden
        return StepResult(
            action=action,
            tick=hidden.tick,
            frame=(await self.observe()).frame,
            finished=finished,
            truncated=truncated and not finished,
            hidden=hidden,
            prev_hidden=prev,
            info={},
            end_reason="objective_complete" if finished else "defeat" if failed else None,
        )

    async def observe(self) -> Observation:
        if not self.config.capture_frames:
            return Observation(frame=None)
        return Observation(frame=await asyncio.to_thread(self._frame))

    async def summary(self) -> MissionSummary:
        hidden = self._last_hidden
        finished = bool(getattr(hidden.world.mission, "finished", False))
        failed = bool(getattr(hidden.world.mission, "failed", False))
        truncated = bool(getattr(hidden.world.mission, "truncated", False)) and not finished
        return MissionSummary(
            id=self.id,
            mission=self.mission,
            seed=self.seed,
            finished=finished,
            truncated=truncated,
            duration_ticks=hidden.tick,
            end_reason="objective_complete" if finished else "defeat" if failed else None,
        )

    async def close(self) -> None:
        await asyncio.to_thread(self.env.close)

    def _snapshot(
        self,
        info: dict[str, Any],
        *,
        reward: float,
        finished: bool,
        failed: bool,
        truncated: bool,
    ) -> HiddenStateSnapshot:
        world = world_from_info(
            info,
            tick=self._tick,
            reward=reward,
            total_reward=self._total_reward,
            finished=finished,
            failed=failed,
            truncated=truncated,
        )
        return HiddenStateSnapshot(tick=self._tick, world=world)

    def _repeat_count(self, action: ArenaAction) -> int:
        if not isinstance(action, WaitAction) or action.ms <= 0:
            return 1
        steps = max(1, action.ms // max(1, self.config.wait_step_ms))
        return min(steps, self.config.max_wait_steps)

    def _action_index(self, action: ArenaAction) -> int:
        if isinstance(action, KeyDownAction):
            mapped = _key_action(action.key)
            if mapped:
                self._pressed.add(mapped)
                return self._index(mapped)
        if isinstance(action, KeyUpAction):
            mapped = _key_action(action.key)
            if mapped:
                self._pressed.discard(mapped)
            return 0
        if isinstance(action, MouseDownAction):
            return self._index("place" if action.button == "right" else "dig")
        if isinstance(action, MoveMouseAction):
            return self._mouse_index(action.x, action.y)
        if isinstance(action, ScrollAction):
            return self._index("slot_2" if action.dy < 0 else "slot_1")
        if isinstance(action, WaitAction):
            return self._index(self._held_action())
        return 0

    def _held_action(self) -> str | None:
        for action in (
            "dig",
            "place",
            "forward",
            "backward",
            "left",
            "right",
            "jump",
            "sneak",
        ):
            if action in self._pressed:
                return action
        return None

    def _index(self, action_name: str | None) -> int:
        if action_name is None:
            return 0
        try:
            return self.mission.action_names.index(action_name) + 1
        except ValueError:
            return 0

    def _mouse_index(self, x: int, y: int) -> int:
        width, height = self._dimensions()
        dx = x - width // 2
        dy = y - height // 2
        dead_x = max(8, width // 8)
        dead_y = max(8, height // 8)
        if abs(dx) >= abs(dy) and abs(dx) > dead_x:
            return self._index("mouse x+" if dx > 0 else "mouse x-")
        if abs(dy) > dead_y:
            return self._index("mouse y+" if dy < 0 else "mouse y-")
        return 0

    def _frame(self) -> Frame:
        data = _rgb_array(self._observation)
        width, height = self._dimensions()
        encoded = _png_bytes(data)
        path = Path(self.config.frame_dir) / f"{self._tick:06d}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded)
        return Frame(
            id=f"craftium:{self._tick}",
            width=width,
            height=height,
            captured_tick=self._tick,
            image_path=str(path),
            image_b64=base64.b64encode(encoded).decode(),
        )

    def _dimensions(self) -> tuple[int, int]:
        shape = tuple(int(part) for part in getattr(self._observation, "shape", ()))
        if len(shape) >= 2:
            return shape[1], shape[0]
        return 64, 64


class CraftiumBackend(Backend):
    game = "craftium"

    def __init__(self, config: WarGamesConfig) -> None:
        if not isinstance(config, CraftiumConfig):
            config = CraftiumConfig(**config.__dict__)
        super().__init__(config)
        self.config: CraftiumConfig = config
        self._sessions: list[CraftiumSession] = []
        self._missions = self._discover_missions()
        self._bootstrapped = False

    def _discover_missions(self) -> tuple[CraftiumMissionSpec, ...]:
        catalog = load_mission_catalog(self.config.missions_dir)
        if catalog:
            return catalog
        return discover(self.config.root)

    def missions(self) -> tuple[MissionSpec, ...]:
        return self._missions

    def export_missions(self, output_dir: str | Path) -> tuple[Path, ...]:
        return extract_mission_catalog(self.config.root, output_dir)

    def supports(self, mission: MissionSpec) -> bool:
        return isinstance(mission, CraftiumMissionSpec) and mission.game == self.game

    async def bootstrap(self) -> None:
        if self._bootstrapped:
            return
        if sys.platform != "linux":
            raise GameNotInstalled("WarGames Craftium runs only inside its Linux Docker runtime")
        _import_craftium()
        self._bootstrapped = True

    async def start(self, mission: MissionSpec, *, seed: int) -> BackendSession:
        if not self.supports(mission):
            raise ValueError(f"unsupported Craftium mission: {mission.id}")
        await self.bootstrap()
        spec = mission  # type: ignore[assignment]
        env = await asyncio.to_thread(_make_env, spec, self.config)
        observation, info = await asyncio.to_thread(env.reset, seed=seed)
        session = CraftiumSession(
            id=f"{spec.id}:{seed}:{uuid.uuid4().hex[:8]}",
            mission=spec,
            seed=seed,
            env=env,
            observation=observation,
            info=info,
            config=self.config,
        )
        self._sessions.append(session)
        return session

    async def close(self) -> None:
        for session in tuple(self._sessions):
            await session.close()
        self._sessions.clear()


def _import_craftium() -> None:
    try:
        import craftium  # noqa: F401
        import gymnasium  # noqa: F401
    except Exception as exc:
        raise GameNotInstalled(
            "Craftium is not installed in this runtime. Run `wargames install --game craftium`."
        ) from exc


def _make_env(mission: CraftiumMissionSpec, config: CraftiumConfig) -> CraftiumEnv:
    _import_craftium()
    import gymnasium as gym  # type: ignore[import-not-found]

    return gym.make(
        mission.env_id,
        enable_voxel_obs=config.enable_voxel_obs,
        render_mode="rgb_array",
        run_dir_prefix=config.run_dir_prefix,
        sync_mode=True,
    )


def _key_action(key: str) -> str | None:
    return {
        "w": "forward",
        "ArrowUp": "forward",
        "s": "backward",
        "ArrowDown": "backward",
        "a": "left",
        "ArrowLeft": "left",
        "d": "right",
        "ArrowRight": "right",
        "Space": "jump",
        "Shift": "sneak",
        "Control": "dig",
        "e": "place",
        "1": "slot_1",
        "2": "slot_2",
        "3": "slot_3",
        "4": "slot_4",
        "5": "slot_5",
    }.get(key)


def _rgb_array(observation: object) -> Any:
    try:
        import numpy as np  # type: ignore[import-not-found]
    except Exception as exc:
        raise GameNotInstalled("numpy is required to encode Craftium observations") from exc
    array = np.asarray(observation)
    if array.ndim == 2:
        array = np.repeat(array[:, :, None], 3, axis=2)
    if array.ndim == 3 and array.shape[2] == 1:
        array = np.repeat(array, 3, axis=2)
    if array.dtype != np.uint8:
        array = array.clip(0, 255).astype(np.uint8)
    return array


def _png_bytes(array: Any) -> bytes:
    try:
        from PIL import Image  # type: ignore[import-not-found]
    except Exception as exc:
        raise GameNotInstalled("Pillow is required to encode Craftium frames") from exc
    buffer = io.BytesIO()
    Image.fromarray(array).save(buffer, format="PNG")
    return buffer.getvalue()
