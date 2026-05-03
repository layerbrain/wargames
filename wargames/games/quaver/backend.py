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
from wargames.games.quaver.config import QuaverConfig
from wargames.games.quaver.missions import (
    QuaverMissionSpec,
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)
from wargames.games.quaver.probe import JsonlStateProbe
from wargames.games.quaver.process import (
    bootstrap_quaver,
    locate_default_maps_dir,
    locate_quaver,
    locate_runtime_root,
    quaver_command,
    quaver_environment,
)
from wargames.games.quaver.world import world_from_frame
from wargames.games.redalert.window import focus_window, wait_for_window


class QuaverSession(BackendSession):
    def __init__(
        self,
        *,
        id: str,
        mission: QuaverMissionSpec,
        seed: int,
        target: Target,
        injector: InputInjector,
        probe: JsonlStateProbe,
        audio_capture: FileAudioCapture,
        process: ProcessHandle,
        config: QuaverConfig,
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
                "chart": {
                    "map_id": self.mission.map_id,
                    "mapset_id": self.mission.mapset_id,
                    "title": self.mission.song_title,
                    "artist": self.mission.artist,
                    "difficulty_name": self.mission.difficulty_name,
                    "mode": self.mission.mode,
                    "key_count": self.mission.key_count,
                    "song_length_ms": self.mission.song_length_ms,
                    "hit_objects": self.mission.hit_objects,
                    "long_notes": self.mission.long_notes,
                    "mines": self.mission.mines,
                    "total_judgements": self.mission.total_judgements,
                },
                "gameplay": {
                    "song_time_ms": 0.0,
                    "started": False,
                    "paused": False,
                    "completed": False,
                    "failed": failed,
                    "health": 100.0,
                    "score": 0,
                    "accuracy": 0.0,
                    "combo": 0,
                    "max_combo": 0,
                    "total_judgement_count": 0,
                    "stats_count": 0,
                },
                "judgements": {},
            }
        )
        return HiddenStateSnapshot(tick=self._tick, world=world)

    async def _probe_snapshot_after(self, tick: int) -> HiddenStateSnapshot:
        try:
            return await asyncio.wait_for(self.probe.next_after(tick), timeout=0.5)
        except TimeoutError:
            latest = await self.probe.latest()
            if latest is None:
                raise ProbeError("Quaver state probe has not produced a world snapshot")
            return latest


class QuaverBackend(Backend):
    game = "quaver"

    def __init__(self, config: WarGamesConfig) -> None:
        if not isinstance(config, QuaverConfig):
            config = QuaverConfig(**config.__dict__)
        super().__init__(config)
        self.config: QuaverConfig = config
        self._sessions: list[QuaverSession] = []
        self._missions = self._discover_missions()
        self._bootstrapped = False

    def _discover_missions(self) -> tuple[QuaverMissionSpec, ...]:
        catalog = load_mission_catalog(self.config.missions_dir)
        if catalog:
            return catalog
        return discover(
            self.config.root,
            default_maps_dir=self.config.default_maps_dir,
            songs_dir=self.config.songs_dir,
        )

    def missions(self) -> tuple[MissionSpec, ...]:
        return self._missions

    def export_missions(self, output_dir: str | Path) -> tuple[Path, ...]:
        written = extract_mission_catalog(
            self.config.root,
            output_dir,
            default_maps_dir=self.config.default_maps_dir,
            songs_dir=self.config.songs_dir,
        )
        if not written:
            raise GameNotInstalled("Quaver default chart archives were not found in the Quaver runtime")
        return written

    def supports(self, mission: MissionSpec) -> bool:
        return isinstance(mission, QuaverMissionSpec) and mission.game == self.game

    async def bootstrap(self) -> None:
        if self._bootstrapped:
            return
        if sys.platform != "linux":
            raise GameNotInstalled("WarGames Quaver runs only inside its Linux/Xvfb Docker runtime")
        bootstrap_quaver(self.config)
        locate_default_maps_dir(self.config)
        self._bootstrapped = True

    async def start(self, mission: MissionSpec, *, seed: int) -> BackendSession:
        if not self.supports(mission):
            raise ValueError(f"unsupported Quaver mission: {mission.id}")
        await self.bootstrap()
        spec = mission  # type: ignore[assignment]
        width, height = self.config.window_size
        binary = locate_quaver(self.config)
        runtime_root = locate_runtime_root(self.config)
        verify_state_probe_installed(runtime_root)
        display = os.getenv("DISPLAY", ":99")
        state_path = str(Path(self.config.probe_dir) / f"quaver-{uuid.uuid4().hex}.jsonl")
        audio_path = str(Path(self.config.probe_dir) / f"quaver-{uuid.uuid4().hex}.pcm")
        audio_capture = FileAudioCapture(audio_path, max_chunk_bytes=384_000)
        audio_capture.reset()
        probe = JsonlStateProbe(state_path)
        await probe.start()
        env = quaver_environment(
            self.config, spec, display=display, state_path=state_path, audio_path=audio_path
        )
        process = await ProcessLauncher().start(
            quaver_command(binary, spec, self.config),
            env=env,
            cwd=str(runtime_root),
            timeout=self.config.step_timeout,
            id=spec.id,
        )
        target = await wait_for_window(
            pid=process.pid,
            display=env.get("DISPLAY"),
            width=width,
            height=height,
            timeout=self.config.step_timeout,
            title="Quaver",
        )
        await focus_window(target)
        await _wait_for_visible_frame(target, timeout=self.config.step_timeout)
        await _wait_for_probe(probe, timeout=self.config.step_timeout)
        session = QuaverSession(
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


def verify_state_probe_installed(runtime_root: Path) -> None:
    dll = runtime_root / "Quaver.Shared.dll"
    marker = "WARGAMES_QUAVER_STATE_PATH"
    try:
        data = dll.read_bytes()
    except OSError:
        data = b""
    if marker.encode() in data or marker.encode("utf-16-le") in data:
        return
    raise ProbeNotInstalled(
        "Quaver must be built with the WarGames state exporter. "
        "Run `wargames install --game quaver` inside the WarGames runtime."
    )


async def _wait_for_probe(probe: JsonlStateProbe, *, timeout: float) -> None:
    try:
        await asyncio.wait_for(probe.next(), timeout=timeout)
    except TimeoutError as exc:
        raise ProbeError("Quaver state probe did not produce a snapshot") from exc


async def _wait_for_visible_frame(target: Target, *, timeout: float) -> None:
    import_tool = shutil.which("import")
    identify = shutil.which("identify")
    if import_tool is None or identify is None:
        await asyncio.sleep(1)
        return

    path = Path("/tmp/wargames/quaver-ready.png")
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
