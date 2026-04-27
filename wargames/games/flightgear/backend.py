from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

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
from wargames.games.flightgear.config import FlightGearConfig
from wargames.games.flightgear.missions import (
    FlightGearMissionSpec,
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)
from wargames.games.flightgear.process import (
    bootstrap_flightgear,
    flightgear_command,
    flightgear_environment,
    is_flightgear_ready,
    locate_fgfs,
    read_flightgear_property,
)
from wargames.games.redalert.window import focus_window, wait_for_window


class FlightGearSession(BackendSession):
    def __init__(
        self,
        *,
        id: str,
        mission: FlightGearMissionSpec,
        seed: int,
        target: Target,
        injector: InputInjector,
        process: ProcessHandle | None,
        config: FlightGearConfig,
    ) -> None:
        self.id = id
        self.mission = mission
        self.seed = seed
        self.target = target
        self.injector = injector
        self.process = process
        self.config = config
        self.capture = (
            ScreenRegionCapture(config.frame_dir) if config.capture_frames else NullWindowCapture()
        )
        self._tick = 0
        self._last_hidden = self._snapshot(finished=False, failed=False)

    async def step(self, action: ArenaAction) -> StepResult:
        prev = self._last_hidden
        await self.injector.send_many(self.target, lower_cua(action, self.target.rect))
        self._tick += 1
        finished = self.process is not None and self.process.process.returncode == 0
        failed = self.process is not None and self.process.process.returncode not in {None, 0}
        hidden = self._snapshot(finished=finished, failed=failed)
        failed = bool(getattr(hidden.world.mission, "failed", failed))
        self._last_hidden = hidden
        truncated = self._tick >= self.mission.time_limit_ticks and not finished
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
            await self.capture.capture(self.target, tick=self._tick)
            if self.config.capture_frames
            else None
        )
        return Observation(frame=frame)

    async def center_pointer(self) -> None:
        x = self.target.rect.x + self.target.rect.width // 2
        y = self.target.rect.y + self.target.rect.height // 2
        await self.injector.send(self.target, MouseEvent(kind="move", x=x, y=y))

    async def summary(self) -> MissionSummary:
        finished = self.process is not None and self.process.process.returncode == 0
        failed = self.process is not None and self.process.process.returncode not in {None, 0}
        truncated = self._tick >= self.mission.time_limit_ticks and not finished
        return MissionSummary(
            id=self.id,
            mission=self.mission,
            seed=self.seed,
            finished=finished,
            truncated=truncated,
            duration_ticks=self._tick,
            end_reason="objective_complete" if finished else "defeat" if failed else None,
        )

    async def close(self) -> None:
        if self.process is not None:
            await self.process.terminate(timeout=self.config.step_timeout)

    def _snapshot(self, *, finished: bool, failed: bool) -> HiddenStateSnapshot:
        telemetry = _read_telemetry(self.config)
        world = SimpleNamespace(
            mission=SimpleNamespace(
                finished=finished, failed=failed or telemetry["crashed"] is True
            ),
            aircraft=SimpleNamespace(
                id=self.mission.aircraft,
                airport=self.mission.airport,
                runway=self.mission.runway,
                altitude_ft=telemetry["altitude_ft"],
                airspeed_kt=telemetry["airspeed_kt"],
                pitch_deg=telemetry["pitch_deg"],
                roll_deg=telemetry["roll_deg"],
                heading_deg=telemetry["heading_deg"],
                vertical_speed_fps=telemetry["vertical_speed_fps"],
                throttle=telemetry["throttle"],
                crashed=telemetry["crashed"],
            ),
        )
        return HiddenStateSnapshot(tick=self._tick, world=world)


class FlightGearBackend(Backend):
    game = "flightgear"

    def __init__(self, config: WarGamesConfig) -> None:
        if not isinstance(config, FlightGearConfig):
            config = FlightGearConfig(**config.__dict__)
        super().__init__(config)
        self.config: FlightGearConfig = config
        self._sessions: list[FlightGearSession] = []
        self._missions = self._discover_missions()
        self._bootstrapped = False

    def _discover_missions(self) -> tuple[FlightGearMissionSpec, ...]:
        catalog = load_mission_catalog(self.config.missions_dir)
        if catalog:
            return catalog
        root = self.config.fgfs_root or os.getenv("FG_ROOT") or "/usr/share/games/flightgear"
        return discover(root)

    def missions(self) -> tuple[MissionSpec, ...]:
        return self._missions

    def export_missions(self, output_dir: str | Path) -> tuple[Path, ...]:
        root = self.config.fgfs_root or os.getenv("FG_ROOT") or "/usr/share/games/flightgear"
        written = extract_mission_catalog(root, output_dir)
        if not written:
            raise GameNotInstalled(f"FlightGear tutorial catalog was not found under {root}")
        return written

    def supports(self, mission: MissionSpec) -> bool:
        return isinstance(mission, FlightGearMissionSpec) and mission.game == self.game

    async def bootstrap(self) -> None:
        if self._bootstrapped:
            return
        if sys.platform != "linux":
            raise GameNotInstalled(
                "WarGames FlightGear runs only inside the Linux/Xvfb runtime box"
            )
        bootstrap_flightgear(self.config)
        self._bootstrapped = True

    async def start(self, mission: MissionSpec, *, seed: int) -> BackendSession:
        if not self.supports(mission):
            raise ValueError(f"unsupported FlightGear mission: {mission.id}")
        await self.bootstrap()
        spec = mission  # type: ignore[assignment]
        width, height = self.config.window_size
        binary = locate_fgfs(self.config)
        command = flightgear_command(binary, spec, self.config)
        display = os.getenv("DISPLAY", ":99")
        env = flightgear_environment(self.config, display=display)
        process = await ProcessLauncher().start(
            command,
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
            title="FlightGear",
        )
        await focus_window(target)
        await _wait_for_simulator_ready(self.config, timeout=self.config.step_timeout)
        await _wait_for_visible_frame(target, timeout=self.config.step_timeout)
        injector = self._injector_for(target)
        session = FlightGearSession(
            id=f"{spec.id}:{seed}:{uuid.uuid4().hex[:8]}",
            mission=spec,
            seed=seed,
            target=target,
            injector=injector,
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


async def _wait_for_visible_frame(target: Target, *, timeout: float) -> None:
    import_tool = shutil.which("import")
    identify = shutil.which("identify")
    if import_tool is None or identify is None:
        await asyncio.sleep(1)
        return

    path = Path("/tmp/wargames/flightgear-ready.png")
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


def _read_telemetry(config: FlightGearConfig) -> dict[str, float | bool | None]:
    return {
        "altitude_ft": _float_property("/position/altitude-ft", config),
        "airspeed_kt": _float_property("/velocities/airspeed-kt", config),
        "pitch_deg": _float_property("/orientation/pitch-deg", config),
        "roll_deg": _float_property("/orientation/roll-deg", config),
        "heading_deg": _float_property("/orientation/heading-deg", config),
        "vertical_speed_fps": _float_property("/velocities/vertical-speed-fps", config),
        "throttle": _float_property("/controls/engines/engine/throttle", config),
        "crashed": _bool_property("/sim/crashed", config),
    }


def _float_property(path: str, config: FlightGearConfig) -> float | None:
    value = read_flightgear_property(path, port=config.telnet_port, timeout=0.1)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _bool_property(path: str, config: FlightGearConfig) -> bool | None:
    value = read_flightgear_property(path, port=config.telnet_port, timeout=0.1)
    if value is None:
        return None
    lowered = value.lower()
    if lowered in {"true", "1", "yes"}:
        return True
    if lowered in {"false", "0", "no"}:
        return False
    return None


async def _wait_for_simulator_ready(config: FlightGearConfig, *, timeout: float) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        if await asyncio.to_thread(is_flightgear_ready, config):
            return
        if asyncio.get_running_loop().time() >= deadline:
            raise TimeoutError("FlightGear did not finish startup before timeout")
        await asyncio.sleep(1)
