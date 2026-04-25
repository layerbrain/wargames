from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import shutil
import socket
import subprocess
import sys
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from wargames import GameDescriptor, WarGames, WarGamesConfig
from wargames.core.capture.frame import Frame

_LINUX_BOX_ENV = "LAYERBRAIN_WARGAMES_IN_LINUX_BOX"
_LINUX_BOX_IMAGE = "wargames-linux"
_LINUX_BOX_OPENRA_MOUNT = "/openra"
_LINUX_BOX_DEFAULT_RESOLUTION = (1280, 720)
_BOX_COMMANDS = {"boot", "control", "serve"}


def _game(id: str) -> GameDescriptor:
    if id == "redalert":
        from wargames.games.redalert import GAME

        return GAME
    raise SystemExit(f"unknown game: {id}")


def _config(game: GameDescriptor, *, capture_frames: bool = False) -> WarGamesConfig:
    config = game.config_cls.from_env()
    return replace(config, capture_frames=capture_frames)


def _default_mission(game: GameDescriptor, config: WarGamesConfig) -> str:
    missions = game.backend_cls(config).missions()
    if not missions:
        raise SystemExit(f"game has no missions: {game.id}")
    return missions[0].id


def _frame_payload(frame: Frame | None) -> dict[str, Any] | None:
    if frame is None:
        return None
    payload: dict[str, Any] = {
        "id": frame.id,
        "width": frame.width,
        "height": frame.height,
        "captured_tick": frame.captured_tick,
        "mime": frame.mime,
        "image_path": frame.image_path,
    }
    if frame.image_b64:
        payload["image_b64"] = frame.image_b64
    elif frame.image_path:
        payload["image_b64"] = base64.b64encode(Path(frame.image_path).read_bytes()).decode()
    return payload


def _start_watch_stream(session: object, config: WarGamesConfig) -> subprocess.Popen[bytes] | None:
    from wargames.core.errors import DependencyMissing
    from wargames.core.stream.x11 import X11StreamViewer
    from wargames.games.redalert.backend import RedAlertSession

    if not isinstance(session, RedAlertSession):
        return None
    display = session.target.display or os.getenv("DISPLAY", ":99")
    viewer_display = os.getenv("LAYERBRAIN_WARGAMES_VIEWER_DISPLAY")
    if viewer_display is None and os.getenv("DISPLAY") == display:
        raise DependencyMissing(
            "watch needs a viewer display separate from the game Xvfb display; "
            "set LAYERBRAIN_WARGAMES_VIEWER_DISPLAY=:0"
        )
    return X11StreamViewer(
        display=display,
        resolution=config.xvfb_resolution,
        title=f"WarGames {session.mission.id} {display}",
        viewer_display=viewer_display,
    ).start()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _should_run_in_linux_box(
    args: argparse.Namespace,
    *,
    platform: str = sys.platform,
    env: Mapping[str, str] = os.environ,
) -> bool:
    return platform != "linux" and env.get(_LINUX_BOX_ENV) != "1" and args.command in _BOX_COMMANDS


def _find_openra_root(env: Mapping[str, str] = os.environ) -> Path | None:
    candidates = [
        env.get("LAYERBRAIN_WARGAMES_REDALERT_OPENRA_ROOT"),
        env.get("OPENRA_ROOT"),
        str(_repo_root().parent / "openra-source"),
        "/Users/aaronkazah/Documents/Codex/2026-04-24/yo/openra-source",
    ]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if (path / "mods" / "ra" / "mod.yaml").exists() and (path / "launch-game.sh").exists():
                return path
    return None


def _host_openra_support_dir(env: Mapping[str, str] = os.environ) -> Path:
    raw = env.get("LAYERBRAIN_WARGAMES_REDALERT_HOST_SUPPORT_DIR")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".cache" / "wargames" / "openra-support"


def _without_host_watch(argv: Sequence[str]) -> list[str]:
    inner = [arg for arg in argv if arg != "--watch"]
    if inner and inner[0] in {"boot", "control"} and "--no-watch" not in inner:
        inner.append("--no-watch")
    if inner and inner[0] == "serve":
        if "--host" in inner:
            inner[inner.index("--host") + 1] = "0.0.0.0"
        else:
            inner.extend(["--host", "0.0.0.0"])
    return inner


def _free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _parse_resolution(value: str) -> tuple[int, int]:
    width, sep, height = value.replace("x", ",").partition(",")
    if not sep:
        raise ValueError(f"invalid resolution: {value!r}")
    return int(width.strip()), int(height.strip())


def _runtime_resolution(env: Mapping[str, str] = os.environ) -> tuple[int, int]:
    for key in ("LAYERBRAIN_WARGAMES_REDALERT_OPENRA_WINDOW_SIZE", "LAYERBRAIN_WARGAMES_XVFB_RESOLUTION"):
        value = env.get(key)
        if value:
            return _parse_resolution(value)
    return _LINUX_BOX_DEFAULT_RESOLUTION


def _resolution_text(resolution: tuple[int, int], *, separator: str = "x") -> str:
    return f"{resolution[0]}{separator}{resolution[1]}"


def _start_host_stream_viewer(port: int, *, resolution: tuple[int, int]) -> subprocess.Popen[bytes]:
    executable = shutil.which("ffplay") or "/opt/homebrew/bin/ffplay"
    if not Path(executable).exists():
        raise SystemExit("ffplay is required for --watch")
    return subprocess.Popen(
        [
            executable,
            "-hide_banner",
            "-loglevel",
            "warning",
            "-fflags",
            "nobuffer",
            "-flags",
            "low_delay",
            "-framedrop",
            "-noborder",
            "-window_title",
            "WarGames",
            "-x",
            str(resolution[0]),
            "-y",
            str(resolution[1]),
            "-i",
            f"udp://127.0.0.1:{port}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def _read_lines(stream: object) -> AsyncIterator[str]:
    while True:
        line = await asyncio.to_thread(stream.readline)  # type: ignore[attr-defined]
        if line == "":
            break
        yield line


def _stop_process(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def _image_exists(image: str) -> bool:
    return (
        subprocess.run(
            ["docker", "image", "inspect", image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def _ensure_linux_box_image() -> None:
    if shutil.which("docker") is None:
        raise SystemExit("WarGames needs the local Linux runtime box to run Red Alert from this host.")
    if _image_exists(_LINUX_BOX_IMAGE):
        return
    subprocess.run(
        ["docker", "build", "-f", "docker/linux/Dockerfile", "-t", _LINUX_BOX_IMAGE, "."],
        cwd=_repo_root(),
        check=True,
    )


def _linux_box_command(
    argv: Sequence[str],
    *,
    stream_port: int | None = None,
    resolution: tuple[int, int] | None = None,
) -> list[str]:
    openra_root = _find_openra_root()
    command = ["docker", "run", "--rm", "-i"]
    if argv and argv[0] == "serve":
        port = _arg_value(argv, "--port") or "8000"
        command.extend(["-p", f"127.0.0.1:{port}:{port}"])
    host_repo = _repo_root()
    command.extend(["-v", f"{host_repo}:/workspace/host-wargames"])
    command.extend(["--entrypoint", "/workspace/host-wargames/scripts/linux_box.sh"])
    env: dict[str, str] = {_LINUX_BOX_ENV: "1"}
    for key, value in os.environ.items():
        if key.startswith("LAYERBRAIN_WARGAMES_"):
            env[key] = value
    active_resolution = resolution or _runtime_resolution(env)
    env.setdefault("LAYERBRAIN_WARGAMES_XVFB_RESOLUTION", _resolution_text(active_resolution))
    env.setdefault("LAYERBRAIN_WARGAMES_XVFB_SCREEN", f"{_resolution_text(active_resolution)}x24")
    env.setdefault("LAYERBRAIN_WARGAMES_REDALERT_OPENRA_WINDOW_SIZE", _resolution_text(active_resolution))
    if stream_port is not None:
        env["LAYERBRAIN_WARGAMES_HOST_STREAM_URL"] = f"udp://host.docker.internal:{stream_port}?pkt_size=1316"
    if openra_root is not None:
        command.extend(["-v", f"{openra_root}:{_LINUX_BOX_OPENRA_MOUNT}"])
        env["LAYERBRAIN_WARGAMES_REDALERT_OPENRA_ROOT"] = _LINUX_BOX_OPENRA_MOUNT
        env["LAYERBRAIN_WARGAMES_REDALERT_OPENRA_BINARY"] = f"{_LINUX_BOX_OPENRA_MOUNT}/launch-game.sh"
    support_dir = _host_openra_support_dir()
    command.extend(["-v", f"{support_dir}:/tmp/wargames/openra-support"])
    env.setdefault("LAYERBRAIN_WARGAMES_REDALERT_OPENRA_SUPPORT_DIR", "/tmp/wargames/openra-support")
    for key, value in sorted(env.items()):
        command.extend(["-e", f"{key}={value}"])
    inner = (
        "cd /workspace/host-wargames "
        "&& python -m pip install -e '.[server]' >/tmp/wargames-pip.log "
        "&& exec python -m wargames "
    )
    inner += " ".join(shlex_quote(arg) for arg in _without_host_watch(argv))
    command.extend([_LINUX_BOX_IMAGE, "bash", "-lc", inner])
    return command


def shlex_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _arg_value(argv: Sequence[str], name: str) -> str | None:
    try:
        return argv[argv.index(name) + 1]
    except (ValueError, IndexError):
        return None


def _run_in_linux_box(argv: Sequence[str], args: argparse.Namespace) -> int:
    _ensure_linux_box_image()
    _host_openra_support_dir().mkdir(parents=True, exist_ok=True)
    stream_process: subprocess.Popen[bytes] | None = None
    stream_port: int | None = None
    resolution = _runtime_resolution()
    if bool(getattr(args, "watch", False)):
        stream_port = _free_udp_port()
        stream_process = _start_host_stream_viewer(stream_port, resolution=resolution)
    try:
        completed = subprocess.run(_linux_box_command(argv, stream_port=stream_port, resolution=resolution), check=False)
        return completed.returncode
    finally:
        _stop_process(stream_process)


async def _missions(args: argparse.Namespace) -> int:
    game = _game(args.game)
    config = _config(game)
    if args.extract:
        if args.game != "redalert":
            raise SystemExit("mission extraction is only implemented for redalert")
        from wargames.games.redalert.missions import extract_mission_catalog

        openra_root = getattr(config, "openra_root", None)
        if openra_root is None:
            raise SystemExit("LAYERBRAIN_WARGAMES_REDALERT_OPENRA_ROOT is required for mission extraction")
        output = args.output or getattr(config, "extracted_missions_dir")
        written = extract_mission_catalog(openra_root, output)
        print(json.dumps({"written": [str(path) for path in written]}, indent=2))
        return 0

    missions = game.backend_cls(config).missions()
    if args.difficulty:
        missions = tuple(mission for mission in missions if mission.difficulty == args.difficulty)
    if args.json:
        print(json.dumps([mission.__dict__ for mission in missions], indent=2, sort_keys=True))
    else:
        for mission in missions:
            tags = ",".join(mission.tags)
            print(f"{mission.id}\t{mission.difficulty}\t{mission.source}\t{tags}\t{mission.title}")
    return 0


async def _boot(args: argparse.Namespace) -> int:
    game = _game(args.game)
    config = _config(game, capture_frames=bool(args.capture_frames))
    mission_id = args.mission or _default_mission(game, config)
    watch_process: subprocess.Popen[bytes] | None = None
    async with WarGames.for_game(game, config) as wg:
        mission = await wg.start_mission(mission_id, seed=args.seed)
        try:
            if args.watch:
                watch_process = _start_watch_stream(mission.session, config)
            observation = await mission.observe()
            print(json.dumps({"event": "booted", "mission": mission.session.mission.id, "frame": _frame_payload(observation.frame)}))
            await asyncio.sleep(args.hold)
        finally:
            _stop_process(watch_process)
            await mission.close()
    return 0


async def _control(args: argparse.Namespace) -> int:
    game = _game(args.game)
    config = _config(game, capture_frames=True)
    mission_id = args.mission or _default_mission(game, config)
    stream = sys.stdin if args.actions == "-" else open(args.actions, encoding="utf-8")
    watch_process: subprocess.Popen[bytes] | None = None
    async with WarGames.for_game(game, config) as wg:
        mission = await wg.start_mission(mission_id, seed=args.seed)
        try:
            if args.watch:
                watch_process = _start_watch_stream(mission.session, config)
            async for line in _read_lines(stream):
                if not line.strip():
                    continue
                tool_call = json.loads(line)
                name = str(tool_call.get("name") or tool_call.get("tool"))
                arguments = dict(tool_call.get("arguments", {}))
                action = game.action_from_tool_call(name, arguments)
                result = await mission.step(action)
                print(
                    json.dumps(
                        {
                            "event": "action_result",
                            "tick": result.tick,
                            "finished": result.finished,
                            "truncated": result.truncated,
                            "frame": _frame_payload(result.frame),
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
        finally:
            _stop_process(watch_process)
            await mission.close()
            if stream is not sys.stdin:
                stream.close()
    return 0


async def _serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn  # type: ignore[import-not-found]
    except Exception as exc:
        raise SystemExit("uvicorn is required to serve WarGames WS") from exc

    if args.game == "redalert":
        from wargames.games.redalert.transport.ws import app
    else:
        raise SystemExit(f"unknown game: {args.game}")

    config = uvicorn.Config(app.fastapi_app, host=args.host, port=args.port, log_level=args.log_level)
    await uvicorn.Server(config).serve()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wargames")
    subcommands = parser.add_subparsers(dest="command", required=True)

    missions = subcommands.add_parser("missions", help="list or extract missions")
    missions.add_argument("--game", choices=("redalert",), default="redalert")
    missions.add_argument("--difficulty", choices=("easy", "normal", "hard", "extra_hard"))
    missions.add_argument("--json", action="store_true")
    missions.add_argument("--extract", action="store_true")
    missions.add_argument("--output")
    missions.set_defaults(handler=_missions)

    boot = subcommands.add_parser("boot", help="boot a mission and keep it running")
    boot.add_argument("--game", choices=("redalert",), default="redalert")
    boot.add_argument("--mission")
    boot.add_argument("--seed", type=int, default=42)
    boot.add_argument("--watch", dest="watch", action="store_true", default=True)
    boot.add_argument("--no-watch", dest="watch", action="store_false")
    boot.add_argument("--capture-frames", action="store_true")
    boot.add_argument("--hold", type=float, default=300.0)
    boot.set_defaults(handler=_boot)

    control = subcommands.add_parser("control", help="dispatch CUA tool calls from JSON lines")
    control.add_argument("--game", choices=("redalert",), default="redalert")
    control.add_argument("--mission")
    control.add_argument("--seed", type=int, default=42)
    control.add_argument("--actions", required=True)
    control.add_argument("--watch", dest="watch", action="store_true", default=True)
    control.add_argument("--no-watch", dest="watch", action="store_false")
    control.set_defaults(handler=_control)

    serve = subcommands.add_parser("serve", help="serve the WebSocket transport")
    serve.add_argument("--game", choices=("redalert",), default="redalert")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--log-level", default="info")
    serve.set_defaults(handler=_serve)

    return parser


async def async_main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(argv)
    if _should_run_in_linux_box(args):
        return await asyncio.to_thread(_run_in_linux_box, argv, args)
    return await args.handler(args)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return asyncio.run(async_main(argv))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
