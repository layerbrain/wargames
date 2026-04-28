from __future__ import annotations

import os
import pwd
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

from wargames.core.errors import GameNotInstalled, ProbeNotInstalled
from wargames.games.zeroad.config import ZeroADConfig

_ZEROAD_RUNTIME_USER = "wargames"


def locate_zeroad(config: ZeroADConfig) -> str:
    candidates = [
        config.binary,
        os.getenv("ZEROAD_BINARY"),
        _cache_binary(),
        str(Path(config.root) / "binaries" / "system" / "pyrogenesis") if config.root else None,
        str(Path(config.root) / "bin" / "pyrogenesis") if config.root else None,
        str(Path(config.root) / "pyrogenesis") if config.root else None,
        shutil.which("pyrogenesis"),
        shutil.which("0ad"),
        "/usr/lib/0ad/pyrogenesis",
        "/usr/games/pyrogenesis",
        "/usr/bin/pyrogenesis",
        "/usr/games/0ad",
        "/usr/bin/0ad",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate).expanduser())
    raise GameNotInstalled("0 A.D. binary was not found in its Docker runtime")


def zeroad_environment(config: ZeroADConfig, *, display: str | None = None) -> Mapping[str, str]:
    env: dict[str, str] = {
        "LIBGL_ALWAYS_SOFTWARE": "1",
        "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS": "0",
    }
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if cache_dir:
        root = Path(cache_dir).expanduser() / "games" / "zeroad"
        env["HOME"] = str(root / "home")
        env["XDG_CACHE_HOME"] = str(root / "xdg-cache")
        env["XDG_CONFIG_HOME"] = str(root / "xdg-config")
        env["XDG_DATA_HOME"] = str(root / "xdg-data")
    if config.root:
        env["ZEROAD_ROOT"] = config.root
    if display:
        env["DISPLAY"] = display
    return env


def zeroad_command(binary: str, config: ZeroADConfig, *, rl_host: str, rl_port: int) -> list[str]:
    width, height = config.window_size
    command = [
        binary,
        f"--rl-interface={rl_host}:{rl_port}",
        "-quickstart",
        "-nosound",
        "-conf=windowed:true",
        "-conf=borderless.fullscreen:false",
        "-conf=pauseonfocusloss:false",
        "-conf=rendererbackend:opengl",
        "-conf=shadows:false",
        f"-xres={width}",
        f"-yres={height}",
    ]
    runtime_user = _zeroad_runtime_user()
    if os.geteuid() == 0 and runtime_user is not None:
        return [
            "runuser",
            "--user",
            runtime_user,
            "--preserve-environment",
            "--",
            *command,
        ]
    return command


def prepare_zeroad_runtime_environment(env: Mapping[str, str]) -> None:
    paths = [
        Path(value).expanduser()
        for key in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME")
        if (value := env.get(key))
    ]
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)

    runtime_user = _zeroad_runtime_user()
    if os.geteuid() != 0 or runtime_user is None:
        return

    user = pwd.getpwnam(runtime_user)
    for path in paths:
        _chown_tree(path, uid=user.pw_uid, gid=user.pw_gid)


def zeroad_working_dir(binary: str, config: ZeroADConfig) -> str | None:
    if config.root:
        return config.root
    path = Path(binary).resolve()
    if path.parent.name == "system" and path.parent.parent.name == "binaries":
        return str(path.parent.parent.parent)
    return None


def bootstrap_zeroad(config: ZeroADConfig) -> None:
    binary = Path(locate_zeroad(config))
    if not binary.exists():
        raise GameNotInstalled(f"0 A.D. binary was not found: {binary}")
    verify_rl_interface_installed(str(binary))


def verify_rl_interface_installed(binary: str) -> None:
    path = Path(binary)
    if path.name == "0ad":
        return
    try:
        strings = subprocess.run(
            ["strings", str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        strings = None
    if strings is not None and "rl-interface" in strings.stdout:
        return
    raise ProbeNotInstalled(
        "0 A.D. must be built with the upstream RL interface. "
        "Run `wargames install --game zeroad` inside the WarGames runtime."
    )


def _cache_binary() -> str | None:
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if not cache_dir:
        return None
    return str(
        Path(cache_dir)
        / "games"
        / "zeroad"
        / "0ad"
        / "binaries"
        / "system"
        / "pyrogenesis"
    )


def _zeroad_runtime_user() -> str | None:
    if shutil.which("runuser") is None:
        return None
    try:
        pwd.getpwnam(_ZEROAD_RUNTIME_USER)
    except KeyError:
        return None
    return _ZEROAD_RUNTIME_USER


def _chown_tree(path: Path, *, uid: int, gid: int) -> None:
    try:
        os.chown(path, uid, gid)
    except PermissionError:
        return
    for root, dirs, files in os.walk(path):
        for name in (*dirs, *files):
            try:
                os.chown(Path(root) / name, uid, gid)
            except FileNotFoundError:
                pass
