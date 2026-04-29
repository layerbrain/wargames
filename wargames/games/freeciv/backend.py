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
from wargames.games.freeciv.config import FreeCivConfig
from wargames.games.freeciv.missions import (
    FreeCivMissionSpec,
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)
from wargames.games.freeciv.process import (
    FreeCivServerHandle,
    bootstrap_freeciv,
    freeciv_client_command,
    freeciv_environment,
    freeciv_server_command,
    locate_freeciv_client,
    locate_freeciv_server,
    prepare_freeciv_runtime_environment,
    start_freeciv_server,
    wait_for_tcp,
    write_freeciv_startup_script,
)
from wargames.games.freeciv.world import world_from_save
from wargames.games.redalert.window import focus_window, wait_for_window


class FreeCivSession(BackendSession):
    def __init__(
        self,
        *,
        id: str,
        mission: FreeCivMissionSpec,
        seed: int,
        target: Target,
        injector: InputInjector,
        server: FreeCivServerHandle,
        client: ProcessHandle,
        config: FreeCivConfig,
        initial_save: Path,
    ) -> None:
        self.id = id
        self.mission = mission
        self.seed = seed
        self.target = target
        self.injector = injector
        self.server = server
        self.client = client
        self.config = config
        self.capture = (
            ScreenRegionCapture(config.frame_dir) if config.capture_frames else NullWindowCapture()
        )
        self._last_hidden = self._snapshot(initial_save)

    async def step(self, action: ArenaAction) -> StepResult:
        prev = self._last_hidden
        await self.injector.send_many(self.target, lower_cua(action, self.target.rect))
        if self.config.action_settle_seconds > 0:
            await asyncio.sleep(self.config.action_settle_seconds)
        save = await self.server.save(
            f"step-{prev.tick}-{uuid.uuid4().hex[:8]}",
            timeout=self.config.snapshot_timeout,
        )
        hidden = self._snapshot(save)
        failed = bool(getattr(hidden.world.mission, "failed", False))
        if self.client.process.returncode not in {None, 0} or self.server.process.returncode not in {
            None,
            0,
        }:
            failed = True
        finished = bool(getattr(hidden.world.mission, "finished", False))
        truncated = hidden.tick >= self.mission.time_limit_ticks and not finished
        self._last_hidden = hidden
        frame = (await self.observe()).frame
        return StepResult(
            action=action,
            tick=hidden.tick,
            frame=frame,
            finished=finished,
            truncated=truncated,
            hidden=hidden,
            prev_hidden=prev,
            info={"save_path": str(save)},
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
        if self.client.process.returncode not in {None, 0} or self.server.process.returncode not in {
            None,
            0,
        }:
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
        await self.client.terminate(timeout=self.config.step_timeout)
        await self.server.terminate(timeout=self.config.step_timeout)

    def _snapshot(self, save: Path) -> HiddenStateSnapshot:
        world = world_from_save(save, self.mission, player_name=self.mission.player_name)
        return HiddenStateSnapshot(tick=world.tick, world=world)


class FreeCivBackend(Backend):
    game = "freeciv"

    def __init__(self, config: WarGamesConfig) -> None:
        if not isinstance(config, FreeCivConfig):
            config = FreeCivConfig(**config.__dict__)
        super().__init__(config)
        self.config: FreeCivConfig = config
        self._sessions: list[FreeCivSession] = []
        self._missions = self._discover_missions()
        self._bootstrapped = False

    def _discover_missions(self) -> tuple[FreeCivMissionSpec, ...]:
        catalog = load_mission_catalog(self.config.missions_dir)
        if catalog:
            return catalog
        root = self.config.root or "/usr/share/games/freeciv"
        return discover(root)

    def missions(self) -> tuple[MissionSpec, ...]:
        return self._missions

    def export_missions(self, output_dir: str | Path) -> tuple[Path, ...]:
        root = self.config.root or "/usr/share/games/freeciv"
        written = extract_mission_catalog(root, output_dir)
        if not written:
            raise GameNotInstalled(f"Freeciv scenarios were not found under {root}")
        return written

    def supports(self, mission: MissionSpec) -> bool:
        return isinstance(mission, FreeCivMissionSpec) and mission.game == self.game

    async def bootstrap(self) -> None:
        if self._bootstrapped:
            return
        if sys.platform != "linux":
            raise GameNotInstalled(
                "WarGames Freeciv runs only inside its Linux/Xvfb Docker runtime"
            )
        bootstrap_freeciv(self.config)
        self._bootstrapped = True

    async def start(self, mission: MissionSpec, *, seed: int) -> BackendSession:
        if not self.supports(mission):
            raise ValueError(f"unsupported Freeciv mission: {mission.id}")
        await self.bootstrap()
        spec = mission  # type: ignore[assignment]
        display = os.getenv("DISPLAY", ":99")
        env = freeciv_environment(self.config, display=display)
        save_dir = prepare_freeciv_runtime_environment(self.config, env)
        script_path = write_freeciv_startup_script(spec, self.config, seed=seed)
        server = await start_freeciv_server(
            freeciv_server_command(
                locate_freeciv_server(self.config),
                self.config,
                spec,
                script_path=script_path,
                save_dir=save_dir,
            ),
            env=env,
            save_dir=save_dir,
            id=spec.id,
        )
        try:
            await wait_for_tcp(
                self.config.server_host,
                self.config.server_port,
                timeout=self.config.step_timeout,
            )
            client = await ProcessLauncher().start(
                freeciv_client_command(locate_freeciv_client(self.config), self.config, spec),
                env=env,
                timeout=self.config.step_timeout,
                id=f"{spec.id}:client",
            )
            width, height = self.config.window_size
            target = await wait_for_window(
                pid=client.pid,
                display=env.get("DISPLAY"),
                width=width,
                height=height,
                timeout=self.config.step_timeout,
                title="Freeciv",
            )
            await focus_window(target)
            await _wait_for_visible_frame(target, timeout=self.config.step_timeout)
            await asyncio.sleep(1.0)
            await server.send("start")
            initial_save = await server.save(
                f"initial-{seed}-{uuid.uuid4().hex[:8]}", timeout=self.config.snapshot_timeout
            )
            session = FreeCivSession(
                id=f"{spec.id}:{seed}:{uuid.uuid4().hex[:8]}",
                mission=spec,
                seed=seed,
                target=target,
                injector=self._injector_for(target),
                server=server,
                client=client,
                config=self.config,
                initial_save=initial_save,
            )
            await session.center_pointer()
            self._sessions.append(session)
            return session
        except Exception:
            await server.terminate(timeout=self.config.step_timeout)
            raise

    def _injector_for(self, target: Target) -> InputInjector:
        if self.config.injector_transport == "xtest":
            return XTestInjector()
        return XdotoolInjector()

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

    path = Path("/tmp/wargames/freeciv-ready.png")
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
        await asyncio.sleep(0.25)


def _has_visible_pixels(path: Path, identify: str) -> bool:
    if not path.exists():
        return False
    try:
        result = subprocess.run(
            [identify, "-format", "%[fx:mean]", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    try:
        return float(result.stdout.strip() or "0") > 0.01
    except ValueError:
        return False
