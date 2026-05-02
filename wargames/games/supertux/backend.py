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
from wargames.core.errors import GameNotInstalled, ProbeError, ProbeNotInstalled
from wargames.core.missions.spec import MissionSpec
from wargames.core.process.launcher import ProcessHandle, ProcessLauncher
from wargames.core.runtime.observation import Observation
from wargames.core.runtime.result import MissionSummary, StepResult
from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.redalert.window import focus_window, wait_for_window
from wargames.games.supertux.config import SuperTuxConfig
from wargames.games.supertux.missions import (
    SuperTuxMissionSpec,
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)
from wargames.games.supertux.probe import JsonlStateProbe
from wargames.games.supertux.process import (
    bootstrap_supertux,
    locate_supertux,
    supertux_command,
    supertux_environment,
)
from wargames.games.supertux.world import world_from_frame


class SuperTuxSession(BackendSession):
    def __init__(
        self,
        *,
        id: str,
        mission: SuperTuxMissionSpec,
        seed: int,
        target: Target,
        injector: InputInjector,
        probe: JsonlStateProbe,
        process: ProcessHandle,
        config: SuperTuxConfig,
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
        latest = await self.probe.latest()
        tick = latest.tick if latest else self._last_hidden.tick
        frame = (
            await self.capture.capture(self.target, tick=tick)
            if self.config.capture_frames
            else None
        )
        return Observation(frame=frame)

    async def center_pointer(self) -> None:
        x = self.target.rect.x + self.target.rect.width // 2
        y = self.target.rect.y + self.target.rect.height // 2
        await self.injector.send(self.target, MouseEvent(kind="move", x=x, y=y))

    async def summary(self) -> MissionSummary:
        latest = await self.probe.latest()
        tick = self._last_hidden.tick
        finished = False
        failed = self.process.process.returncode not in {None, 0}
        if latest is not None:
            tick = latest.tick
            finished = bool(getattr(latest.world.mission, "finished", False))
            failed = failed or bool(getattr(latest.world.mission, "failed", False))
        truncated = tick >= self.mission.time_limit_ticks and not finished
        return MissionSummary(
            id=self.id,
            mission=self.mission,
            seed=self.seed,
            finished=finished,
            truncated=truncated,
            duration_ticks=tick,
            end_reason="objective_complete" if finished else "defeat" if failed else None,
        )

    async def close(self) -> None:
        await self.probe.close()
        await self.process.terminate(timeout=self.config.step_timeout)

    def _snapshot(self, *, finished: bool, failed: bool) -> HiddenStateSnapshot:
        world = world_from_frame(
            {
                "tick": self._tick,
                "mission": {"finished": finished, "failed": failed},
                "level": {
                    "file": self.mission.level_file,
                    "name": self.mission.title,
                    "set": self.mission.level_set,
                    "elapsed_ticks": self._tick,
                    "coins": 0,
                    "total_coins": 0,
                    "secrets": 0,
                    "total_secrets": 0,
                    "target_time_seconds": self.mission.target_time_seconds,
                },
                "player": {
                    "x": None,
                    "y": None,
                    "vx": None,
                    "vy": None,
                    "coins": 0,
                    "bonus": "none",
                    "alive": True,
                    "dead": False,
                    "winning": False,
                },
            }
        )
        return HiddenStateSnapshot(tick=self._tick, world=world)

    async def _probe_snapshot_after(self, tick: int) -> HiddenStateSnapshot:
        try:
            return await asyncio.wait_for(self.probe.next_after(tick), timeout=0.5)
        except TimeoutError:
            latest = await self.probe.latest()
            if latest is None:
                raise ProbeError("SuperTux state probe has not produced a world snapshot")
            return latest


class SuperTuxBackend(Backend):
    game = "supertux"

    def __init__(self, config: WarGamesConfig) -> None:
        if not isinstance(config, SuperTuxConfig):
            config = SuperTuxConfig(**config.__dict__)
        super().__init__(config)
        self.config: SuperTuxConfig = config
        self._sessions: list[SuperTuxSession] = []
        self._missions = self._discover_missions()
        self._bootstrapped = False

    def _discover_missions(self) -> tuple[SuperTuxMissionSpec, ...]:
        catalog = load_mission_catalog(self.config.missions_dir)
        if catalog:
            return catalog
        return discover(self.config.data_dir or self.config.root)

    def missions(self) -> tuple[MissionSpec, ...]:
        return self._missions

    def export_missions(self, output_dir: str | Path) -> tuple[Path, ...]:
        written = extract_mission_catalog(self.config.data_dir or self.config.root, output_dir)
        if not written:
            raise GameNotInstalled("SuperTux levels were not found in the SuperTux runtime")
        return written

    def supports(self, mission: MissionSpec) -> bool:
        return isinstance(mission, SuperTuxMissionSpec) and mission.game == self.game

    async def bootstrap(self) -> None:
        if self._bootstrapped:
            return
        if sys.platform != "linux":
            raise GameNotInstalled("WarGames SuperTux runs only inside its Linux/Xvfb Docker runtime")
        bootstrap_supertux(self.config)
        self._bootstrapped = True

    async def start(self, mission: MissionSpec, *, seed: int) -> BackendSession:
        if not self.supports(mission):
            raise ValueError(f"unsupported SuperTux mission: {mission.id}")
        await self.bootstrap()
        spec = mission  # type: ignore[assignment]
        width, height = self.config.window_size
        binary = locate_supertux(self.config)
        verify_state_probe_installed(binary)
        display = os.getenv("DISPLAY", ":99")
        state_path = str(Path(self.config.probe_dir) / f"supertux-{uuid.uuid4().hex}.jsonl")
        probe = JsonlStateProbe(state_path)
        await probe.start()
        env = supertux_environment(self.config, display=display, state_path=state_path)
        process = await ProcessLauncher().start(
            supertux_command(binary, spec, self.config, seed=seed),
            env=env,
            timeout=self.config.step_timeout,
            id=spec.id,
        )
        target = await wait_for_window(
            pid=process.pid,
            display=env.get("DISPLAY"),
            width=width,
            height=height,
            timeout=self.config.step_timeout,
            title="SuperTux",
        )
        await focus_window(target)
        await _wait_for_visible_frame(target, timeout=self.config.step_timeout)
        await _wait_for_probe(probe, timeout=self.config.step_timeout)
        session = SuperTuxSession(
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


def verify_state_probe_installed(binary: str) -> None:
    try:
        strings = subprocess.run(
            ["strings", binary],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        strings = None
    if strings is not None and "WARGAMES_SUPERTUX_STATE_PATH" in strings.stdout:
        return
    raise ProbeNotInstalled(
        "SuperTux must be built with the WarGames state exporter. "
        "Run `wargames install --game supertux` inside the WarGames runtime."
    )


async def _wait_for_probe(probe: JsonlStateProbe, *, timeout: float) -> None:
    try:
        await asyncio.wait_for(probe.next(), timeout=timeout)
    except TimeoutError as exc:
        raise ProbeError("SuperTux state probe did not produce a snapshot") from exc


async def _wait_for_visible_frame(target: Target, *, timeout: float) -> None:
    import_tool = shutil.which("import")
    identify = shutil.which("identify")
    if import_tool is None or identify is None:
        await asyncio.sleep(1)
        return

    path = Path("/tmp/wargames/supertux-ready.png")
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
