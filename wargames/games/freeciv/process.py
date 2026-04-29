from __future__ import annotations

import asyncio
import os
import pwd
import shutil
import signal
import socket
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from wargames.core.errors import GameNotInstalled
from wargames.games.freeciv.config import FreeCivConfig
from wargames.games.freeciv.missions import FreeCivMissionSpec

FREECIV_RUNTIME_USER = "wargames"


@dataclass
class FreeCivServerHandle:
    id: str
    process: asyncio.subprocess.Process
    command: tuple[str, ...]
    env: Mapping[str, str]
    save_dir: Path

    @property
    def pid(self) -> int:
        if self.process.pid is None:
            raise RuntimeError("process has no pid")
        return self.process.pid

    async def send(self, command: str) -> None:
        if self.process.stdin is None:
            raise RuntimeError("Freeciv server stdin is not available")
        if self.process.returncode is not None:
            raise RuntimeError(f"Freeciv server exited with {self.process.returncode}")
        self.process.stdin.write(f"{command}\n".encode("utf-8"))
        await self.process.stdin.drain()

    async def save(self, label: str, *, timeout: float) -> Path:
        safe_label = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in label)
        stem = self.save_dir / safe_label
        before = _latest_mtime(_save_candidates(stem))
        await self.send(f"save {stem}")
        return await _wait_for_save(stem, after=before, timeout=timeout)

    async def terminate(self, timeout: float = 5.0) -> None:
        if self.process.returncode is not None:
            return
        try:
            await self.send("quit")
        except Exception:
            pass
        try:
            os.killpg(self.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        except Exception:
            self.process.terminate()
        try:
            await asyncio.wait_for(self.process.wait(), timeout=timeout)
        except TimeoutError:
            try:
                os.killpg(self.pid, signal.SIGKILL)
            except ProcessLookupError:
                return
            except Exception:
                self.process.kill()
            await self.process.wait()


def locate_freeciv_server(config: FreeCivConfig) -> str:
    candidates = [
        config.server_binary,
        os.getenv("FREECIV_SERVER_BINARY"),
        str(Path(config.root) / "freeciv-server") if config.root else None,
        str(Path(config.root) / "bin" / "freeciv-server") if config.root else None,
        str(Path(config.root) / "usr" / "games" / "freeciv-server") if config.root else None,
        shutil.which("freeciv-server"),
        "/usr/games/freeciv-server",
        "/usr/bin/freeciv-server",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise GameNotInstalled("Freeciv server binary was not found in its Docker runtime")


def locate_freeciv_client(config: FreeCivConfig) -> str:
    candidates = [
        config.client_binary,
        os.getenv("FREECIV_CLIENT_BINARY"),
        str(Path(config.root) / "freeciv-gtk3.22") if config.root else None,
        str(Path(config.root) / "bin" / "freeciv-gtk3.22") if config.root else None,
        str(Path(config.root) / "usr" / "games" / "freeciv-gtk3.22") if config.root else None,
        shutil.which("freeciv-gtk3.22"),
        shutil.which("freeciv-gtk3"),
        "/usr/games/freeciv-gtk3.22",
        "/usr/games/freeciv-gtk3",
        "/usr/bin/freeciv-gtk3.22",
        "/usr/bin/freeciv-gtk3",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise GameNotInstalled("Freeciv GTK client binary was not found in its Docker runtime")


def locate_freeciv_scenario(config: FreeCivConfig, mission: FreeCivMissionSpec) -> str:
    scenario = Path(mission.scenario_file)
    if scenario.is_absolute() and scenario.exists():
        return str(scenario)

    roots = [Path(config.root)] if config.root else []
    roots.extend([Path("/usr/share/games/freeciv"), Path("/usr")])
    candidates: list[Path] = []
    for root in roots:
        candidates.extend(
            [
                root / scenario,
                root / "scenarios" / scenario,
                root / "share" / "games" / "freeciv" / "scenarios" / scenario,
            ]
        )
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise GameNotInstalled(f"Freeciv scenario was not found: {mission.scenario_file}")


def freeciv_environment(config: FreeCivConfig, *, display: str | None = None) -> Mapping[str, str]:
    env: dict[str, str] = {
        "GDK_BACKEND": "x11",
        "LIBGL_ALWAYS_SOFTWARE": "1",
        "NO_AT_BRIDGE": "1",
        "SDL_AUDIODRIVER": "dummy",
    }
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if cache_dir:
        root = Path(cache_dir).expanduser() / "games" / "freeciv"
        env["HOME"] = str(root / "home")
        env["XDG_CACHE_HOME"] = str(root / "xdg-cache")
        env["XDG_CONFIG_HOME"] = str(root / "xdg-config")
        env["XDG_DATA_HOME"] = str(root / "xdg-data")
    if display:
        env["DISPLAY"] = display
    return env


def freeciv_save_dir(config: FreeCivConfig) -> Path:
    if config.save_dir:
        return Path(config.save_dir).expanduser()
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if cache_dir:
        return Path(cache_dir).expanduser() / "games" / "freeciv" / "saves"
    return Path("/tmp/wargames/freeciv-saves")


def prepare_freeciv_runtime_environment(config: FreeCivConfig, env: Mapping[str, str]) -> Path:
    paths = [
        Path(value)
        for key, value in env.items()
        if key in {"HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME"}
    ]
    paths.extend([Path(config.startup_dir), freeciv_save_dir(config)])
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
    _chown_for_runtime_user(paths)
    return freeciv_save_dir(config)


def bootstrap_freeciv(config: FreeCivConfig) -> None:
    server = Path(locate_freeciv_server(config))
    client = Path(locate_freeciv_client(config))
    if not server.exists():
        raise GameNotInstalled(f"Freeciv server binary was not found: {server}")
    if not client.exists():
        raise GameNotInstalled(f"Freeciv client binary was not found: {client}")


def freeciv_server_command(
    binary: str,
    config: FreeCivConfig,
    mission: FreeCivMissionSpec,
    *,
    script_path: Path,
    save_dir: Path,
) -> list[str]:
    command = [
        binary,
        "--Announce",
        "none",
        "--bind",
        config.server_host,
        "--port",
        str(config.server_port),
        "--saves",
        str(save_dir),
        "--read",
        str(script_path),
        "--exit-on-end",
        "--debug",
        "n",
    ]
    command.extend(["--file", locate_freeciv_scenario(config, mission)])
    return _wrap_runtime_user(command)


def freeciv_client_command(
    binary: str, config: FreeCivConfig, mission: FreeCivMissionSpec
) -> list[str]:
    width, height = config.window_size
    command = [
        binary,
        "--autoconnect",
        "--server",
        config.server_host,
        "--port",
        str(config.server_port),
        "--name",
        mission.player_name,
        "--Plugin",
        "none",
        "--",
        "--resolution",
        f"{width}x{height}",
    ]
    return _wrap_runtime_user(command)


def write_freeciv_startup_script(
    mission: FreeCivMissionSpec, config: FreeCivConfig, *, seed: int
) -> Path:
    directory = Path(config.startup_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{mission.id}.{seed}.serv"
    path.write_text(mission.startup_script(), encoding="utf-8")
    _chown_for_runtime_user([path])
    return path


async def start_freeciv_server(
    command: Sequence[str],
    *,
    env: Mapping[str, str],
    save_dir: Path,
    id: str,
) -> FreeCivServerHandle:
    process = await asyncio.create_subprocess_exec(
        *command,
        env={**os.environ, **env},
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        start_new_session=True,
    )
    return FreeCivServerHandle(
        id=id,
        process=process,
        command=tuple(command),
        env={**os.environ, **env},
        save_dir=save_dir,
    )


async def wait_for_tcp(host: str, port: int, *, timeout: float) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        try:
            with socket.create_connection((host, port), timeout=min(timeout, 0.5)):
                return
        except OSError:
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError(f"Freeciv server did not listen on {host}:{port}")
            await asyncio.sleep(0.05)


def _wrap_runtime_user(command: list[str]) -> list[str]:
    if os.name != "posix" or os.geteuid() != 0 or not _runtime_user_exists():
        return command
    runuser = shutil.which("runuser")
    if runuser is None:
        return command
    return [runuser, "--user", FREECIV_RUNTIME_USER, "--preserve-environment", "--", *command]


def _runtime_user_exists() -> bool:
    try:
        pwd.getpwnam(FREECIV_RUNTIME_USER)
    except KeyError:
        return False
    return True


def _chown_for_runtime_user(paths: Sequence[Path]) -> None:
    if os.name != "posix" or os.geteuid() != 0:
        return
    try:
        pwd.getpwnam(FREECIV_RUNTIME_USER)
    except KeyError:
        return
    for path in paths:
        try:
            shutil.chown(path, user=FREECIV_RUNTIME_USER, group=FREECIV_RUNTIME_USER)
        except OSError:
            pass


async def _wait_for_save(stem: Path, *, after: float, timeout: float) -> Path:
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        for path in _save_candidates(stem):
            try:
                stat = path.stat()
                if stat.st_mtime >= after and stat.st_size > 0 and await _file_size_is_stable(path):
                    return path
            except OSError:
                pass
        if asyncio.get_running_loop().time() >= deadline:
            raise TimeoutError(f"Freeciv save did not appear: {stem}")
        await asyncio.sleep(0.05)


async def _file_size_is_stable(path: Path) -> bool:
    try:
        first = path.stat().st_size
    except OSError:
        return False
    await asyncio.sleep(0.1)
    try:
        return path.stat().st_size == first
    except OSError:
        return False


def _save_candidates(stem: Path) -> tuple[Path, ...]:
    if stem.suffix:
        return (stem,)
    return (
        stem.with_suffix(".sav.xz"),
        stem.with_suffix(".sav.gz"),
        stem.with_suffix(".sav.bz2"),
        stem.with_suffix(".sav"),
    )


def _latest_mtime(paths: Sequence[Path]) -> float:
    values: list[float] = []
    for path in paths:
        try:
            values.append(path.stat().st_mtime)
        except OSError:
            pass
    return max(values, default=0.0)
