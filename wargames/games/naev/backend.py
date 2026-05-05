from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from wargames.core.backend.base import Backend, BackendSession
from wargames.core.capture.audio import FileAudioCapture
from wargames.core.capture.window import NullWindowCapture, ScreenRegionCapture
from wargames.core.config import WarGamesConfig
from wargames.core.control.cua import ArenaAction
from wargames.core.control.events import KeyEvent, MouseEvent, Target
from wargames.core.control.injector import InputInjector, XTestInjector, XdotoolInjector
from wargames.core.control.lower import lower_cua
from wargames.core.errors import GameNotInstalled, ProbeError
from wargames.core.missions.spec import MissionSpec
from wargames.core.process.launcher import ProcessHandle, ProcessLauncher
from wargames.core.runtime.observation import Observation
from wargames.core.runtime.result import MissionSummary, StepResult
from wargames.core.world.probe import HiddenStateSnapshot
from wargames.games.naev.config import NaevConfig
from wargames.games.naev.missions import (
    NaevMissionSpec,
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)
from wargames.games.naev.probe import StdoutStateProbe
from wargames.games.naev.process import (
    bootstrap_naev,
    install_state_exporter,
    locate_naev,
    naev_command,
    naev_environment,
    prepare_data_dir,
)
from wargames.games.naev.world import world_from_frame
from wargames.games.redalert.window import focus_window, wait_for_window


class NaevSession(BackendSession):
    def __init__(
        self,
        *,
        id: str,
        mission: NaevMissionSpec,
        seed: int,
        target: Target,
        injector: InputInjector,
        probe: StdoutStateProbe,
        audio_capture: FileAudioCapture,
        process: ProcessHandle,
        config: NaevConfig,
    ) -> None:
        self.id = id
        self.mission = mission
        self.seed = seed
        self.target = target
        self.injector = injector
        self.probe = probe
        self.audio_capture = audio_capture
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
        observation = await self.observe()
        return StepResult(
            action=action,
            tick=hidden.tick,
            frame=observation.frame,
            finished=finished,
            truncated=truncated,
            hidden=hidden,
            prev_hidden=prev,
            info={},
            end_reason="objective_complete" if finished else "defeat" if failed else None,
            audio=observation.audio,
        )

    async def observe(self) -> Observation:
        latest = await self.probe.latest()
        tick = latest.tick if latest else self._last_hidden.tick
        frame = (
            await self.capture.capture(self.target, tick=tick)
            if self.config.capture_frames
            else None
        )
        return Observation(frame=frame, audio=await self.audio_capture.capture(tick=tick))

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
        await self.process.terminate(timeout=5.0)

    def _snapshot(self, *, finished: bool, failed: bool) -> HiddenStateSnapshot:
        world = world_from_frame(
            {
                "tick": self._tick,
                "mission": {
                    "name": self.mission.mission_name,
                    "finished": finished,
                    "failed": failed,
                    "completed_count": 1 if finished else 0,
                    "failed_count": 1 if failed else 0,
                },
                "player": {
                    "system": "Hakoi",
                    "landed": False,
                    "credits": 30_000,
                    "wealth": 30_000,
                    "jumps": 0,
                },
                "navigation": {"system": "Hakoi", "landed": False, "jumps_available": 0},
            }
        )
        return HiddenStateSnapshot(tick=self._tick, world=world)

    async def _probe_snapshot_after(self, tick: int) -> HiddenStateSnapshot:
        try:
            return await asyncio.wait_for(self.probe.next_after(tick), timeout=1.0)
        except TimeoutError:
            latest = await self.probe.latest()
            if latest is None:
                raise ProbeError("Naev state probe has not produced a world snapshot")
            return latest


class NaevBackend(Backend):
    game = "naev"

    def __init__(self, config: WarGamesConfig) -> None:
        if not isinstance(config, NaevConfig):
            config = NaevConfig(**config.__dict__)
        super().__init__(config)
        self.config: NaevConfig = config
        self._sessions: list[NaevSession] = []
        self._missions = self._discover_missions()
        self._bootstrapped = False

    def _discover_missions(self) -> tuple[NaevMissionSpec, ...]:
        catalog = load_mission_catalog(self.config.missions_dir)
        if catalog:
            return catalog
        return discover(self.config.data_dir or self.config.root)

    def missions(self) -> tuple[MissionSpec, ...]:
        return self._missions

    def export_missions(self, output_dir: str | Path) -> tuple[Path, ...]:
        written = extract_mission_catalog(self.config.data_dir or self.config.root, output_dir)
        if not written:
            raise GameNotInstalled("Naev missions were not found in the Naev runtime")
        return written

    def supports(self, mission: MissionSpec) -> bool:
        return isinstance(mission, NaevMissionSpec) and mission.game == self.game

    async def bootstrap(self) -> None:
        if self._bootstrapped:
            return
        if sys.platform != "linux":
            raise GameNotInstalled("WarGames Naev runs only inside its Linux/Xvfb Docker runtime")
        bootstrap_naev(self.config)
        self._bootstrapped = True

    async def start(self, mission: MissionSpec, *, seed: int) -> BackendSession:
        if not self.supports(mission):
            raise ValueError(f"unsupported Naev mission: {mission.id}")
        await self.bootstrap()
        spec = mission  # type: ignore[assignment]
        width, height = self.config.window_size
        data_dir = prepare_data_dir(self.config, spec)
        install_state_exporter(data_dir, spec)
        binary = locate_naev(self.config)
        display = os.getenv("DISPLAY", ":99")
        audio_path = str(Path(self.config.probe_dir) / f"naev-{uuid.uuid4().hex}.pcm")
        audio_capture = FileAudioCapture(audio_path, max_chunk_bytes=384_000)
        audio_capture.reset()
        env = naev_environment(self.config, display=display, audio_path=audio_path)
        process = await ProcessLauncher().start(
            naev_command(binary, data_dir, self.config),
            env=env,
            timeout=self.config.step_timeout,
            id=spec.id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        if process.process.stdout is None:
            raise ProbeError("Naev stdout state probe could not attach to the process")
        probe = StdoutStateProbe(process.process.stdout)
        await probe.start()
        target = await wait_for_window(
            pid=process.pid,
            display=env.get("DISPLAY"),
            width=width,
            height=height,
            timeout=self.config.step_timeout,
            title="Naev",
        )
        await focus_window(target)
        injector = self._injector_for(target)
        await _wait_for_visible_frame(target, timeout=self.config.step_timeout)
        await _wait_for_main_menu(probe, timeout=self.config.step_timeout)
        await _drive_startup_menu(target, injector, probe, timeout=self.config.step_timeout)
        await _wait_for_probe(probe, timeout=self.config.step_timeout)
        target = await wait_for_window(
            pid=process.pid,
            display=env.get("DISPLAY"),
            width=width,
            height=height,
            timeout=self.config.step_timeout,
            title="Naev",
        )
        await focus_window(target)
        session = NaevSession(
            id=f"{spec.id}:{seed}:{uuid.uuid4().hex[:8]}",
            mission=spec,
            seed=seed,
            target=target,
            injector=injector,
            probe=probe,
            audio_capture=audio_capture,
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


async def _drive_startup_menu(
    target: Target,
    injector: InputInjector,
    probe: StdoutStateProbe,
    *,
    timeout: float,
) -> None:
    input_target = Target(
        pid=target.pid,
        window_id=None,
        rect=target.rect,
        display=target.display,
    )
    await asyncio.sleep(0.5)
    await _tap_key(input_target, injector, "Enter")
    await asyncio.sleep(0.5)
    await _click(input_target, injector, 0.500, 0.605)
    await asyncio.sleep(0.5)
    await _click(input_target, injector, 0.500, 0.563)
    await asyncio.sleep(0.8)
    await _click(input_target, injector, 0.500, 0.497)
    for key in "wargames":
        await _tap_key(input_target, injector, key, ms=35)
    await asyncio.sleep(0.2)
    await _click(input_target, injector, 0.545, 0.542)
    await asyncio.sleep(0.8)
    await _click(input_target, injector, 0.500, 0.537)

    deadline = asyncio.get_running_loop().time() + timeout
    while await probe.latest() is None and asyncio.get_running_loop().time() < deadline:
        await _tap_key(input_target, injector, "Escape", ms=50)
        await asyncio.sleep(0.2)
        await _tap_key(input_target, injector, "Enter", ms=50)
        await asyncio.sleep(0.2)
        await _tap_key(input_target, injector, "Space", ms=50)
        await asyncio.sleep(0.4)


async def _tap_key(
    target: Target, injector: InputInjector, key: str, *, ms: int = 75
) -> None:
    await injector.send(target, KeyEvent(kind="down", key=key))
    await asyncio.sleep(ms / 1000)
    await injector.send(target, KeyEvent(kind="up", key=key))


async def _click(
    target: Target,
    injector: InputInjector,
    x_fraction: float,
    y_fraction: float,
) -> None:
    x = target.rect.x + int(target.rect.width * x_fraction)
    y = target.rect.y + int(target.rect.height * y_fraction)
    await injector.send(target, MouseEvent(kind="move", x=x, y=y))
    await asyncio.sleep(0.05)
    await injector.send(target, MouseEvent(kind="down", button="left"))
    await asyncio.sleep(0.05)
    await injector.send(target, MouseEvent(kind="up", button="left"))


async def _wait_for_probe(probe: StdoutStateProbe, *, timeout: float) -> None:
    try:
        await asyncio.wait_for(probe.next(), timeout=timeout)
    except TimeoutError as exc:
        tail = "\n".join(probe.log_tail()[-20:])
        detail = f":\n{tail}" if tail else ""
        raise ProbeError(f"Naev state probe did not produce a snapshot{detail}") from exc


async def _wait_for_main_menu(probe: StdoutStateProbe, *, timeout: float) -> None:
    try:
        await asyncio.wait_for(probe.wait_for_log("Reached main menu"), timeout=timeout)
    except TimeoutError as exc:
        tail = "\n".join(probe.log_tail()[-20:])
        detail = f":\n{tail}" if tail else ""
        raise ProbeError(f"Naev did not reach the main menu{detail}") from exc


async def _wait_for_visible_frame(target: Target, *, timeout: float) -> None:
    import_tool = shutil.which("import")
    identify = shutil.which("identify")
    if import_tool is None or identify is None:
        await asyncio.sleep(1)
        return

    path = Path("/tmp/wargames/naev-ready.png")
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
