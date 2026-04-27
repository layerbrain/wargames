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
from wargames.evaluation.profile import profile_registry
from wargames.evaluation.schema import GameRewardSchema
from wargames.evaluation.task import RunConfig, TaskSpec, canonical_task_id
from wargames.harness.agent_loader import create_agent, list_agent_specs, load_agent_spec
from wargames.harness.turns import events_from_payload, validate_turn

_LINUX_BOX_ENV = "LAYERBRAIN_WARGAMES_IN_LINUX_BOX"
_LINUX_BOX_IMAGE = "wargames-linux"
_LINUX_BOX_DEFAULT_RESOLUTION = (1280, 720)
_BOX_COMMANDS = {"boot", "control", "install", "run", "serve"}
_INSTALLABLE_GAMES = ("redalert", "flightgear")
_TASK_GAMES = ("redalert", "flightgear")
_LINUX_BOX_CACHE_MOUNT = "/opt/wargames-cache"
_LINUX_BOX_CACHE_VOLUME = "wargames-games"
_OPENRA_REPO = "https://github.com/OpenRA/OpenRA.git"
_OPENRA_REF = "bleed"


def _game(id: str) -> GameDescriptor:
    if id == "redalert":
        from wargames.games.redalert import GAME

        return GAME
    if id == "flightgear":
        from wargames.games.flightgear import GAME

        return GAME
    raise SystemExit(f"unknown game: {id}")


def _reward_schema(game: str) -> GameRewardSchema:
    if game == "redalert":
        from wargames.games.redalert.reward_schema import REDALERT_REWARD_SCHEMA

        return REDALERT_REWARD_SCHEMA
    if game == "flightgear":
        from wargames.games.flightgear.reward_schema import FLIGHTGEAR_REWARD_SCHEMA

        return FLIGHTGEAR_REWARD_SCHEMA
    raise SystemExit(f"unknown game: {game}")


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

    target = getattr(session, "target", None)
    if target is None:
        return None
    display = target.display or os.getenv("DISPLAY", ":99")
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


def _load_local_env() -> None:
    path = _repo_root() / "local.env"
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _wargames_cache_dir(env: Mapping[str, str] = os.environ) -> Path:
    raw = env.get("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if raw:
        return Path(raw).expanduser()
    raw = env.get("XDG_CACHE_HOME")
    if raw:
        return Path(raw).expanduser() / "wargames"
    raw = env.get("HOME")
    if raw:
        return Path(raw).expanduser() / ".cache" / "wargames"
    return Path.home() / ".cache" / "wargames"


def _game_install_dir(game: str, env: Mapping[str, str] = os.environ) -> Path:
    return _wargames_cache_dir(env) / "games" / game


def _game_install_manifest(game: str, env: Mapping[str, str] = os.environ) -> Path:
    return _game_install_dir(game, env) / "install.json"


def _write_game_install_manifest(
    game: str,
    payload: Mapping[str, object],
    env: Mapping[str, str] = os.environ,
) -> None:
    manifest = _game_install_manifest(game, env)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _default_openra_root(env: Mapping[str, str] = os.environ) -> Path:
    return _game_install_dir("redalert", env) / "openra"


def _redalert_install_manifest(env: Mapping[str, str] = os.environ) -> Path:
    return _game_install_manifest("redalert", env)


def _is_openra_root(path: Path) -> bool:
    return (path / "mods" / "ra" / "mod.yaml").exists() and (path / "launch-game.sh").exists()


def _manifest_openra_root(env: Mapping[str, str] = os.environ) -> Path | None:
    manifest = _redalert_install_manifest(env)
    if not manifest.exists():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    raw = data.get("openra_root")
    if not isinstance(raw, str) or not raw:
        return None
    return Path(raw).expanduser()


def _write_redalert_install_manifest(
    openra_root: Path, env: Mapping[str, str] = os.environ
) -> None:
    manifest = _redalert_install_manifest(env)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "game": "redalert",
                "openra_binary": str(openra_root / "launch-game.sh"),
                "openra_root": str(openra_root),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _is_flightgear_root(path: Path) -> bool:
    return (path / "bin" / "fgfs").exists() or path.name == "fgfs"


def _find_flightgear_binary(root: Path | None = None) -> Path | None:
    candidates: list[Path | str | None] = [
        root if root and root.name == "fgfs" else None,
        root / "bin" / "fgfs" if root and root.name != "fgfs" else None,
        shutil.which("fgfs"),
        "/usr/games/fgfs",
        "/usr/bin/fgfs",
    ]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists():
                return path
    return None


def _flightgear_root(binary: Path, root: Path | None = None) -> Path:
    if root is not None:
        return root
    if binary.parent.name == "bin":
        return binary.parent.parent
    return binary.parent


def _should_run_in_linux_box(
    args: argparse.Namespace,
    *,
    platform: str = sys.platform,
    env: Mapping[str, str] = os.environ,
) -> bool:
    if env.get(_LINUX_BOX_ENV) == "1":
        return False
    if args.command == "missions" and getattr(args, "extract", False):
        return True
    return args.command in _BOX_COMMANDS


def _find_openra_root(env: Mapping[str, str] = os.environ) -> Path | None:
    candidates = [
        env.get("LAYERBRAIN_WARGAMES_REDALERT_OPENRA_ROOT"),
        env.get("OPENRA_ROOT"),
        _manifest_openra_root(env),
        _default_openra_root(env),
    ]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if _is_openra_root(path):
                return path
    return None


def _host_openra_support_dir(env: Mapping[str, str] = os.environ) -> Path:
    raw = env.get("LAYERBRAIN_WARGAMES_REDALERT_HOST_SUPPORT_DIR")
    if raw:
        return Path(raw).expanduser()
    return _wargames_cache_dir(env) / "openra-support"


def _without_host_watch(argv: Sequence[str]) -> list[str]:
    inner = list(argv)
    if inner and inner[0] in {"boot", "control"} and "--no-watch" not in inner:
        inner = [arg for arg in inner if arg != "--watch"]
        inner.append("--no-watch")
    if inner and inner[0] == "run":
        try:
            index = inner.index("--watch")
        except ValueError:
            pass
        else:
            inner[index + 1] = "none"
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
    for key in (
        "LAYERBRAIN_WARGAMES_REDALERT_OPENRA_WINDOW_SIZE",
        "LAYERBRAIN_WARGAMES_XVFB_RESOLUTION",
    ):
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
        raise SystemExit(
            "WarGames needs the local Linux runtime box to run Red Alert from this host."
        )
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
    command = ["docker", "run", "--rm", "-i"]
    if argv and argv[0] == "serve":
        port = _arg_value(argv, "--port") or "8000"
        command.extend(["-p", f"127.0.0.1:{port}:{port}"])
    host_repo = _repo_root()
    command.extend(["-v", f"{host_repo}:/workspace/host-wargames"])
    command.extend(["-v", f"{_LINUX_BOX_CACHE_VOLUME}:{_LINUX_BOX_CACHE_MOUNT}"])
    command.extend(["--entrypoint", "/workspace/host-wargames/scripts/linux_box.sh"])
    env: dict[str, str] = {_LINUX_BOX_ENV: "1"}
    for key, value in os.environ.items():
        if key.startswith("LAYERBRAIN_WARGAMES_"):
            env[key] = value
    active_resolution = resolution or _runtime_resolution(env)
    env["LAYERBRAIN_WARGAMES_CACHE_DIR"] = _LINUX_BOX_CACHE_MOUNT
    env.setdefault("LAYERBRAIN_WARGAMES_XVFB_RESOLUTION", _resolution_text(active_resolution))
    env.setdefault("LAYERBRAIN_WARGAMES_XVFB_SCREEN", f"{_resolution_text(active_resolution)}x24")
    env.setdefault(
        "LAYERBRAIN_WARGAMES_REDALERT_OPENRA_WINDOW_SIZE", _resolution_text(active_resolution)
    )
    if stream_port is not None:
        env["LAYERBRAIN_WARGAMES_HOST_STREAM_URL"] = (
            f"udp://host.docker.internal:{stream_port}?pkt_size=1316"
        )
    env.setdefault(
        "LAYERBRAIN_WARGAMES_REDALERT_OPENRA_SUPPORT_DIR",
        f"{_LINUX_BOX_CACHE_MOUNT}/openra-support",
    )
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
    stream_process: subprocess.Popen[bytes] | None = None
    stream_port: int | None = None
    resolution = _runtime_resolution()
    watch = getattr(args, "watch", False)
    if watch is True or (isinstance(watch, str) and watch != "none"):
        stream_port = _free_udp_port()
        stream_process = _start_host_stream_viewer(stream_port, resolution=resolution)
    try:
        completed = subprocess.run(
            _linux_box_command(argv, stream_port=stream_port, resolution=resolution), check=False
        )
        return completed.returncode
    finally:
        _stop_process(stream_process)


def _clone_openra(*, repo: str, ref: str, target: Path) -> None:
    git = shutil.which("git")
    if git is None:
        raise SystemExit("git is required to install Red Alert")
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [git, "clone", "--depth", "1"]
    if ref:
        command.extend(["--branch", ref])
    command.extend([repo, str(target)])
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"OpenRA clone failed with exit code {exc.returncode}") from exc


def _install_probe(openra_root: Path) -> None:
    script = _repo_root() / "scripts" / "install_probe.sh"
    try:
        subprocess.run([str(script), str(openra_root)], check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"WarGames probe build failed with exit code {exc.returncode}") from exc


def _install_redalert(args: argparse.Namespace, env: Mapping[str, str] = os.environ) -> int:
    openra_root = Path(args.root).expanduser() if args.root else _default_openra_root(env)
    status = "present"
    if openra_root.exists():
        if openra_root.is_file():
            raise SystemExit(f"OpenRA install path is a file: {openra_root}")
        if not _is_openra_root(openra_root):
            if any(openra_root.iterdir()):
                raise SystemExit(
                    f"OpenRA install path exists but is not an OpenRA source checkout: {openra_root}"
                )
            _clone_openra(repo=args.repo, ref=args.ref, target=openra_root)
            status = "installed"
    else:
        _clone_openra(repo=args.repo, ref=args.ref, target=openra_root)
        status = "installed"

    if not _is_openra_root(openra_root):
        raise SystemExit(f"OpenRA checkout is missing Red Alert runtime files: {openra_root}")

    _host_openra_support_dir(env).mkdir(parents=True, exist_ok=True)
    probe_built = False
    if args.build_probe:
        _install_probe(openra_root)
        probe_built = True

    _write_redalert_install_manifest(openra_root, env)
    print(
        json.dumps(
            {
                "game": "redalert",
                "openra_binary": str(openra_root / "launch-game.sh"),
                "openra_root": str(openra_root),
                "probe_built": probe_built,
                "status": status,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _install_flightgear(args: argparse.Namespace, env: Mapping[str, str] = os.environ) -> int:
    root = Path(args.root).expanduser() if args.root else None
    if root is not None and not _is_flightgear_root(root):
        raise SystemExit(f"FlightGear root does not contain fgfs: {root}")

    binary = _find_flightgear_binary(root)
    status = "present"

    if binary is None:
        raise SystemExit(
            "FlightGear was not found in the Linux runtime. Rebuild the WarGames Docker image "
            "or register a container-visible install with --root."
        )

    payload = {
        "game": "flightgear",
        "fgfs_binary": str(binary),
        "root": str(_flightgear_root(binary, root)),
        "state_interface": "property-tree via --telnet/--httpd/generic protocol",
        "status": status,
    }
    _write_game_install_manifest("flightgear", payload, env)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


async def _install(args: argparse.Namespace) -> int:
    if os.environ.get(_LINUX_BOX_ENV) != "1" and not args.root:
        raise SystemExit(
            "game runtimes install inside the WarGames Docker runtime; "
            "run the normal host CLI or pass a container-visible --root"
        )
    if args.game == "redalert":
        return await asyncio.to_thread(_install_redalert, args)
    if args.game == "flightgear":
        return await asyncio.to_thread(_install_flightgear, args)
    raise SystemExit(f"unknown game: {args.game}")


async def _missions(args: argparse.Namespace) -> int:
    game = _game(args.game)
    config = _config(game)
    if args.extract:
        output = args.output or _mission_catalog_output(game, config)
        backend = game.backend_cls(config)
        written = backend.export_missions(output)
        print(
            json.dumps(
                {
                    "game": game.id,
                    "count": len(written),
                    "written": [str(path) for path in written],
                },
                indent=2,
            )
        )
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


def _mission_catalog_output(game: GameDescriptor, config: WarGamesConfig) -> str:
    if hasattr(config, "extracted_missions_dir"):
        return str(getattr(config, "extracted_missions_dir"))
    if hasattr(config, "missions_dir"):
        return str(getattr(config, "missions_dir"))
    return f"scenarios/{game.id}/missions"


async def _agents(args: argparse.Namespace) -> int:
    dirs = tuple(Path(path) for path in args.agent_dir)
    if args.agent_command == "list":
        for spec in list_agent_specs(dirs):
            print(f"{spec.id}\t{spec.kind}\t{spec.model or ''}\t{spec.description}")
        return 0
    if args.agent_command == "show":
        spec = load_agent_spec(args.agent_id, dirs)
        print(json.dumps(spec.__dict__, indent=2, sort_keys=True, default=str))
        return 0
    if args.agent_command == "validate":
        from wargames.harness.agent_spec import AgentSpec

        spec = AgentSpec.from_file(Path(args.path))
        print(json.dumps({"ok": True, "id": spec.id, "kind": spec.kind}, sort_keys=True))
        return 0
    raise SystemExit(f"unknown agents command: {args.agent_command}")


async def _profiles(args: argparse.Namespace) -> int:
    _game(args.game)
    if args.profile_command == "list":
        for profile in profile_registry.list(args.game):
            print(f"{profile.id}\t{profile.description}")
        return 0
    if args.profile_command == "show":
        profile = profile_registry.get(args.game, args.profile_id)
        print(
            json.dumps(
                {
                    "id": profile.id,
                    "game": profile.game,
                    "description": profile.description,
                    "per_step_entries": profile.per_step_entries,
                    "terminal_entries": profile.terminal_entries,
                    "step_reward_min": profile.step_reward_min,
                    "step_reward_max": profile.step_reward_max,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.profile_command == "validate":
        from wargames.evaluation.profile_loader import load_profile_yaml

        profile = load_profile_yaml(Path(args.path), schema=_reward_schema(args.game))
        print(json.dumps({"ok": True, "id": profile.id, "game": profile.game}, sort_keys=True))
        return 0
    if args.profile_command == "new":
        path = Path(args.output or f"{args.profile_id}.yaml")
        path.write_text(
            "\n".join(
                [
                    f"id: {args.profile_id}",
                    f"game: {args.game}",
                    'description: "Custom reward profile."',
                    "step_reward_min: -0.10",
                    "step_reward_max: 0.10",
                    "entries:",
                    "  - id: terminal",
                    "    fn: wargames.core.missions.rewards.terminal",
                    "    weight: 1.0",
                    "    when: terminal",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"created": str(path)}, sort_keys=True))
        return 0
    if args.profile_command == "dry-run":
        from wargames.evaluation.profile_loader import load_profile_yaml
        from wargames.core.world.probe import HiddenStateSnapshot

        profile = load_profile_yaml(Path(args.path))
        total: dict[str, float] = {}
        previous = None
        for line in Path(args.trace).read_text(encoding="utf-8").splitlines():
            data = json.loads(line)
            curr_raw = data.get("hidden")
            if curr_raw is None:
                continue
            curr = HiddenStateSnapshot(
                tick=int(curr_raw["tick"]), world=_object_tree(curr_raw["world"])
            )
            prev_raw = data.get("prev_hidden")
            prev = (
                HiddenStateSnapshot(
                    tick=int(prev_raw["tick"]), world=_object_tree(prev_raw["world"])
                )
                if prev_raw
                else previous
            )
            breakdown = await profile.score_step(prev, curr) if prev else None
            if breakdown is not None:
                for key, value in breakdown.entries.items():
                    total[key] = total.get(key, 0.0) + value
            previous = curr
        print(
            json.dumps({"total": sum(total.values()), "breakdown": total}, indent=2, sort_keys=True)
        )
        return 0
    raise SystemExit(f"unknown profile command: {args.profile_command}")


def _object_tree(value: object) -> object:
    from types import SimpleNamespace

    if isinstance(value, dict):
        return SimpleNamespace(**{key: _object_tree(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_object_tree(item) for item in value)
    return value


async def _run(args: argparse.Namespace) -> int:
    game = _game(args.game)
    mission = _resolve_run_mission(args)
    if args.profile:
        mission = mission.with_reward_profile(args.profile)
    profile_registry.get(mission.game, mission.reward_profile)
    run_config = RunConfig(
        recorder_mode=args.record,
        video_mode=args.video,
        frame_sample_rate=args.frame_sample_rate,
        write_trace=args.write_trace,
        out_dir=args.out,
    )
    spec = load_agent_spec(args.agent, tuple(Path(path) for path in args.agent_dir))
    agent = create_agent(spec)
    config = _config(game, capture_frames=True)
    from wargames.harness.runner import run_task

    async with WarGames.for_game(game, config) as wg:
        summary = await run_task(task=mission, run_config=run_config, wg=wg, agent=agent)
    print(json.dumps(summary.__dict__, indent=2, sort_keys=True))
    return 0


def _resolve_run_mission(args: argparse.Namespace) -> TaskSpec:
    seed = int(args.seed) if args.seed is not None else 0
    return TaskSpec(
        id=canonical_task_id(args.game, args.mission, seed),
        game=args.game,
        mission_id=args.mission,
        seed=seed,
        max_steps=args.max_steps,
        max_wall_seconds=args.max_wall_seconds,
        reward_profile=args.profile or "standard",
    )


async def _watch(args: argparse.Namespace) -> int:
    root = Path(args.runs_dir) / args.run_id
    events = root / "events.jsonl"
    rewards = root / "rewards.jsonl"
    if not events.exists() and not rewards.exists():
        raise SystemExit(f"no replay events found for run: {args.run_id}")
    for path in (events, rewards):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            print(line)
    return 0


async def _export(args: argparse.Namespace) -> int:
    run_root = Path(args.runs_dir) / args.run_id
    if not run_root.exists():
        raise SystemExit(f"run not found: {args.run_id}")
    out = Path(args.out) / args.run_id
    out.mkdir(parents=True, exist_ok=True)
    names = ["summary.json", "end_state.json", "events.jsonl", "rewards.jsonl"]
    if args.include_trace:
        names.append("trace.jsonl")
    for name in names:
        source = run_root / name
        if source.exists():
            (out / name).write_bytes(source.read_bytes())
    frames = run_root / "frames"
    if args.video == "mp4":
        if not frames.exists():
            raise SystemExit("cannot export mp4: run has no frames/")
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise SystemExit("ffmpeg is required for --video mp4")
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(args.framerate),
                "-i",
                str(frames / "%06d.png"),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(out / "video.mp4"),
            ],
            check=True,
        )
    print(json.dumps({"exported": str(out)}, sort_keys=True))
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
            print(
                json.dumps(
                    {
                        "event": "booted",
                        "mission": mission.session.mission.id,
                        "frame": _frame_payload(observation.frame),
                    }
                )
            )
            await asyncio.sleep(args.hold)
        finally:
            _stop_process(watch_process)
            await mission.close()
    return 0


async def _control(args: argparse.Namespace) -> int:
    game = _game(args.game)
    config = _config(game, capture_frames=bool(args.capture_frames))
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
                result = None
                events_applied = 0
                for event in validate_turn(events_from_payload(json.loads(line))):
                    action = game.action_from_tool_call(event.name, event.arguments)
                    result = await mission.step(action)
                    events_applied += 1
                    if result.finished or result.truncated:
                        break
                if result is None:
                    continue
                print(
                    json.dumps(
                        {
                            "event": "action_result",
                            "tick": result.tick,
                            "finished": result.finished,
                            "truncated": result.truncated,
                            "frame": _frame_payload(result.frame),
                            "events_applied": events_applied,
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
    elif args.game == "flightgear":
        from wargames.games.flightgear.transport.ws import app
    else:
        raise SystemExit(f"unknown game: {args.game}")

    config = uvicorn.Config(
        app.fastapi_app, host=args.host, port=args.port, log_level=args.log_level
    )
    await uvicorn.Server(config).serve()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wargames")
    subcommands = parser.add_subparsers(dest="command", required=True)

    install = subcommands.add_parser("install", help="install game runtime dependencies")
    install.add_argument("--game", choices=_INSTALLABLE_GAMES, default="redalert")
    install.add_argument(
        "--root", help="use an existing game install or install into this path when supported"
    )
    install.add_argument("--repo", default=_OPENRA_REPO, help=argparse.SUPPRESS)
    install.add_argument("--ref", default=_OPENRA_REF, help=argparse.SUPPRESS)
    install.add_argument(
        "--build-probe", action="store_true", help="build the WarGames OpenRA probe immediately"
    )
    install.set_defaults(handler=_install)

    missions = subcommands.add_parser("missions", help="list or extract missions")
    missions.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    missions.add_argument("--difficulty", choices=("easy", "normal", "hard", "extra_hard"))
    missions.add_argument("--json", action="store_true")
    missions.add_argument("--extract", action="store_true")
    missions.add_argument("--output")
    missions.set_defaults(handler=_missions)

    run = subcommands.add_parser("run", help="run a named agent against a mission")
    run.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    run.add_argument("--mission", required=True)
    run.add_argument("--seed", type=int, default=0, help=argparse.SUPPRESS)
    run.add_argument("--max-steps", type=int, default=512)
    run.add_argument("--max-wall-seconds", type=int, default=900)
    run.add_argument("--agent", required=True)
    run.add_argument("--agent-dir", action="append", default=[])
    run.add_argument("--profile")
    run.add_argument("--watch", choices=("none", "window", "hud"), default="none")
    run.add_argument("--record", choices=("none", "summary_only", "full"), default="summary_only")
    run.add_argument("--video", choices=("none", "frames"), default="none")
    run.add_argument("--frame-sample-rate", type=int, default=1)
    run.add_argument("--write-trace", action="store_true")
    run.add_argument("--out", default="runs")
    run.set_defaults(handler=_run)

    agents = subcommands.add_parser("agents", help="list, show, or validate named agent configs")
    agent_subcommands = agents.add_subparsers(dest="agent_command", required=True)
    agents_list = agent_subcommands.add_parser("list")
    agents_list.add_argument("--agent-dir", action="append", default=[])
    agents_list.set_defaults(handler=_agents)
    agents_show = agent_subcommands.add_parser("show")
    agents_show.add_argument("agent_id")
    agents_show.add_argument("--agent-dir", action="append", default=[])
    agents_show.set_defaults(handler=_agents)
    agents_validate = agent_subcommands.add_parser("validate")
    agents_validate.add_argument("path")
    agents_validate.add_argument("--agent-dir", action="append", default=[])
    agents_validate.set_defaults(handler=_agents)

    profile = subcommands.add_parser("profile", help="list, show, or validate reward profiles")
    profile_subcommands = profile.add_subparsers(dest="profile_command", required=True)
    profile_list = profile_subcommands.add_parser("list")
    profile_list.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    profile_list.set_defaults(handler=_profiles)
    profile_show = profile_subcommands.add_parser("show")
    profile_show.add_argument("profile_id")
    profile_show.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    profile_show.set_defaults(handler=_profiles)
    profile_validate = profile_subcommands.add_parser("validate")
    profile_validate.add_argument("path")
    profile_validate.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    profile_validate.set_defaults(handler=_profiles)
    profile_new = profile_subcommands.add_parser("new")
    profile_new.add_argument("profile_id")
    profile_new.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    profile_new.add_argument("-o", "--output")
    profile_new.set_defaults(handler=_profiles)
    profile_dry_run = profile_subcommands.add_parser("dry-run")
    profile_dry_run.add_argument("path")
    profile_dry_run.add_argument("--trace", required=True)
    profile_dry_run.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    profile_dry_run.set_defaults(handler=_profiles)

    watch = subcommands.add_parser("watch", help="replay recorded public run events")
    watch.add_argument("run_id")
    watch.add_argument("--runs-dir", default="runs")
    watch.set_defaults(handler=_watch)

    export = subcommands.add_parser("export", help="export a recorded run")
    export.add_argument("run_id")
    export.add_argument("--runs-dir", default="runs")
    export.add_argument("--out", required=True)
    export.add_argument("--video", choices=("none", "mp4"), default="none")
    export.add_argument("--include-trace", action="store_true")
    export.add_argument("--framerate", type=int, default=30)
    export.set_defaults(handler=_export)

    boot = subcommands.add_parser("boot", help="boot a mission and keep it running")
    boot.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    boot.add_argument("--mission")
    boot.add_argument("--seed", type=int, default=0, help=argparse.SUPPRESS)
    boot.add_argument("--watch", dest="watch", action="store_true", default=True)
    boot.add_argument("--no-watch", dest="watch", action="store_false")
    boot.add_argument("--capture-frames", action="store_true")
    boot.add_argument("--hold", type=float, default=300.0)
    boot.set_defaults(handler=_boot)

    control = subcommands.add_parser(
        "control", help="dispatch primitive CUA events from JSON lines"
    )
    control.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    control.add_argument("--mission")
    control.add_argument("--seed", type=int, default=0, help=argparse.SUPPRESS)
    control.add_argument("--actions", required=True)
    control.add_argument("--watch", dest="watch", action="store_true", default=True)
    control.add_argument("--no-watch", dest="watch", action="store_false")
    control.add_argument("--capture-frames", action="store_true")
    control.set_defaults(handler=_control)

    serve = subcommands.add_parser("serve", help="serve the WebSocket transport")
    serve.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--log-level", default="info")
    serve.set_defaults(handler=_serve)

    return parser


async def async_main(argv: Sequence[str] | None = None) -> int:
    _load_local_env()
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
