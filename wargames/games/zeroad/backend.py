from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
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
from wargames.core.errors import GameNotInstalled
from wargames.core.missions.spec import MissionSpec
from wargames.core.process.launcher import ProcessHandle, ProcessLauncher
from wargames.core.runtime.observation import Observation
from wargames.core.runtime.result import MissionSummary, StepResult
from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.redalert.window import focus_window, wait_for_window
from wargames.games.zeroad.config import ZeroADConfig
from wargames.games.zeroad.missions import (
    ZeroADMissionSpec,
    discover,
    extract_mission_catalog,
    fallback_missions,
    load_mission_catalog,
)
from wargames.games.zeroad.process import (
    bootstrap_zeroad,
    locate_zeroad,
    prepare_zeroad_runtime_environment,
    zeroad_command,
    zeroad_environment,
    zeroad_working_dir,
)
from wargames.games.zeroad.rl_client import ZeroADRLClient
from wargames.games.zeroad.world import world_from_state


class ZeroADSession(BackendSession):
    def __init__(
        self,
        *,
        id: str,
        mission: ZeroADMissionSpec,
        seed: int,
        target: Target,
        injector: InputInjector,
        client: ZeroADRLClient,
        process: ProcessHandle | None,
        config: ZeroADConfig,
        initial_state: dict[str, object],
    ) -> None:
        self.id = id
        self.mission = mission
        self.seed = seed
        self.target = target
        self.injector = injector
        self.client = client
        self.process = process
        self.config = config
        self.capture = (
            ScreenRegionCapture(config.frame_dir) if config.capture_frames else NullWindowCapture()
        )
        self._last_hidden = self._snapshot(initial_state)

    async def step(self, action: ArenaAction) -> StepResult:
        prev = self._last_hidden
        await self.injector.send_many(self.target, lower_cua(action, self.target.rect))
        state = await self.client.step()
        hidden = self._snapshot(state)
        self._last_hidden = hidden
        finished = bool(getattr(hidden.world.mission, "finished", False))
        failed = bool(getattr(hidden.world.mission, "failed", False))
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
            end_reason="objective_complete" if finished else "defeat" if failed else None,
        )

    async def observe(self) -> Observation:
        frame = (
            await self.capture.capture(self.target, tick=self._last_hidden.tick)
            if self.config.capture_frames
            else None
        )
        return Observation(frame=frame)

    async def center_pointer(self) -> None:
        x = self.target.rect.x + self.target.rect.width // 2
        y = self.target.rect.y + self.target.rect.height // 2
        await self.injector.send(self.target, MouseEvent(kind="move", x=x, y=y))

    async def summary(self) -> MissionSummary:
        finished = bool(getattr(self._last_hidden.world.mission, "finished", False))
        failed = bool(getattr(self._last_hidden.world.mission, "failed", False))
        if self.process is not None and self.process.process.returncode not in {None, 0}:
            failed = True
        truncated = self._last_hidden.tick >= self.mission.time_limit_ticks and not finished
        return MissionSummary(
            id=self.id,
            mission=self.mission,
            seed=self.seed,
            finished=finished,
            truncated=truncated,
            duration_ticks=self._last_hidden.tick,
            end_reason="objective_complete" if finished else "defeat" if failed else None,
        )

    async def close(self) -> None:
        if self.process is not None:
            await self.process.terminate(timeout=self.config.step_timeout)

    def _snapshot(self, state: dict[str, object]) -> HiddenStateSnapshot:
        world = world_from_state(state, player_id=self.mission.player_id)
        return HiddenStateSnapshot(tick=world.tick, world=world)


class ZeroADBackend(Backend):
    game = "zeroad"

    def __init__(self, config: WarGamesConfig) -> None:
        if not isinstance(config, ZeroADConfig):
            config = ZeroADConfig(**config.__dict__)
        super().__init__(config)
        self.config: ZeroADConfig = config
        self._sessions: list[ZeroADSession] = []
        self._missions = self._discover_missions()
        self._bootstrapped = False

    def _discover_missions(self) -> tuple[ZeroADMissionSpec, ...]:
        catalog = load_mission_catalog(self.config.missions_dir)
        if catalog:
            return catalog
        if self.config.root:
            discovered = discover(self.config.root)
            if discovered:
                return discovered
        return fallback_missions()

    def missions(self) -> tuple[MissionSpec, ...]:
        return self._missions

    def export_missions(self, output_dir: str | Path) -> tuple[Path, ...]:
        root = self.config.root or "/usr/share/games/0ad"
        written = extract_mission_catalog(root, output_dir)
        if not written:
            raise GameNotInstalled(f"0 A.D. maps were not found under {root}")
        return written

    def supports(self, mission: MissionSpec) -> bool:
        return isinstance(mission, ZeroADMissionSpec) and mission.game == self.game

    async def bootstrap(self) -> None:
        if self._bootstrapped:
            return
        if sys.platform != "linux":
            raise GameNotInstalled(
                "WarGames 0 A.D. runs only inside its Linux/Xvfb Docker runtime"
            )
        bootstrap_zeroad(self.config)
        self._bootstrapped = True

    async def start(self, mission: MissionSpec, *, seed: int) -> BackendSession:
        if not self.supports(mission):
            raise ValueError(f"unsupported 0 A.D. mission: {mission.id}")
        await self.bootstrap()
        spec = mission  # type: ignore[assignment]
        width, height = self.config.window_size
        binary = locate_zeroad(self.config)
        display = os.getenv("DISPLAY", ":99")
        env = zeroad_environment(self.config, display=display)
        prepare_zeroad_runtime_environment(env)
        command = zeroad_command(
            binary,
            self.config,
            rl_host=self.config.rl_host,
            rl_port=self.config.rl_port,
        )
        process = await ProcessLauncher().start(
            command,
            env=env,
            cwd=zeroad_working_dir(binary, self.config),
            timeout=self.config.step_timeout,
            id=spec.id,
        )
        client = ZeroADRLClient(
            host=self.config.rl_host,
            port=self.config.rl_port,
            timeout=self.config.step_timeout,
        )
        await client.wait_ready(self.config.step_timeout)
        initial_state = await client.reset(
            spec.scenario_config(seed=seed),
            player_id=spec.player_id,
        )
        target = await wait_for_window(
            pid=process.pid,
            display=env.get("DISPLAY"),
            width=width,
            height=height,
            timeout=self.config.step_timeout,
            title="0 A.D.",
        )
        await focus_window(target)
        await _wait_for_visible_frame(target, timeout=self.config.step_timeout)
        session = ZeroADSession(
            id=f"{spec.id}:{seed}:{uuid.uuid4().hex[:8]}",
            mission=spec,
            seed=seed,
            target=target,
            injector=self._injector_for(target),
            client=client,
            process=process,
            config=self.config,
            initial_state=initial_state,
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


async def _wait_for_visible_frame(target: Target, *, timeout: float) -> None:
    import_tool = shutil.which("import")
    identify = shutil.which("identify")
    if import_tool is None or identify is None:
        await asyncio.sleep(1)
        return

    path = Path("/tmp/wargames/zeroad-ready.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if target.display:
        env["DISPLAY"] = target.display
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        capture = await asyncio.create_subprocess_exec(
            import_tool,
            "-window",
            "root",
            str(path),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if await capture.wait() == 0 and _has_visible_pixels(path, identify):
            return
        if asyncio.get_running_loop().time() >= deadline:
            return
        await asyncio.sleep(1)


def _has_visible_pixels(path: Path, identify: str) -> bool:
    if not path.exists() or path.stat().st_size <= 1024:
        return False
    result = subprocess.run(
        [identify, "-format", "%[mean]", str(path)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode != 0:
        return False
    try:
        return float(result.stdout.strip()) > 1.0
    except ValueError:
        return False
