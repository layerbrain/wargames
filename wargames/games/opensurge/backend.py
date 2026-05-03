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
from wargames.games.opensurge.config import OpenSurgeConfig
from wargames.games.opensurge.missions import (
    OpenSurgeMissionSpec,
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)
from wargames.games.opensurge.probe import JsonlStateProbe
from wargames.games.opensurge.process import (
    bootstrap_opensurge,
    locate_opensurge,
    opensurge_command,
    opensurge_environment,
)
from wargames.games.opensurge.world import world_from_frame


class OpenSurgeSession(BackendSession):
    def __init__(
        self,
        *,
        id: str,
        mission: OpenSurgeMissionSpec,
        seed: int,
        target: Target,
        injector: InputInjector,
        probe: JsonlStateProbe,
        audio_capture: FileAudioCapture,
        process: ProcessHandle,
        config: OpenSurgeConfig,
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
        await self.process.terminate(timeout=self.config.step_timeout)

    def _snapshot(self, *, finished: bool, failed: bool) -> HiddenStateSnapshot:
        world = world_from_frame(
            {
                "tick": self._tick,
                "mission": {"finished": finished, "failed": failed},
                "level": {
                    "file": self.mission.level_file,
                    "name": self.mission.title,
                    "act": self.mission.act,
                    "elapsed_ticks": self._tick,
                    "elapsed_seconds": 0.0,
                    "width": 0.0,
                    "height": 0.0,
                    "target_time_seconds": self.mission.target_time_seconds,
                },
                "player": {
                    "x": None,
                    "y": None,
                    "xsp": None,
                    "ysp": None,
                    "gsp": None,
                    "speed": None,
                    "rings": 0,
                    "score": 0,
                    "lives": 0,
                    "alive": True,
                    "dying": False,
                    "winning": False,
                    "rolling": False,
                    "jumping": False,
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
                raise ProbeError("OpenSurge state probe has not produced a world snapshot")
            return latest


class OpenSurgeBackend(Backend):
    game = "opensurge"

    def __init__(self, config: WarGamesConfig) -> None:
        if not isinstance(config, OpenSurgeConfig):
            config = OpenSurgeConfig(**config.__dict__)
        super().__init__(config)
        self.config: OpenSurgeConfig = config
        self._sessions: list[OpenSurgeSession] = []
        self._missions = self._discover_missions()
        self._bootstrapped = False

    def _discover_missions(self) -> tuple[OpenSurgeMissionSpec, ...]:
        catalog = load_mission_catalog(self.config.missions_dir)
        if catalog:
            return catalog
        return discover(self.config.data_dir or self.config.root)

    def missions(self) -> tuple[MissionSpec, ...]:
        return self._missions

    def export_missions(self, output_dir: str | Path) -> tuple[Path, ...]:
        written = extract_mission_catalog(self.config.data_dir or self.config.root, output_dir)
        if not written:
            raise GameNotInstalled("Open Surge levels were not found in the Open Surge runtime")
        return written

    def supports(self, mission: MissionSpec) -> bool:
        return isinstance(mission, OpenSurgeMissionSpec) and mission.game == self.game

    async def bootstrap(self) -> None:
        if self._bootstrapped:
            return
        if sys.platform != "linux":
            raise GameNotInstalled("WarGames Open Surge runs only inside its Linux/Xvfb Docker runtime")
        bootstrap_opensurge(self.config)
        self._bootstrapped = True

    async def start(self, mission: MissionSpec, *, seed: int) -> BackendSession:
        if not self.supports(mission):
            raise ValueError(f"unsupported Open Surge mission: {mission.id}")
        await self.bootstrap()
        spec = mission  # type: ignore[assignment]
        width, height = self.config.window_size
        binary = locate_opensurge(self.config)
        verify_state_probe_installed(binary)
        display = os.getenv("DISPLAY", ":99")
        state_path = str(Path(self.config.probe_dir) / f"opensurge-{uuid.uuid4().hex}.jsonl")
        audio_path = str(Path(self.config.probe_dir) / f"opensurge-{uuid.uuid4().hex}.pcm")
        audio_capture = FileAudioCapture(audio_path, max_chunk_bytes=384_000)
        audio_capture.reset()
        probe = JsonlStateProbe(state_path)
        await probe.start()
        env = opensurge_environment(
            self.config, display=display, state_path=state_path, audio_path=audio_path
        )
        process = await ProcessLauncher().start(
            opensurge_command(binary, spec, self.config, seed=seed),
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
            title="Open Surge",
        )
        await focus_window(target)
        await _wait_for_visible_frame(target, timeout=self.config.step_timeout)
        await _wait_for_probe(probe, timeout=self.config.step_timeout)
        session = OpenSurgeSession(
            id=f"{spec.id}:{seed}:{uuid.uuid4().hex[:8]}",
            mission=spec,
            seed=seed,
            target=target,
            injector=self._injector_for(target),
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
    if strings is not None and "WARGAMES_OPENSURGE_STATE_PATH" in strings.stdout:
        return
    raise ProbeNotInstalled(
        "Open Surge must be built with the WarGames state exporter. "
        "Run `wargames install --game opensurge` inside the WarGames runtime."
    )


async def _wait_for_probe(probe: JsonlStateProbe, *, timeout: float) -> None:
    try:
        await asyncio.wait_for(probe.next(), timeout=timeout)
    except TimeoutError as exc:
        raise ProbeError("Open Surge state probe did not produce a snapshot") from exc


async def _wait_for_visible_frame(target: Target, *, timeout: float) -> None:
    import_tool = shutil.which("import")
    identify = shutil.which("identify")
    if import_tool is None or identify is None:
        await asyncio.sleep(1)
        return

    path = Path("/tmp/wargames/opensurge-ready.png")
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
