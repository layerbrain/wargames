from __future__ import annotations

import os
import shutil
import socket
from collections.abc import Mapping
from pathlib import Path

from wargames.core.errors import GameNotInstalled
from wargames.games.flightgear.config import FlightGearConfig
from wargames.games.flightgear.missions import FlightGearMissionSpec


def locate_fgfs(config: FlightGearConfig) -> str:
    candidates = [
        config.fgfs_binary,
        os.getenv("FGFS_BINARY"),
        str(Path(config.fgfs_root) / "bin" / "fgfs") if config.fgfs_root else None,
        shutil.which("fgfs"),
        "/usr/games/fgfs",
        "/usr/bin/fgfs",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise GameNotInstalled("FlightGear fgfs binary was not found in its Docker runtime")


def flightgear_environment(
    config: FlightGearConfig, *, display: str | None = None
) -> Mapping[str, str]:
    env: dict[str, str] = {
        "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS": "0",
    }
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if cache_dir:
        flightgear_cache = Path(cache_dir).expanduser() / "games" / "flightgear"
        env["FG_HOME"] = str(flightgear_cache / "home")
        env["FG_SCENERY"] = f"{flightgear_cache / 'scenery'}:/usr/share/games/flightgear/Scenery"
        env["XDG_CACHE_HOME"] = str(flightgear_cache / "xdg-cache")
    if display:
        env["DISPLAY"] = display
    return env


def bootstrap_flightgear(config: FlightGearConfig) -> None:
    binary = Path(locate_fgfs(config))
    if not binary.exists():
        raise GameNotInstalled(f"FlightGear fgfs binary was not found: {binary}")


def flightgear_command(
    binary: str, mission: FlightGearMissionSpec, config: FlightGearConfig
) -> list[str]:
    width, height = config.window_size
    command = [
        binary,
        f"--aircraft={mission.aircraft}",
        f"--airport={mission.airport}",
        f"--timeofday={mission.timeofday}",
        "--disable-real-weather-fetch",
        "--disable-sound",
        "--disable-terrasync",
        f"--telnet={config.telnet_port}",
        f"--httpd={config.http_port}",
        f"--geometry={width}x{height}",
        "--disable-fullscreen",
    ]
    if mission.runway:
        command.append(f"--runway={mission.runway}")
    command.extend(mission.startup_args)
    dbus = shutil.which("dbus-run-session")
    if dbus:
        return [dbus, "--", *command]
    return command


def read_flightgear_property(
    path: str,
    *,
    port: int,
    host: str = "127.0.0.1",
    timeout: float = 2.0,
) -> str | None:
    try:
        with socket.create_connection((host, port), timeout=timeout) as conn:
            conn.settimeout(min(timeout, 0.5))
            _read_telnet_until_prompt(conn)
            conn.settimeout(timeout)
            conn.sendall(f"get {path}\r\n".encode("ascii"))
            chunks = _read_telnet_until_prompt(conn)
    except OSError:
        return None
    return _parse_flightgear_property(path, b"".join(chunks).decode("utf-8", errors="replace"))


def _read_telnet_until_prompt(conn: socket.socket) -> list[bytes]:
    chunks: list[bytes] = []
    while True:
        try:
            chunk = conn.recv(4096)
        except TimeoutError:
            break
        if not chunk:
            break
        chunks.append(chunk)
        if b"/> " in b"".join(chunks):
            break
    return chunks


def _parse_flightgear_property(path: str, response: str) -> str | None:
    for raw_line in response.replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if line.startswith("/>"):
            line = line[2:].strip()
        if not line.startswith(path):
            continue
        _, has_value, value = line.partition("=")
        if not has_value:
            continue
        value = value.strip()
        if value.startswith("'"):
            return value.split("'", 2)[1]
        return value.split(maxsplit=1)[0] if value else ""
    return None


def is_flightgear_ready(config: FlightGearConfig) -> bool:
    fdm_initialized = read_flightgear_property(
        "/sim/signals/fdm-initialized",
        port=config.telnet_port,
    )
    if fdm_initialized != "true":
        return False

    splash_alpha = read_flightgear_property(
        "/sim/startup/splash-alpha",
        port=config.telnet_port,
    )
    if splash_alpha is None:
        return False
    try:
        return float(splash_alpha) <= 0.0
    except ValueError:
        return False
