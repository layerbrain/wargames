from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

from wargames.core.backend.base import Backend, BackendSession
from wargames.core.capture.window import NullWindowCapture, ScreenRegionCapture
from wargames.core.config import WarGamesConfig
from wargames.core.control.cua import ArenaAction
from wargames.core.control.events import MouseEvent, Target
from wargames.core.control.injector import InputInjector, XTestInjector, XdotoolInjector
from wargames.core.control.lower import lower_cua
from wargames.core.errors import GameNotInstalled, ProbeError
from wargames.core.missions.spec import MissionSpec
from wargames.core.process.launcher import ProcessHandle, ProcessLauncher
from wargames.core.runtime.observation import Observation
from wargames.core.runtime.result import MissionSummary, StepResult
from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.redalert.window import focus_window, wait_for_window
from wargames.games.mindustry.config import MindustryConfig
from wargames.games.mindustry.missions import (
    MindustryMissionSpec,
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)
from wargames.games.mindustry.probe import JsonlStateProbe
from wargames.games.mindustry.process import (
    bootstrap_mindustry,
    locate_client_jar,
    locate_root,
    mindustry_command,
    mindustry_environment,
)
from wargames.games.mindustry.world import world_from_frame


class MindustrySession(BackendSession):
    def __init__(
        self,
        *,
        id: str,
        mission: MindustryMissionSpec,
        seed: int,
        target: Target,
        injector: InputInjector,
        probe: JsonlStateProbe,
        process: ProcessHandle,
        config: MindustryConfig,
    ) -> None:
        self.id = id
        self.mission = mission
        self.seed = seed
        self.target = target
        self.injector = injector
        self.probe = probe
        self.process = process
        self.config = config
        self.capture = (
            ScreenRegionCapture(config.frame_dir) if config.capture_frames else NullWindowCapture()
        )
        self._tick = 0
        self._last_hidden = self._snapshot(finished=False, failed=False)

    async def latest_hidden(self) -> HiddenStateSnapshot:
        latest = await self.probe.latest()
        return latest or self._last_hidden

    async def step(self, action: ArenaAction) -> StepResult:
        before = await self.probe.latest()
        before_tick = before.tick if before is not None else self._last_hidden.tick
        prev = before or self._last_hidden
        await self.injector.send_many(self.target, lower_cua(action, self.target.rect))
        hidden = await self._probe_snapshot_after(before_tick)
        self._last_hidden = hidden
        finished = bool(getattr(hidden.world.mission, "finished", False))
        failed = bool(getattr(hidden.world.mission, "failed", False))
        if self.process.process.returncode not in {None, 0}:
            failed = True
        truncated = hidden.tick >= self.mission.time_limit_ticks and not finished
        return StepResult(
            action=action,
            tick=hidden.tick,
            frame=(await self.observe()).frame,
            finished=finished,
            truncated=truncated,
            hidden=hidden,
            prev_hidden=prev,
            info={},
            end_reason="objective_complete" if finished else "defeat" if failed else None,
        )

    async def observe(self) -> Observation:
        latest = await self.probe.latest()
        tick = latest.tick if latest else self._last_hidden.tick
        frame = (
            await self.capture.capture(self.target, tick=tick)
            if self.config.capture_frames
            else None
        )
        return Observation(frame=frame)

    async def summary(self) -> MissionSummary:
        latest = await self.latest_hidden()
        finished = bool(getattr(latest.world.mission, "finished", False))
        failed = bool(getattr(latest.world.mission, "failed", False))
        if self.process.process.returncode not in {None, 0}:
            failed = True
        truncated = latest.tick >= self.mission.time_limit_ticks and not finished
        return MissionSummary(
            id=self.id,
            mission=self.mission,
            seed=self.seed,
            finished=finished,
            truncated=truncated,
            duration_ticks=latest.tick,
            end_reason="objective_complete" if finished else "defeat" if failed else None,
        )

    async def close(self) -> None:
        await self.probe.close()
        await self.process.terminate(timeout=self.config.step_timeout)

    async def center_pointer(self) -> None:
        x = self.target.rect.x + self.target.rect.width // 2
        y = self.target.rect.y + self.target.rect.height // 2
        await self.injector.send(self.target, MouseEvent(kind="move", x=x, y=y))


    def _snapshot(self, *, finished: bool, failed: bool) -> HiddenStateSnapshot:
        world = world_from_frame(
            {
                "tick": self._tick,
                "mission": {"finished": finished, "failed": failed},
                "game": {
                    "map": self.mission.map_name,
                    "wave": 0,
                    "enemies": 0,
                    "tick": self._tick,
                    "won": False,
                    "game_over": False,
                },
                "teams": [
                    {
                        "id": 1,
                        "name": "sharded",
                        "cores": 1,
                        "units": 0,
                        "buildings": 0,
                        "items": 0,
                        "core_health": 0.0,
                    }
                ],
            }
        )
        return HiddenStateSnapshot(tick=self._tick, world=world)

    async def _probe_snapshot_after(self, tick: int) -> HiddenStateSnapshot:
        try:
            return await asyncio.wait_for(self.probe.next_after(tick), timeout=2.0)
        except TimeoutError:
            latest = await self.probe.latest()
            if latest is None:
                raise ProbeError("Mindustry state probe has not produced a world snapshot")
            return latest


class MindustryBackend(Backend):
    game = "mindustry"

    def __init__(self, config: WarGamesConfig) -> None:
        if not isinstance(config, MindustryConfig):
            config = MindustryConfig(**config.__dict__)
        super().__init__(config)
        self.config: MindustryConfig = config
        self._sessions: list[MindustrySession] = []
        self._missions = self._discover_missions()
        self._bootstrapped = False

    def _discover_missions(self) -> tuple[MindustryMissionSpec, ...]:
        catalog = load_mission_catalog(self.config.missions_dir)
        if catalog:
            return catalog
        return discover(self.config.root)

    def missions(self) -> tuple[MissionSpec, ...]:
        return self._missions

    def export_missions(self, output_dir: str | Path) -> tuple[Path, ...]:
        return extract_mission_catalog(self.config.root, output_dir)

    def supports(self, mission: MissionSpec) -> bool:
        return isinstance(mission, MindustryMissionSpec) and mission.game == self.game

    async def bootstrap(self) -> None:
        if self._bootstrapped:
            return
        if sys.platform != "linux":
            raise GameNotInstalled(
                "WarGames Mindustry runs only inside its Linux Docker runtime"
            )
        bootstrap_mindustry(self.config)
        self._bootstrapped = True

    async def start(self, mission: MissionSpec, *, seed: int) -> BackendSession:
        if not self.supports(mission):
            raise ValueError(f"unsupported Mindustry mission: {mission.id}")
        await self.bootstrap()
        spec = mission  # type: ignore[assignment]
        width, height = self.config.window_size
        state_path = str(Path(self.config.probe_dir) / f"mindustry-{uuid.uuid4().hex}.jsonl")
        probe = JsonlStateProbe(state_path)
        await probe.start()
        display = os.getenv("DISPLAY", ":99")
        env = mindustry_environment(self.config, state_path=state_path, mission=spec, display=display)
        process = await ProcessLauncher().start(
            mindustry_command(locate_client_jar(self.config), spec),
            env=env,
            cwd=str(locate_root(self.config)),
            id=spec.id,
            timeout=self.config.step_timeout,
        )
        target = await wait_for_window(
            pid=process.pid,
            display=env.get("DISPLAY"),
            width=width,
            height=height,
            timeout=self.config.step_timeout,
            title="Mindustry",
        )
        await focus_window(target)
        await _wait_for_probe(probe, timeout=self.config.step_timeout)
        session = MindustrySession(
            id=f"{spec.id}:{seed}:{uuid.uuid4().hex[:8]}",
            mission=spec,
            seed=seed,
            target=target,
            injector=self._injector_for(target),
            probe=probe,
            process=process,
            config=self.config,
        )
        await session.center_pointer()
        self._sessions.append(session)
        return session

    def _injector_for(self, target: Target) -> InputInjector:
        if self.config.injector_transport == "xdotool":
            return XdotoolInjector()
        return XTestInjector()

    async def close(self) -> None:
        for session in tuple(self._sessions):
            await session.close()
        self._sessions.clear()


async def _wait_for_probe(probe: JsonlStateProbe, *, timeout: float) -> None:
    try:
        await asyncio.wait_for(probe.next(), timeout=timeout)
    except TimeoutError as exc:
        raise ProbeError("Mindustry state probe did not produce a snapshot") from exc
