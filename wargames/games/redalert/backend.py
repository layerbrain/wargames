from __future__ import annotations

import os
import sys
import uuid
import asyncio
from pathlib import Path

from wargames.core.backend.base import Backend, BackendSession
from wargames.core.capture.window import NullWindowCapture, ScreenRegionCapture
from wargames.core.config import WarGamesConfig
from wargames.core.control.cua import (
    ArenaAction,
    ClickAction,
    DoubleClickAction,
    DragAction,
    KeyAction,
    MoveMouseAction,
    ScrollAction,
    TypeTextAction,
    WaitAction,
)
from wargames.core.control.events import MouseEvent, Target, WindowRect
from wargames.core.control.injector import InputInjector, XTestInjector, XdotoolInjector
from wargames.core.control.lower import lower_cua
from wargames.core.errors import GameNotInstalled
from wargames.core.missions.spec import MissionSpec
from wargames.core.process.launcher import ProcessHandle, ProcessLauncher
from wargames.core.runtime.observation import Observation
from wargames.core.runtime.result import MissionSummary, StepResult
from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.redalert.config import RedAlertConfig
from wargames.games.redalert.missions import RedAlertMissionSpec, discover, fallback_missions
from wargames.games.redalert.probe import SocketStateProbe
from wargames.games.redalert.process import (
    bootstrap_openra,
    locate_openra,
    openra_command,
    openra_environment,
    verify_probe_installed,
)
from wargames.games.redalert.window import focus_window, wait_for_window


class RedAlertSession(BackendSession):
    def __init__(
        self,
        *,
        id: str,
        mission: RedAlertMissionSpec,
        seed: int,
        target: Target,
        injector: InputInjector,
        probe: SocketStateProbe,
        process: ProcessHandle | None,
        config: RedAlertConfig,
    ) -> None:
        self.id = id
        self.mission = mission
        self.seed = seed
        self.target = target
        self.injector = injector
        self.probe = probe
        self.process = process
        self.config = config
        self.capture = ScreenRegionCapture(config.frame_dir) if config.capture_frames else NullWindowCapture()
        self._last_hidden: HiddenStateSnapshot | None = None

    async def step(self, action: ArenaAction) -> StepResult:
        before = await self.probe.latest()
        before_tick = before.tick if before is not None else -1
        prev = self._last_hidden or before
        if _recenter_before_action(action):
            await self.center_pointer()
        await self.injector.send_many(self.target, lower_cua(action, self.target.rect))
        if _recenter_after_action(action):
            await self.center_pointer()
        try:
            hidden = await asyncio.wait_for(self.probe.next_after(before_tick), timeout=0.5)
        except TimeoutError:
            hidden = await self.probe.latest() or before
        if hidden is None:
            raise RuntimeError("Red Alert probe has not produced a world snapshot")
        self._last_hidden = hidden
        finished = bool(hidden.world.mission.finished)
        truncated = hidden.tick >= self.mission.time_limit_ticks and not finished
        frame = (await self.observe()).frame
        return StepResult(
            action=action,
            tick=hidden.tick,
            frame=frame,
            finished=finished,
            truncated=truncated,
            hidden=hidden,
            prev_hidden=prev,
            info={},
            end_reason="objective_complete" if finished else None,
        )

    async def observe(self) -> Observation:
        latest = await self.probe.latest()
        tick = latest.tick if latest else 0
        frame = await self.capture.capture(self.target, tick=tick) if self.config.capture_frames else None
        return Observation(frame=frame)

    async def center_pointer(self) -> None:
        x = self.target.rect.x + self.target.rect.width // 2
        y = self.target.rect.y + self.target.rect.height // 2
        await self.injector.send(self.target, MouseEvent(kind="move", x=x, y=y))

    async def summary(self) -> MissionSummary:
        latest = await self.probe.latest()
        tick = latest.tick if latest else 0
        finished = bool(latest and latest.world.mission.finished)
        truncated = bool(latest and latest.tick >= self.mission.time_limit_ticks and not finished)
        return MissionSummary(
            id=self.id,
            mission=self.mission,
            seed=self.seed,
            finished=finished,
            truncated=truncated,
            duration_ticks=tick,
            end_reason="objective_complete" if finished else None,
        )

    async def close(self) -> None:
        await self.probe.close()
        if self.process is not None:
            await self.process.terminate(timeout=self.config.step_timeout)


class RedAlertBackend(Backend):
    game = "redalert"

    def __init__(self, config: WarGamesConfig) -> None:
        if not isinstance(config, RedAlertConfig):
            config = RedAlertConfig(**config.__dict__)
        super().__init__(config)
        self.config: RedAlertConfig = config
        self._sessions: list[RedAlertSession] = []
        self._missions = self._discover_missions()
        self._bootstrapped = False

    def _discover_missions(self) -> tuple[RedAlertMissionSpec, ...]:
        if self.config.openra_root:
            found = discover(self.config.openra_root)
            if found:
                return found
        return fallback_missions()

    def missions(self) -> tuple[MissionSpec, ...]:
        return self._missions

    def supports(self, mission: MissionSpec) -> bool:
        return isinstance(mission, RedAlertMissionSpec) and mission.game == self.game

    async def bootstrap(self) -> None:
        if self._bootstrapped:
            return
        if sys.platform != "linux":
            raise GameNotInstalled("WarGames RedAlert runs only inside the Linux/Xvfb runtime box")
        bootstrap_openra(self.config)
        self._bootstrapped = True

    async def start(self, mission: MissionSpec, *, seed: int) -> BackendSession:
        if not self.supports(mission):
            raise ValueError(f"unsupported RedAlert mission: {mission.id}")
        await self.bootstrap()
        spec = mission  # type: ignore[assignment]
        socket_path = str(Path(self.config.probe_dir) / f"{uuid.uuid4().hex}.sock")
        probe = SocketStateProbe(socket_path)
        await probe.start()
        process: ProcessHandle | None = None
        width, height = self.config.openra_window_size
        verify_probe_installed(self.config)
        binary = locate_openra(self.config)
        command = openra_command(binary, spec, self.config)
        display = os.getenv("DISPLAY", ":99")
        env = openra_environment(self.config, probe_socket=socket_path, display=display)
        process = await ProcessLauncher().start(command, env=env, timeout=self.config.step_timeout, id=spec.id)
        target = await wait_for_window(
            pid=process.pid,
            display=env.get("DISPLAY"),
            width=width,
            height=height,
            timeout=self.config.step_timeout,
        )
        await focus_window(target)
        injector = self._injector_for(target)
        await injector.send(target, MouseEvent(kind="move", x=target.rect.x + target.rect.width // 2, y=target.rect.y + target.rect.height // 2))
        await probe.wait_connected(self.config.step_timeout)
        await probe.next()
        await injector.send(target, MouseEvent(kind="move", x=target.rect.x + target.rect.width // 2, y=target.rect.y + target.rect.height // 2))
        session = RedAlertSession(
            id=f"{spec.id}:{seed}",
            mission=spec,
            seed=seed,
            target=target,
            injector=injector,
            probe=probe,
            process=process,
            config=self.config,
        )
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


def _recenter_after_action(action: ArenaAction) -> bool:
    return not isinstance(action, MoveMouseAction)


def _recenter_before_action(action: ArenaAction) -> bool:
    return isinstance(action, (WaitAction, KeyAction, TypeTextAction, ScrollAction))
