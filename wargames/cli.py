from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from wargames import GameDescriptor, WarGames, WarGamesConfig
from wargames.core.capture.audio import AudioChunk
from wargames.core.capture.frame import Frame
from wargames.evaluation.profile import profile_registry
from wargames.evaluation.schema import GameRewardSchema
from wargames.evaluation.task import RunConfig, TaskSpec, canonical_task_id
from wargames.games.registry import SUPPORTED_GAMES, load_game
from wargames.harness.agent_loader import create_agent, list_agent_specs, load_agent_spec
from wargames.harness.turns import events_from_payload, validate_turn

_LINUX_BOX_ENV = "LAYERBRAIN_WARGAMES_IN_LINUX_BOX"
_LINUX_BOX_DEFAULT_RESOLUTION = (1280, 720)
_BOX_COMMANDS = {"boot", "control", "install", "run", "serve"}
_INSTALLABLE_GAMES = SUPPORTED_GAMES
_TASK_GAMES = _INSTALLABLE_GAMES
_LINUX_BOX_CACHE_MOUNT = "/opt/wargames-cache"
_LINUX_BOX_BASE_IMAGE = "wargames-linux-base"
_LINUX_BOX_BASE_DOCKERFILE = "docker/base/Dockerfile"


@dataclass(frozen=True)
class LinuxBoxRuntime:
    game: str
    image: str
    dockerfile: str
    cache_volume: str
    base_image: str = _LINUX_BOX_BASE_IMAGE
    platform: str | None = None


_LINUX_BOX_RUNTIMES = {
    "redalert": LinuxBoxRuntime(
        game="redalert",
        image="wargames-linux-redalert",
        dockerfile="docker/redalert/Dockerfile",
        cache_volume="wargames-redalert",
    ),
    "flightgear": LinuxBoxRuntime(
        game="flightgear",
        image="wargames-linux-flightgear",
        dockerfile="docker/flightgear/Dockerfile",
        cache_volume="wargames-flightgear",
    ),
    "supertuxkart": LinuxBoxRuntime(
        game="supertuxkart",
        image="wargames-linux-supertuxkart",
        dockerfile="docker/supertuxkart/Dockerfile",
        cache_volume="wargames-supertuxkart",
    ),
    "zeroad": LinuxBoxRuntime(
        game="zeroad",
        image="wargames-linux-zeroad",
        dockerfile="docker/zeroad/Dockerfile",
        cache_volume="wargames-zeroad",
    ),
    "freeciv": LinuxBoxRuntime(
        game="freeciv",
        image="wargames-linux-freeciv",
        dockerfile="docker/freeciv/Dockerfile",
        cache_volume="wargames-freeciv",
    ),
    "doom": LinuxBoxRuntime(
        game="doom",
        image="wargames-linux-doom",
        dockerfile="docker/doom/Dockerfile",
        cache_volume="wargames-doom",
    ),
    "supertux": LinuxBoxRuntime(
        game="supertux",
        image="wargames-linux-supertux",
        dockerfile="docker/supertux/Dockerfile",
        cache_volume="wargames-supertux",
    ),
    "mindustry": LinuxBoxRuntime(
        game="mindustry",
        image="wargames-linux-mindustry",
        dockerfile="docker/mindustry/Dockerfile",
        cache_volume="wargames-mindustry",
        base_image="wargames-linux-base-amd64",
        platform="linux/amd64",
    ),
    "craftium": LinuxBoxRuntime(
        game="craftium",
        image="wargames-linux-craftium",
        dockerfile="docker/craftium/Dockerfile",
        cache_volume="wargames-craftium",
        base_image="wargames-linux-base-amd64",
        platform="linux/amd64",
    ),
    "ikemen": LinuxBoxRuntime(
        game="ikemen",
        image="wargames-linux-ikemen",
        dockerfile="docker/ikemen/Dockerfile",
        cache_volume="wargames-ikemen",
        base_image="wargames-linux-base-amd64",
        platform="linux/amd64",
    ),
    "opensurge": LinuxBoxRuntime(
        game="opensurge",
        image="wargames-linux-opensurge",
        dockerfile="docker/opensurge/Dockerfile",
        cache_volume="wargames-opensurge",
    ),
    "quaver": LinuxBoxRuntime(
        game="quaver",
        image="wargames-linux-quaver",
        dockerfile="docker/quaver/Dockerfile",
        cache_volume="wargames-quaver",
        base_image="wargames-linux-base-amd64",
        platform="linux/amd64",
    ),
    "naev": LinuxBoxRuntime(
        game="naev",
        image="wargames-linux-naev",
        dockerfile="docker/naev/Dockerfile",
        cache_volume="wargames-naev",
        base_image="wargames-linux-base-amd64",
        platform="linux/amd64",
    ),
}
_OPENRA_REPO = "https://github.com/OpenRA/OpenRA.git"
_OPENRA_REF = "bleed"
_SUPERTUXKART_REPO = "https://github.com/supertuxkart/stk-code.git"
_SUPERTUXKART_REF = "1.4"
_ZEROAD_REPO = "https://gitea.wildfiregames.com/0ad/0ad.git"
_ZEROAD_REF = "v0.28.0"
_DOOM_REPO = "https://github.com/chocolate-doom/chocolate-doom.git"
_DOOM_REF = "chocolate-doom-3.1.1"
_SUPERTUX_REPO = "https://github.com/SuperTux/supertux.git"
_SUPERTUX_REF = "v0.7.0"
_MINDUSTRY_VERSION = "v146"
_CRAFTIUM_VERSION = "0.0.1"
_CRAFTIUM_REF = "v0.0.1"
_CRAFTIUM_REPO = "https://github.com/mikelma/craftium.git"
_IKEMEN_VERSION = "v0.99.0"
_OPENSURGE_REPO = "https://github.com/alemart/opensurge.git"
_OPENSURGE_REF = "v0.6.1.3"
_QUAVER_REPO = "https://github.com/Quaver/Quaver.git"
_QUAVER_REF = "670164b1b7eb451bd4302b060360ba70b3c88b40"
_NAEV_REPO = "https://github.com/naev/naev"
_NAEV_PACKAGE_VERSION = "0.8.2"


def _game(id: str) -> GameDescriptor:
    try:
        return load_game(id)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def _reward_schema(game: str) -> GameRewardSchema:
    if game == "redalert":
        from wargames.games.redalert.reward_schema import REDALERT_REWARD_SCHEMA

        return REDALERT_REWARD_SCHEMA
    if game == "flightgear":
        from wargames.games.flightgear.reward_schema import FLIGHTGEAR_REWARD_SCHEMA

        return FLIGHTGEAR_REWARD_SCHEMA
    if game == "supertuxkart":
        from wargames.games.supertuxkart.reward_schema import SUPERTUXKART_REWARD_SCHEMA

        return SUPERTUXKART_REWARD_SCHEMA
    if game == "zeroad":
        from wargames.games.zeroad.reward_schema import ZEROAD_REWARD_SCHEMA

        return ZEROAD_REWARD_SCHEMA
    if game == "freeciv":
        from wargames.games.freeciv.reward_schema import FREECIV_REWARD_SCHEMA

        return FREECIV_REWARD_SCHEMA
    if game == "doom":
        from wargames.games.doom.reward_schema import DOOM_REWARD_SCHEMA

        return DOOM_REWARD_SCHEMA
    if game == "supertux":
        from wargames.games.supertux.reward_schema import SUPERTUX_REWARD_SCHEMA

        return SUPERTUX_REWARD_SCHEMA
    if game == "mindustry":
        from wargames.games.mindustry.reward_schema import MINDUSTRY_REWARD_SCHEMA

        return MINDUSTRY_REWARD_SCHEMA
    if game == "craftium":
        from wargames.games.craftium.reward_schema import CRAFTIUM_REWARD_SCHEMA

        return CRAFTIUM_REWARD_SCHEMA
    if game == "ikemen":
        from wargames.games.ikemen.reward_schema import IKEMEN_REWARD_SCHEMA

        return IKEMEN_REWARD_SCHEMA
    if game == "opensurge":
        from wargames.games.opensurge.reward_schema import OPENSURGE_REWARD_SCHEMA

        return OPENSURGE_REWARD_SCHEMA
    if game == "quaver":
        from wargames.games.quaver.reward_schema import QUAVER_REWARD_SCHEMA

        return QUAVER_REWARD_SCHEMA
    if game == "naev":
        from wargames.games.naev.reward_schema import NAEV_REWARD_SCHEMA

        return NAEV_REWARD_SCHEMA
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


def _audio_payload(audio: AudioChunk | None) -> dict[str, Any] | None:
    if audio is None:
        return None
    payload: dict[str, Any] = {
        "id": audio.id,
        "captured_tick": audio.captured_tick,
        "sample_rate": audio.sample_rate,
        "channels": audio.channels,
        "sample_width": audio.sample_width,
        "duration_seconds": audio.duration_seconds,
        "mime": audio.mime,
        "audio_path": audio.audio_path,
    }
    if audio.audio_b64:
        payload["audio_b64"] = audio.audio_b64
    elif audio.audio_path:
        payload["audio_b64"] = base64.b64encode(Path(audio.audio_path).read_bytes()).decode()
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


def _is_supertuxkart_root(path: Path) -> bool:
    return (
        (path / "data" / "tracks").exists()
        or (path / "tracks").exists()
        or path.name == "supertuxkart"
    )


def _is_zeroad_root(path: Path) -> bool:
    return (
        (path / "binaries" / "data" / "mods" / "public" / "maps").exists()
        or (path / "data" / "mods" / "public" / "maps").exists()
        or (path / "mods" / "public" / "maps").exists()
        or path.name in {"pyrogenesis", "0ad"}
    )


def _is_freeciv_root(path: Path) -> bool:
    return (
        path.name in {"freeciv-server", "freeciv-gtk3.22", "freeciv-gtk3"}
        or (path / "bin" / "freeciv-server").exists()
        or (path / "bin" / "freeciv-gtk3.22").exists()
        or (path / "usr" / "games" / "freeciv-server").exists()
        or (path / "usr" / "games" / "freeciv-gtk3.22").exists()
    )


def _is_doom_root(path: Path) -> bool:
    return path.name == "chocolate-doom" or (path / "src" / "doom" / "g_game.c").exists()


def _is_supertux_root(path: Path) -> bool:
    return path.name == "supertux2" or (path / "src" / "supertux" / "game_session.cpp").exists()


def _is_opensurge_root(path: Path) -> bool:
    return path.name == "opensurge" or (path / "src" / "scenes" / "level.c").exists()


def _is_quaver_root(path: Path) -> bool:
    if path.is_file():
        return path.name == "Quaver"
    return (path / "Quaver" / "Quaver.csproj").exists() and (
        path / "Quaver.Shared" / "Quaver.Shared.csproj"
    ).exists()


def _is_naev_root(path: Path) -> bool:
    if path.is_file():
        return path.name == "naev"
    return (
        (path / "start.xml").exists()
        and (path / "events").is_dir()
        and (path / "missions").is_dir()
    ) or (
        (path / "dat" / "start.xml").exists()
        and (path / "dat" / "events").is_dir()
        and (path / "dat" / "missions").is_dir()
    )


def _is_mindustry_root(path: Path) -> bool:
    return (
        path.name in {"server-release.jar", "Mindustry.jar"}
        or (path / "server-release.jar").exists()
        or (path / "Mindustry.jar").exists()
    )


def _is_ikemen_root(path: Path) -> bool:
    if path.is_file():
        return path.name in {"Ikemen_GO_Linux", "Ikemen_GO"}
    return (
        ((path / "Ikemen_GO_Linux").exists() or (path / "Ikemen_GO").exists())
        and (path / "data" / "system.def").exists()
        and (path / "chars").exists()
        and (path / "stages").exists()
    )


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


def _find_supertuxkart_binary(root: Path | None = None) -> Path | None:
    candidates: list[Path | str | None] = [
        root if root and root.name == "supertuxkart" else None,
        root / "cmake_build" / "bin" / "supertuxkart"
        if root and (root / "CMakeLists.txt").exists()
        else None,
        root / "bin" / "supertuxkart" if root and root.name != "supertuxkart" else None,
        _default_supertuxkart_source_root() / "cmake_build" / "bin" / "supertuxkart",
        shutil.which("supertuxkart"),
        "/usr/games/supertuxkart",
        "/usr/bin/supertuxkart",
    ]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists():
                return path
    return None


def _find_zeroad_binary(root: Path | None = None) -> Path | None:
    candidates: list[Path | str | None] = [
        root if root and root.is_file() and root.name in {"pyrogenesis", "0ad"} else None,
        root / "binaries" / "system" / "pyrogenesis"
        if root and not root.is_file()
        else None,
        root / "bin" / "pyrogenesis" if root and not root.is_file() else None,
        _default_zeroad_source_root() / "binaries" / "system" / "pyrogenesis",
        shutil.which("pyrogenesis"),
        shutil.which("0ad"),
        "/usr/lib/0ad/pyrogenesis",
        "/usr/games/pyrogenesis",
        "/usr/bin/pyrogenesis",
        "/usr/games/0ad",
        "/usr/bin/0ad",
    ]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists():
                return path
    return None


def _find_freeciv_server_binary(root: Path | None = None) -> Path | None:
    candidates: list[Path | str | None] = [
        root if root and root.is_file() and root.name == "freeciv-server" else None,
        root / "bin" / "freeciv-server" if root and not root.is_file() else None,
        root / "usr" / "games" / "freeciv-server" if root and not root.is_file() else None,
        shutil.which("freeciv-server"),
        "/usr/games/freeciv-server",
        "/usr/bin/freeciv-server",
    ]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists():
                return path
    return None


def _find_freeciv_client_binary(root: Path | None = None) -> Path | None:
    candidates: list[Path | str | None] = [
        root
        if root and root.is_file() and root.name in {"freeciv-gtk3.22", "freeciv-gtk3"}
        else None,
        root / "bin" / "freeciv-gtk3.22" if root and not root.is_file() else None,
        root / "bin" / "freeciv-gtk3" if root and not root.is_file() else None,
        root / "usr" / "games" / "freeciv-gtk3.22" if root and not root.is_file() else None,
        root / "usr" / "games" / "freeciv-gtk3" if root and not root.is_file() else None,
        shutil.which("freeciv-gtk3.22"),
        shutil.which("freeciv-gtk3"),
        "/usr/games/freeciv-gtk3.22",
        "/usr/games/freeciv-gtk3",
        "/usr/bin/freeciv-gtk3.22",
        "/usr/bin/freeciv-gtk3",
    ]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists():
                return path
    return None


def _find_doom_binary(root: Path | None = None) -> Path | None:
    candidates: list[Path | str | None] = [
        root if root and root.is_file() and root.name == "chocolate-doom" else None,
        root / "build" / "src" / "chocolate-doom" if root and not root.is_file() else None,
        root / "chocolate-doom" if root and not root.is_file() else None,
        _default_doom_source_root() / "build" / "src" / "chocolate-doom",
        shutil.which("chocolate-doom"),
        "/usr/games/chocolate-doom",
        "/usr/bin/chocolate-doom",
    ]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists():
                return path
    return None


def _find_supertux_binary(root: Path | None = None) -> Path | None:
    candidates: list[Path | str | None] = [
        root if root and root.is_file() and root.name == "supertux2" else None,
        root / "build" / "supertux2" if root and not root.is_file() else None,
        root / "cmake_build" / "supertux2" if root and not root.is_file() else None,
        root / "supertux2" if root and not root.is_file() else None,
        root / "bin" / "supertux2" if root and not root.is_file() else None,
        _default_supertux_source_root() / "build" / "supertux2",
        shutil.which("supertux2"),
        "/usr/games/supertux2",
        "/usr/bin/supertux2",
    ]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists():
                return path
    return None


def _find_opensurge_binary(root: Path | None = None) -> Path | None:
    candidates: list[Path | str | None] = [
        root if root and root.is_file() and root.name == "opensurge" else None,
        root / "opensurge" if root and not root.is_file() else None,
        root / "build" / "opensurge" if root and not root.is_file() else None,
        root / "cmake_build" / "opensurge" if root and not root.is_file() else None,
        root / "bin" / "opensurge" if root and not root.is_file() else None,
        _default_opensurge_source_root() / "opensurge",
        shutil.which("opensurge"),
        "/usr/games/opensurge",
        "/usr/bin/opensurge",
    ]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists():
                return path
    return None


def _find_quaver_binary(root: Path | None = None) -> Path | None:
    candidates: list[Path | str | None] = [
        root if root and root.is_file() and root.name == "Quaver" else None,
        root / "Quaver" / "bin" / "Release" / "net6.0" / "Quaver"
        if root and not root.is_file()
        else None,
        root / "Quaver" / "bin" / "Debug" / "net6.0" / "Quaver"
        if root and not root.is_file()
        else None,
        root / "Quaver" if root and not root.is_file() and root.name == "net6.0" else None,
        _default_quaver_source_root() / "Quaver" / "bin" / "Release" / "net6.0" / "Quaver",
        shutil.which("Quaver"),
    ]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists():
                return path
    return None


def _find_naev_binary(root: Path | None = None) -> Path | None:
    candidates: list[Path | str | None] = [
        root if root and root.is_file() and root.name == "naev" else None,
        root / "naev" if root and not root.is_file() else None,
        shutil.which("naev"),
        "/usr/games/naev",
        "/usr/bin/naev",
    ]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists():
                return path
    return None


def _find_mindustry_server(root: Path | None = None) -> Path | None:
    candidates: list[Path | str | None] = [
        root if root and root.is_file() and root.name == "server-release.jar" else None,
        root / "server-release.jar" if root and not root.is_file() else None,
        _default_mindustry_root() / "server-release.jar",
    ]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists():
                return path
    return None


def _find_mindustry_client(root: Path | None = None) -> Path | None:
    candidates: list[Path | str | None] = [
        root if root and root.is_file() and root.name == "Mindustry.jar" else None,
        root / "Mindustry.jar" if root and not root.is_file() else None,
        _default_mindustry_root() / "Mindustry.jar",
    ]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser()
            if path.exists():
                return path
    return None


def _find_ikemen_binary(root: Path | None = None) -> Path | None:
    candidates: list[Path | str | None] = [
        root if root and root.is_file() and root.name in {"Ikemen_GO_Linux", "Ikemen_GO"} else None,
        root / "Ikemen_GO_Linux" if root and not root.is_file() else None,
        root / "Ikemen_GO" if root and not root.is_file() else None,
        _default_ikemen_root() / "Ikemen_GO_Linux",
        shutil.which("Ikemen_GO_Linux"),
        shutil.which("Ikemen_GO"),
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


def _supertuxkart_root(binary: Path, root: Path | None = None) -> Path:
    if root is not None and root.name != "supertuxkart":
        if (root / "CMakeLists.txt").exists():
            share_root = Path("/usr/share/games/supertuxkart")
            if share_root.exists():
                return share_root
        return root
    share_root = Path("/usr/share/games/supertuxkart")
    if share_root.exists():
        return share_root
    if binary.parent.name == "bin":
        return binary.parent.parent
    return binary.parent


def _zeroad_root(binary: Path, root: Path | None = None) -> Path:
    if root is not None and root.name not in {"pyrogenesis", "0ad"}:
        return root
    if binary.parent.name == "system" and binary.parent.parent.name == "binaries":
        return binary.parent.parent.parent
    share_root = Path("/usr/share/games/0ad")
    if share_root.exists():
        return share_root
    if binary.parent.name == "bin":
        return binary.parent.parent
    return binary.parent


def _freeciv_root(binary: Path, root: Path | None = None) -> Path:
    if root is not None and not root.is_file():
        return root
    if binary.parent.name == "games" and binary.parent.parent.name == "usr":
        return binary.parent.parent
    if binary.parent.name == "bin":
        return binary.parent.parent
    return binary.parent


def _doom_root(binary: Path, root: Path | None = None) -> Path:
    if root is not None and not root.is_file():
        return root
    if binary.parent.name == "src" and binary.parent.parent.name == "build":
        return binary.parent.parent.parent
    return binary.parent


def _supertux_root(binary: Path, root: Path | None = None) -> Path:
    if root is not None and not root.is_file():
        return root
    if binary.parent.name == "build":
        return binary.parent.parent
    if binary.parent.name == "bin":
        return binary.parent.parent
    return binary.parent


def _opensurge_root(binary: Path, root: Path | None = None) -> Path:
    if root is not None and not root.is_file():
        return root
    if binary.parent.name in {"build", "cmake_build", "bin"}:
        return binary.parent.parent
    return binary.parent


def _quaver_root(binary: Path, root: Path | None = None) -> Path:
    if root is not None and not root.is_file():
        return root
    if binary.parent.name == "net6.0":
        return binary.parent.parent.parent.parent
    return binary.parent


def _naev_data_source(root: Path | None = None) -> Path | None:
    candidates = [
        root if root and (root / "start.xml").exists() else None,
        root / "dat" if root and (root / "dat" / "start.xml").exists() else None,
        Path("/usr/share/naev/dat"),
    ]
    for candidate in candidates:
        if candidate and _is_naev_root(candidate):
            return candidate
    return None


def _default_supertuxkart_source_root(env: Mapping[str, str] = os.environ) -> Path:
    return _game_install_dir("supertuxkart", env) / "stk-code"


def _default_zeroad_source_root(env: Mapping[str, str] = os.environ) -> Path:
    return _game_install_dir("zeroad", env) / "0ad"


def _default_doom_source_root(env: Mapping[str, str] = os.environ) -> Path:
    return _game_install_dir("doom", env) / "chocolate-doom"


def _default_supertux_source_root(env: Mapping[str, str] = os.environ) -> Path:
    return _game_install_dir("supertux", env) / "supertux"


def _default_opensurge_source_root(env: Mapping[str, str] = os.environ) -> Path:
    return _game_install_dir("opensurge", env) / "opensurge"


def _default_quaver_source_root(env: Mapping[str, str] = os.environ) -> Path:
    return _game_install_dir("quaver", env) / "quaver"


def _default_mindustry_root(env: Mapping[str, str] = os.environ) -> Path:
    return _game_install_dir("mindustry", env)


def _default_craftium_root(env: Mapping[str, str] = os.environ) -> Path:
    return _game_install_dir("craftium", env)


def _default_ikemen_root(env: Mapping[str, str] = os.environ) -> Path:
    return _game_install_dir("ikemen", env)


def _default_naev_root(env: Mapping[str, str] = os.environ) -> Path:
    return _game_install_dir("naev", env)


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
        "LAYERBRAIN_WARGAMES_SUPERTUXKART_WINDOW_SIZE",
        "LAYERBRAIN_WARGAMES_ZEROAD_WINDOW_SIZE",
        "LAYERBRAIN_WARGAMES_FREECIV_WINDOW_SIZE",
        "LAYERBRAIN_WARGAMES_DOOM_WINDOW_SIZE",
        "LAYERBRAIN_WARGAMES_SUPERTUX_WINDOW_SIZE",
        "LAYERBRAIN_WARGAMES_IKEMEN_WINDOW_SIZE",
        "LAYERBRAIN_WARGAMES_OPENSURGE_WINDOW_SIZE",
        "LAYERBRAIN_WARGAMES_QUAVER_WINDOW_SIZE",
        "LAYERBRAIN_WARGAMES_NAEV_WINDOW_SIZE",
        "LAYERBRAIN_WARGAMES_FLIGHTGEAR_WINDOW_SIZE",
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


def _linux_box_runtime(game: str) -> LinuxBoxRuntime:
    return _LINUX_BOX_RUNTIMES.get(game, _LINUX_BOX_RUNTIMES["redalert"])


def _linux_box_game(args: argparse.Namespace) -> str:
    return str(getattr(args, "game", None) or "redalert")


def _docker_build(*, image: str, dockerfile: str, platform: str | None = None) -> None:
    command = ["docker", "build"]
    if platform:
        command.extend(["--platform", platform])
    command.extend(["-f", dockerfile, "-t", image, "."])
    subprocess.run(command, cwd=_repo_root(), check=True)


def _ensure_linux_box_image(runtime: LinuxBoxRuntime) -> None:
    if shutil.which("docker") is None:
        raise SystemExit(
            "WarGames needs Docker to run the per-game Linux/Xvfb runtime images."
        )
    if not _image_exists(runtime.base_image):
        _docker_build(
            image=runtime.base_image,
            dockerfile=_LINUX_BOX_BASE_DOCKERFILE,
            platform=runtime.platform,
        )
    if not _image_exists(runtime.image):
        _docker_build(image=runtime.image, dockerfile=runtime.dockerfile, platform=runtime.platform)


def _linux_box_command(
    argv: Sequence[str],
    *,
    runtime: LinuxBoxRuntime | None = None,
    stream_port: int | None = None,
    resolution: tuple[int, int] | None = None,
) -> list[str]:
    command = ["docker", "run", "--rm", "-i"]
    if argv and argv[0] == "serve":
        port = _arg_value(argv, "--port") or "8000"
        command.extend(["-p", f"127.0.0.1:{port}:{port}"])
    host_repo = _repo_root()
    active_runtime = runtime or _linux_box_runtime(_linux_box_game_from_argv(argv))
    if active_runtime.platform:
        command.extend(["--platform", active_runtime.platform])
    command.extend(["-v", f"{host_repo}:/workspace/host-wargames"])
    command.extend(["-v", f"{active_runtime.cache_volume}:{_LINUX_BOX_CACHE_MOUNT}"])
    command.extend(["--entrypoint", "/workspace/host-wargames/scripts/linux_box.sh"])
    env: dict[str, str] = {_LINUX_BOX_ENV: "1"}
    for key, value in os.environ.items():
        if key.startswith("LAYERBRAIN_WARGAMES_"):
            env[key] = value
    env["LAYERBRAIN_WARGAMES_GAME"] = active_runtime.game
    active_resolution = resolution or _runtime_resolution(env)
    if (
        active_runtime.game == "opensurge"
        and active_resolution == _LINUX_BOX_DEFAULT_RESOLUTION
        and "LAYERBRAIN_WARGAMES_OPENSURGE_WINDOW_SIZE" not in env
        and "LAYERBRAIN_WARGAMES_XVFB_RESOLUTION" not in env
    ):
        active_resolution = (1280, 960)
    if (
        active_runtime.game == "quaver"
        and active_resolution == _LINUX_BOX_DEFAULT_RESOLUTION
        and "LAYERBRAIN_WARGAMES_QUAVER_WINDOW_SIZE" not in env
        and "LAYERBRAIN_WARGAMES_XVFB_RESOLUTION" not in env
    ):
        active_resolution = (1280, 720)
    env["LAYERBRAIN_WARGAMES_CACHE_DIR"] = _LINUX_BOX_CACHE_MOUNT
    env.setdefault("LAYERBRAIN_WARGAMES_XVFB_RESOLUTION", _resolution_text(active_resolution))
    env.setdefault("LAYERBRAIN_WARGAMES_XVFB_SCREEN", f"{_resolution_text(active_resolution)}x24")
    env.setdefault(
        "LAYERBRAIN_WARGAMES_REDALERT_OPENRA_WINDOW_SIZE", _resolution_text(active_resolution)
    )
    env.setdefault(
        "LAYERBRAIN_WARGAMES_FLIGHTGEAR_WINDOW_SIZE", _resolution_text(active_resolution)
    )
    env.setdefault(
        "LAYERBRAIN_WARGAMES_SUPERTUXKART_WINDOW_SIZE", _resolution_text(active_resolution)
    )
    env.setdefault("LAYERBRAIN_WARGAMES_ZEROAD_WINDOW_SIZE", _resolution_text(active_resolution))
    env.setdefault("LAYERBRAIN_WARGAMES_FREECIV_WINDOW_SIZE", _resolution_text(active_resolution))
    env.setdefault("LAYERBRAIN_WARGAMES_DOOM_WINDOW_SIZE", _resolution_text(active_resolution))
    env.setdefault("LAYERBRAIN_WARGAMES_SUPERTUX_WINDOW_SIZE", _resolution_text(active_resolution))
    env.setdefault("LAYERBRAIN_WARGAMES_IKEMEN_WINDOW_SIZE", _resolution_text(active_resolution))
    env.setdefault("LAYERBRAIN_WARGAMES_OPENSURGE_WINDOW_SIZE", _resolution_text(active_resolution))
    env.setdefault("LAYERBRAIN_WARGAMES_QUAVER_WINDOW_SIZE", _resolution_text(active_resolution))
    env.setdefault("LAYERBRAIN_WARGAMES_NAEV_WINDOW_SIZE", _resolution_text(active_resolution))
    if stream_port is not None:
        env["LAYERBRAIN_WARGAMES_HOST_STREAM_URL"] = (
            f"udp://host.docker.internal:{stream_port}?pkt_size=1316"
        )
    env.setdefault(
        "LAYERBRAIN_WARGAMES_REDALERT_OPENRA_SUPPORT_DIR",
        f"{_LINUX_BOX_CACHE_MOUNT}/openra-support",
    )
    env.setdefault(
        "LAYERBRAIN_WARGAMES_REDALERT_OPENRA_ROOT",
        f"{_LINUX_BOX_CACHE_MOUNT}/games/redalert/openra",
    )
    env.setdefault(
        "LAYERBRAIN_WARGAMES_REDALERT_OPENRA_BINARY",
        f"{_LINUX_BOX_CACHE_MOUNT}/games/redalert/openra/launch-game.sh",
    )
    for key, value in sorted(env.items()):
        command.extend(["-e", f"{key}={value}"])
    inner = (
        "cd /workspace/host-wargames "
        "&& python -m pip install -e '.[server]' >/tmp/wargames-pip.log "
        "&& exec python -m wargames "
    )
    inner += " ".join(shlex_quote(arg) for arg in _without_host_watch(argv))
    command.extend([active_runtime.image, "bash", "-lc", inner])
    return command


def shlex_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _arg_value(argv: Sequence[str], name: str) -> str | None:
    try:
        return argv[argv.index(name) + 1]
    except (ValueError, IndexError):
        return None


def _linux_box_game_from_argv(argv: Sequence[str]) -> str:
    return _arg_value(argv, "--game") or "redalert"


def _run_in_linux_box(argv: Sequence[str], args: argparse.Namespace) -> int:
    runtime = _linux_box_runtime(_linux_box_game(args))
    _ensure_linux_box_image(runtime)
    stream_process: subprocess.Popen[bytes] | None = None
    stream_port: int | None = None
    resolution = _runtime_resolution()
    watch = getattr(args, "watch", False)
    if watch is True or (isinstance(watch, str) and watch != "none"):
        stream_port = _free_udp_port()
        stream_process = _start_host_stream_viewer(stream_port, resolution=resolution)
    try:
        completed = subprocess.run(
            _linux_box_command(
                argv,
                runtime=runtime,
                stream_port=stream_port,
                resolution=resolution,
            ),
            check=False,
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


def _clone_supertuxkart_source(target: Path) -> None:
    git = shutil.which("git")
    if git is None:
        raise SystemExit("git is required to install SuperTuxKart")
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        git,
        "clone",
        "--depth",
        "1",
        "--branch",
        _SUPERTUXKART_REF,
        _SUPERTUXKART_REPO,
        str(target),
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"SuperTuxKart clone failed with exit code {exc.returncode}") from exc


def _clone_zeroad_source(target: Path) -> None:
    git = shutil.which("git")
    if git is None:
        raise SystemExit("git is required to install 0 A.D.")
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        git,
        "clone",
        "--depth",
        "1",
        "--branch",
        _ZEROAD_REF,
        _ZEROAD_REPO,
        str(target),
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"0 A.D. clone failed with exit code {exc.returncode}") from exc


def _clone_doom_source(target: Path) -> None:
    git = shutil.which("git")
    if git is None:
        raise SystemExit("git is required to install Doom")
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        git,
        "clone",
        "--depth",
        "1",
        "--branch",
        _DOOM_REF,
        _DOOM_REPO,
        str(target),
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Chocolate Doom clone failed with exit code {exc.returncode}") from exc


def _clone_supertux_source(target: Path) -> None:
    git = shutil.which("git")
    if git is None:
        raise SystemExit("git is required to install SuperTux")
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        git,
        "clone",
        "--depth",
        "1",
        "--branch",
        _SUPERTUX_REF,
        "--recurse-submodules",
        "--shallow-submodules",
        _SUPERTUX_REPO,
        str(target),
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"SuperTux clone failed with exit code {exc.returncode}") from exc


def _clone_opensurge_source(target: Path) -> None:
    git = shutil.which("git")
    if git is None:
        raise SystemExit("git is required to install Open Surge")
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        git,
        "clone",
        "--depth",
        "1",
        "--branch",
        _OPENSURGE_REF,
        _OPENSURGE_REPO,
        str(target),
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Open Surge clone failed with exit code {exc.returncode}") from exc


def _clone_quaver_source(target: Path) -> None:
    git = shutil.which("git")
    if git is None:
        raise SystemExit("git is required to install Quaver")
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        git,
        "-c",
        "submodule.Quaver.Server.Client.update=none",
        "clone",
        "--depth",
        "1",
        "--recurse-submodules",
        _QUAVER_REPO,
        str(target),
    ]
    try:
        subprocess.run(command, check=True)
        subprocess.run(
            [git, "-C", str(target), "fetch", "--depth", "1", "origin", _QUAVER_REF],
            check=True,
        )
        subprocess.run([git, "-C", str(target), "checkout", _QUAVER_REF], check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Quaver clone failed with exit code {exc.returncode}") from exc


def _download_mindustry_server(target: Path) -> None:
    curl = shutil.which("curl")
    if curl is None:
        raise SystemExit("curl is required to install Mindustry")
    target.parent.mkdir(parents=True, exist_ok=True)
    url = (
        "https://github.com/Anuken/Mindustry/releases/download/"
        f"{_MINDUSTRY_VERSION}/server-release.jar"
    )
    try:
        subprocess.run([curl, "-L", "--retry", "3", "-o", str(target), url], check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Mindustry server download failed with exit code {exc.returncode}") from exc


def _download_mindustry_client(target: Path) -> None:
    curl = shutil.which("curl")
    if curl is None:
        raise SystemExit("curl is required to install Mindustry")
    target.parent.mkdir(parents=True, exist_ok=True)
    url = (
        "https://github.com/Anuken/Mindustry/releases/download/"
        f"{_MINDUSTRY_VERSION}/Mindustry.jar"
    )
    try:
        subprocess.run([curl, "-L", "--retry", "3", "-o", str(target), url], check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Mindustry client download failed with exit code {exc.returncode}") from exc


def _download_ikemen_release(target: Path) -> None:
    curl = shutil.which("curl")
    if curl is None:
        raise SystemExit("curl is required to install IKEMEN GO")
    target.mkdir(parents=True, exist_ok=True)
    archive = target / f"Ikemen_GO-{_IKEMEN_VERSION}-linux.zip"
    url = (
        "https://github.com/ikemen-engine/Ikemen-GO/releases/download/"
        f"{_IKEMEN_VERSION}/Ikemen_GO-{_IKEMEN_VERSION}-linux.zip"
    )
    try:
        subprocess.run([curl, "-L", "--retry", "3", "-o", str(archive), url], check=True)
        shutil.unpack_archive(str(archive), str(target), "zip")
    except (subprocess.CalledProcessError, shutil.ReadError) as exc:
        raise SystemExit("IKEMEN GO release download failed") from exc
    finally:
        archive.unlink(missing_ok=True)
    binary = target / "Ikemen_GO_Linux"
    if binary.exists():
        binary.chmod(binary.stat().st_mode | 0o111)


def _craftium_available() -> bool:
    completed = subprocess.run(
        [sys.executable, "-c", "import craftium, gymnasium"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def _ensure_craftium_package() -> None:
    if _craftium_available():
        return
    source = Path("/opt/craftium")
    if source.exists():
        package = str(source)
    else:
        package = f"git+{_CRAFTIUM_REPO}@{_CRAFTIUM_REF}"
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                package,
                "pillow>=10.0.0",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Craftium install failed with exit code {exc.returncode}") from exc


def _sync_zeroad_lfs(source_root: Path) -> None:
    if _zeroad_lfs_assets_ready(source_root):
        return
    if shutil.which("git") is None or shutil.which("git-lfs") is None:
        raise SystemExit("git-lfs is required to install 0 A.D. runtime assets")
    git = ["git", "-c", f"safe.directory={source_root}"]
    commands = (
        [*git, "lfs", "install", "--local"],
        [*git, "lfs", "pull"],
    )
    for command in commands:
        try:
            subprocess.run(command, cwd=source_root, check=True)
        except subprocess.CalledProcessError as exc:
            raise SystemExit(f"0 A.D. Git LFS sync failed with exit code {exc.returncode}") from exc
    if not _zeroad_lfs_assets_ready(source_root):
        raise SystemExit("0 A.D. Git LFS sync did not materialize runtime assets")


def _zeroad_lfs_assets_ready(source_root: Path) -> bool:
    font = source_root / "binaries" / "data" / "mods" / "mod" / "fonts" / "DejaVuSansMono.ttf"
    return font.exists() and font.stat().st_size > 100_000


def _install_probe(openra_root: Path) -> None:
    script = _repo_root() / "scripts" / "install_probe.sh"
    try:
        subprocess.run([str(script), str(openra_root)], check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"WarGames probe build failed with exit code {exc.returncode}") from exc


def _install_supertuxkart_probe(source_root: Path) -> None:
    script = _repo_root() / "scripts" / "install_supertuxkart_probe.sh"
    try:
        subprocess.run([str(script), str(source_root)], check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"WarGames SuperTuxKart state exporter build failed with exit code {exc.returncode}"
        ) from exc


def _install_doom_probe(source_root: Path) -> None:
    script = _repo_root() / "scripts" / "install_doom_probe.sh"
    try:
        subprocess.run([str(script), str(source_root)], check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"WarGames Doom state exporter build failed with exit code {exc.returncode}"
        ) from exc


def _install_supertux_probe(source_root: Path) -> None:
    script = _repo_root() / "scripts" / "install_supertux_probe.sh"
    try:
        subprocess.run([str(script), str(source_root)], check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"WarGames SuperTux state exporter build failed with exit code {exc.returncode}"
        ) from exc


def _install_opensurge_probe(source_root: Path) -> None:
    script = _repo_root() / "scripts" / "install_opensurge_probe.sh"
    try:
        subprocess.run([str(script), str(source_root)], check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"WarGames Open Surge state exporter build failed with exit code {exc.returncode}"
        ) from exc


def _install_quaver_probe(source_root: Path) -> None:
    script = _repo_root() / "scripts" / "install_quaver_probe.sh"
    try:
        subprocess.run([str(script), str(source_root)], check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"WarGames Quaver state exporter build failed with exit code {exc.returncode}"
        ) from exc


def _build_mindustry_probe(root: Path, server_jar: Path) -> Path:
    source_root = _repo_root() / "wargames" / "games" / "mindustry" / "plugin"
    output = root / "home" / ".local" / "share" / "Mindustry" / "mods" / "wargames-mindustry-state.jar"
    output.parent.mkdir(parents=True, exist_ok=True)
    java_files = [str(path) for path in sorted((source_root / "src").rglob("*.java"))]
    if not java_files:
        raise SystemExit(f"Mindustry WarGames plugin sources are missing: {source_root}")
    classes = root / "plugin-classes"
    shutil.rmtree(classes, ignore_errors=True)
    classes.mkdir(parents=True)
    try:
        subprocess.run(
            ["javac", "-cp", str(server_jar), "-d", str(classes), *java_files],
            check=True,
        )
        manifest = source_root / "plugin.json"
        subprocess.run(
            ["jar", "cf", str(output), "-C", str(classes), ".", "-C", str(source_root), manifest.name],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"WarGames Mindustry state plugin build failed with exit code {exc.returncode}"
        ) from exc
    finally:
        shutil.rmtree(classes, ignore_errors=True)
    return output


def _normalize_zeroad_premake_version(source_root: Path, *, jobs: str) -> None:
    premake_vendor_root = source_root / "libraries" / "source" / "premake-core"
    candidates = sorted(premake_vendor_root.glob("premake-core-*"))
    if not candidates:
        raise SystemExit(f"0 A.D. vendored Premake source was not built under {premake_vendor_root}")

    premake_root = next((path for path in candidates if "5.0.0" in path.name), candidates[-1])
    version = premake_root.name.removeprefix("premake-core-")
    makefile = premake_root / "build" / "bootstrap" / "Premake5.make"
    if not makefile.exists():
        raise SystemExit(f"0 A.D. vendored Premake makefile is missing: {makefile}")

    contents = makefile.read_text(encoding="utf-8")
    updated = re.sub(
        r'-DPREMAKE_VERSION=\\?"[^\\"]+\\?"',
        f'-DPREMAKE_VERSION=\\"{version}\\"',
        contents,
    )
    if updated == contents and f'-DPREMAKE_VERSION=\\"{version}\\"' not in contents:
        raise SystemExit(f"0 A.D. vendored Premake makefile lacks PREMAKE_VERSION: {makefile}")
    makefile.write_text(updated, encoding="utf-8")

    target_binary = premake_vendor_root / "bin" / "premake5"
    if target_binary.exists():
        try:
            completed = subprocess.run(
                [str(target_binary), "--version"],
                cwd=source_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            pass
        else:
            if version in completed.stdout:
                return

    shutil.rmtree(premake_root / "build" / "bootstrap" / "obj", ignore_errors=True)
    built_binary = premake_root / "bin" / "release" / "premake5"
    built_binary.unlink(missing_ok=True)
    target_binary.unlink(missing_ok=True)
    try:
        subprocess.run(
            ["make", "-C", "build/bootstrap", f"-j{jobs}", "config=release"],
            cwd=premake_root,
            check=True,
        )
        target_binary.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(built_binary, target_binary)
        completed = subprocess.run(
            [str(target_binary), "--version"],
            cwd=source_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"0 A.D. vendored Premake rebuild failed with exit code {exc.returncode}"
        ) from exc

    if version not in completed.stdout:
        raise SystemExit(
            "0 A.D. vendored Premake reports an incompatible version: "
            f"{completed.stdout.strip()}"
        )


def _build_zeroad_source(source_root: Path) -> None:
    jobs = str(max(1, min(os.cpu_count() or 1, 4)))
    if shutil.which("cbindgen") is None:
        try:
            subprocess.run(["cargo", "install", "--locked", "cbindgen@0.29.0"], check=True)
        except subprocess.CalledProcessError as exc:
            raise SystemExit(f"cbindgen install failed with exit code {exc.returncode}") from exc
    commands = (
        ["libraries/build-source-libs.sh"],
        ["build/workspaces/update-workspaces.sh", "--without-atlas", f"-j{jobs}"],
        ["make", "-C", "build/workspaces/gcc", f"-j{jobs}", "pyrogenesis"],
    )
    for command in commands:
        try:
            subprocess.run(command, cwd=source_root, check=True)
            if command[0] == "libraries/build-source-libs.sh":
                _normalize_zeroad_premake_version(source_root, jobs=jobs)
        except subprocess.CalledProcessError as exc:
            raise SystemExit(f"0 A.D. build failed with exit code {exc.returncode}") from exc


def _install_redalert(args: argparse.Namespace, env: Mapping[str, str] = os.environ) -> int:
    openra_root = Path(args.root).expanduser() if args.root else _default_openra_root(env)
    status = "present"
    if openra_root.exists():
        if openra_root.is_file():
            raise SystemExit(f"OpenRA install path is a file: {openra_root}")
        if not _is_openra_root(openra_root):
            if any(openra_root.iterdir()):
                raise SystemExit(
                    "OpenRA install path exists but is not an OpenRA source checkout: "
                    f"{openra_root}"
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
            "FlightGear was not found in its Docker runtime image. Rebuild the FlightGear "
            "runtime image or register a container-visible install with --root."
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


def _install_supertuxkart(args: argparse.Namespace, env: Mapping[str, str] = os.environ) -> int:
    root = Path(args.root).expanduser() if args.root else None
    source_root = (
        root
        if root and (root / "CMakeLists.txt").exists()
        else _default_supertuxkart_source_root(env)
    )
    status = "present"

    if not source_root.exists():
        _clone_supertuxkart_source(source_root)
        status = "installed"
    elif not (source_root / "CMakeLists.txt").exists():
        raise SystemExit(f"SuperTuxKart source path is not a source checkout: {source_root}")

    _install_supertuxkart_probe(source_root)
    binary = _find_supertuxkart_binary(source_root)
    if binary is None:
        raise SystemExit(f"SuperTuxKart build did not produce a binary under {source_root}")

    payload = {
        "game": "supertuxkart",
        "binary": str(binary),
        "root": str(_supertuxkart_root(binary, source_root)),
        "source_root": str(source_root),
        "state_interface": "WarGames in-process kart state exporter",
        "status": status,
    }
    _write_game_install_manifest("supertuxkart", payload, env)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _install_zeroad(args: argparse.Namespace, env: Mapping[str, str] = os.environ) -> int:
    root = Path(args.root).expanduser() if args.root else None
    source_root = (
        root
        if root and (root / "build" / "workspaces").exists()
        else _default_zeroad_source_root(env)
    )
    status = "present"

    binary = _find_zeroad_binary(root)
    if binary is None:
        if not source_root.exists():
            _clone_zeroad_source(source_root)
            status = "installed"
        elif not (source_root / "build" / "workspaces").exists():
            raise SystemExit(f"0 A.D. source path is not a source checkout: {source_root}")
        _sync_zeroad_lfs(source_root)
        _build_zeroad_source(source_root)
        binary = _find_zeroad_binary(source_root)
    elif (source_root / ".git").exists():
        _sync_zeroad_lfs(source_root)

    if binary is None:
        raise SystemExit(f"0 A.D. install did not produce a binary under {source_root}")

    payload = {
        "game": "zeroad",
        "binary": str(binary),
        "root": str(_zeroad_root(binary, root or source_root)),
        "source_root": str(source_root),
        "state_interface": "upstream 0 A.D. RL HTTP interface",
        "status": status,
    }
    _write_game_install_manifest("zeroad", payload, env)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _install_freeciv(args: argparse.Namespace, env: Mapping[str, str] = os.environ) -> int:
    root = Path(args.root).expanduser() if args.root else None
    if root is not None and not _is_freeciv_root(root):
        raise SystemExit(f"Freeciv root does not contain freeciv-server and GTK client: {root}")

    server = _find_freeciv_server_binary(root)
    client = _find_freeciv_client_binary(root)
    if server is None or client is None:
        raise SystemExit(
            "Freeciv was not found in its Docker runtime image. Rebuild the Freeciv "
            "runtime image or register a container-visible install with --root."
        )

    payload = {
        "game": "freeciv",
        "server_binary": str(server),
        "client_binary": str(client),
        "root": str(_freeciv_root(server, root)),
        "state_interface": "Freeciv server save snapshots",
        "status": "present",
    }
    _write_game_install_manifest("freeciv", payload, env)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _install_doom(args: argparse.Namespace, env: Mapping[str, str] = os.environ) -> int:
    from wargames.games.doom.missions import discover_iwads

    root = Path(args.root).expanduser() if args.root else None
    source_root = (
        root if root and (root / "CMakeLists.txt").exists() else _default_doom_source_root(env)
    )
    status = "present"

    if not source_root.exists():
        _clone_doom_source(source_root)
        status = "installed"
    elif not _is_doom_root(source_root):
        raise SystemExit(f"Chocolate Doom source path is not a source checkout: {source_root}")

    _install_doom_probe(source_root)
    binary = _find_doom_binary(source_root)
    if binary is None:
        raise SystemExit(f"Chocolate Doom build did not produce a binary under {source_root}")

    iwads = discover_iwads(None)
    if not iwads:
        raise SystemExit("Freedoom IWADs were not found in the Doom runtime image")

    payload = {
        "game": "doom",
        "binary": str(binary),
        "root": str(_doom_root(binary, source_root)),
        "source_root": str(source_root),
        "iwad": str(iwads[0]),
        "state_interface": "WarGames in-process Doom state exporter",
        "status": status,
    }
    _write_game_install_manifest("doom", payload, env)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _install_supertux(args: argparse.Namespace, env: Mapping[str, str] = os.environ) -> int:
    root = Path(args.root).expanduser() if args.root else None
    source_root = (
        root if root and (root / "CMakeLists.txt").exists() else _default_supertux_source_root(env)
    )
    status = "present"

    if not source_root.exists():
        _clone_supertux_source(source_root)
        status = "installed"
    elif not _is_supertux_root(source_root):
        raise SystemExit(f"SuperTux source path is not a source checkout: {source_root}")

    _install_supertux_probe(source_root)
    binary = _find_supertux_binary(source_root)
    if binary is None:
        raise SystemExit(f"SuperTux build did not produce a binary under {source_root}")

    data_dir = source_root / "data"
    if not (data_dir / "levels").exists():
        raise SystemExit(f"SuperTux data directory is missing under {source_root}")

    payload = {
        "game": "supertux",
        "binary": str(binary),
        "root": str(_supertux_root(binary, source_root)),
        "source_root": str(source_root),
        "data_dir": str(data_dir),
        "state_interface": "WarGames in-process SuperTux state exporter",
        "status": status,
    }
    _write_game_install_manifest("supertux", payload, env)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _install_opensurge(args: argparse.Namespace, env: Mapping[str, str] = os.environ) -> int:
    root = Path(args.root).expanduser() if args.root else None
    source_root = (
        root if root and (root / "CMakeLists.txt").exists() else _default_opensurge_source_root(env)
    )
    status = "present"

    if not source_root.exists():
        _clone_opensurge_source(source_root)
        status = "installed"
    elif not _is_opensurge_root(source_root):
        raise SystemExit(f"Open Surge source path is not a source checkout: {source_root}")

    _install_opensurge_probe(source_root)
    binary = _find_opensurge_binary(source_root)
    if binary is None:
        raise SystemExit(f"Open Surge build did not produce a binary under {source_root}")

    data_dir = source_root
    if not (data_dir / "levels").exists():
        raise SystemExit(f"Open Surge levels directory is missing under {source_root}")

    payload = {
        "game": "opensurge",
        "binary": str(binary),
        "root": str(_opensurge_root(binary, source_root)),
        "source_root": str(source_root),
        "data_dir": str(data_dir),
        "state_interface": "WarGames in-process Open Surge state exporter",
        "status": status,
    }
    _write_game_install_manifest("opensurge", payload, env)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _install_quaver(args: argparse.Namespace, env: Mapping[str, str] = os.environ) -> int:
    root = Path(args.root).expanduser() if args.root else None
    source_root = root if root and _is_quaver_root(root) else _default_quaver_source_root(env)
    status = "present"

    if not source_root.exists():
        _clone_quaver_source(source_root)
        status = "installed"
    elif not _is_quaver_root(source_root):
        raise SystemExit(f"Quaver source path is not a source checkout: {source_root}")

    _install_quaver_probe(source_root)
    binary = _find_quaver_binary(source_root)
    if binary is None:
        raise SystemExit(f"Quaver build did not produce a binary under {source_root}")

    default_maps = source_root / "Quaver.Resources" / "Quaver.Resources" / "DefaultMaps"
    if not any(default_maps.glob("*.qp")):
        raise SystemExit(f"Quaver default map archives are missing under {source_root}")

    runtime_root = binary.parent
    payload = {
        "game": "quaver",
        "binary": str(binary),
        "root": str(_quaver_root(binary, source_root)),
        "runtime_root": str(runtime_root),
        "source_root": str(source_root),
        "default_maps_dir": str(default_maps),
        "state_interface": "WarGames in-process Quaver state exporter",
        "status": status,
    }
    _write_game_install_manifest("quaver", payload, env)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _install_naev(args: argparse.Namespace, env: Mapping[str, str] = os.environ) -> int:
    root = Path(args.root).expanduser() if args.root else _default_naev_root(env)
    data_source = _naev_data_source(root if args.root else None) or _naev_data_source(None)
    if data_source is None:
        raise SystemExit(
            "Naev package data was not found in the Docker runtime image. Rebuild the Naev "
            "runtime image or register a container-visible data directory with --root."
        )
    binary = _find_naev_binary(root if args.root else None)
    if binary is None:
        raise SystemExit(
            "Naev binary was not found in the Docker runtime image. Rebuild the Naev "
            "runtime image or register a container-visible install with --root."
        )

    if root.is_file():
        install_root = root.parent
    elif data_source.resolve() == root.resolve():
        install_root = root.parent
    else:
        install_root = root
    data_dir = install_root / "dat"
    if data_source.resolve() != data_dir.resolve():
        data_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(data_source, data_dir, dirs_exist_ok=True)

    payload = {
        "game": "naev",
        "binary": str(binary),
        "root": str(install_root),
        "data_dir": str(data_dir),
        "source": _NAEV_REPO,
        "version": _NAEV_PACKAGE_VERSION,
        "state_interface": "Naev Lua stdout state exporter",
        "status": "present",
    }
    _write_game_install_manifest("naev", payload, env)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _install_mindustry(args: argparse.Namespace, env: Mapping[str, str] = os.environ) -> int:
    root = Path(args.root).expanduser() if args.root else _default_mindustry_root(env)
    install_root = root.parent if root.exists() and root.is_file() else root
    client = _find_mindustry_client(root)
    server = _find_mindustry_server(root)
    status = "present"
    if client is None:
        client = install_root / "Mindustry.jar"
        _download_mindustry_client(client)
        status = "installed"
    if server is None:
        server = install_root / "server-release.jar"
        _download_mindustry_server(server)
        status = "installed"
    plugin = _build_mindustry_probe(install_root, server)
    payload = {
        "game": "mindustry",
        "client_jar": str(client),
        "server_jar": str(server),
        "root": str(install_root),
        "plugin": str(plugin),
        "version": _MINDUSTRY_VERSION,
        "state_interface": "Mindustry client plugin JSONL state exporter",
        "status": status,
    }
    _write_game_install_manifest("mindustry", payload, env)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _install_craftium(args: argparse.Namespace, env: Mapping[str, str] = os.environ) -> int:
    root = Path(args.root).expanduser() if args.root else _default_craftium_root(env)
    root.mkdir(parents=True, exist_ok=True)
    _ensure_craftium_package()
    payload = {
        "game": "craftium",
        "root": str(root),
        "package": f"craftium=={_CRAFTIUM_VERSION}",
        "source": _CRAFTIUM_REPO,
        "ref": _CRAFTIUM_REF,
        "state_interface": "Craftium Gymnasium info and voxel observations",
        "status": "present",
    }
    _write_game_install_manifest("craftium", payload, env)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _install_ikemen(args: argparse.Namespace, env: Mapping[str, str] = os.environ) -> int:
    root = Path(args.root).expanduser() if args.root else _default_ikemen_root(env)
    install_root = root.parent if root.exists() and root.is_file() else root
    binary = _find_ikemen_binary(root)
    status = "present"
    if binary is None:
        if install_root.exists() and any(install_root.iterdir()):
            raise SystemExit(f"IKEMEN GO install path is not a runtime directory: {install_root}")
        _download_ikemen_release(install_root)
        status = "installed"
        binary = _find_ikemen_binary(install_root)
    if binary is None:
        raise SystemExit(f"IKEMEN GO install did not produce a binary under {install_root}")
    if not _is_ikemen_root(install_root):
        raise SystemExit(f"IKEMEN GO runtime content is missing under {install_root}")
    payload = {
        "game": "ikemen",
        "binary": str(binary),
        "root": str(install_root),
        "version": _IKEMEN_VERSION,
        "state_interface": "IKEMEN GO CommonLua JSONL state exporter",
        "status": status,
    }
    _write_game_install_manifest("ikemen", payload, env)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


async def _install(args: argparse.Namespace) -> int:
    if os.environ.get(_LINUX_BOX_ENV) != "1" and not args.root:
        raise SystemExit(
            "game runtimes install inside their per-game WarGames Docker image; "
            "run the normal host CLI or pass a container-visible --root"
        )
    if args.game == "redalert":
        return await asyncio.to_thread(_install_redalert, args)
    if args.game == "flightgear":
        return await asyncio.to_thread(_install_flightgear, args)
    if args.game == "supertuxkart":
        return await asyncio.to_thread(_install_supertuxkart, args)
    if args.game == "zeroad":
        return await asyncio.to_thread(_install_zeroad, args)
    if args.game == "freeciv":
        return await asyncio.to_thread(_install_freeciv, args)
    if args.game == "doom":
        return await asyncio.to_thread(_install_doom, args)
    if args.game == "supertux":
        return await asyncio.to_thread(_install_supertux, args)
    if args.game == "opensurge":
        return await asyncio.to_thread(_install_opensurge, args)
    if args.game == "quaver":
        return await asyncio.to_thread(_install_quaver, args)
    if args.game == "naev":
        return await asyncio.to_thread(_install_naev, args)
    if args.game == "mindustry":
        return await asyncio.to_thread(_install_mindustry, args)
    if args.game == "craftium":
        return await asyncio.to_thread(_install_craftium, args)
    if args.game == "ikemen":
        return await asyncio.to_thread(_install_ikemen, args)
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


async def _reward_profiles(args: argparse.Namespace) -> int:
    _game(args.game)
    if args.reward_profile_command == "list":
        for profile in profile_registry.list(args.game):
            print(f"{profile.id}\t{profile.description}")
        return 0
    if args.reward_profile_command == "show":
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
    if args.reward_profile_command == "validate":
        from wargames.evaluation.profile_loader import load_profile_yaml

        profile = load_profile_yaml(Path(args.path), schema=_reward_schema(args.game))
        print(json.dumps({"ok": True, "id": profile.id, "game": profile.game}, sort_keys=True))
        return 0
    if args.reward_profile_command == "new":
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
    if args.reward_profile_command == "dry-run":
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
    raise SystemExit(f"unknown reward profile command: {args.reward_profile_command}")


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
    if args.reward_profile:
        mission = mission.with_reward_profile(args.reward_profile)
    profile_registry.get(mission.game, mission.reward_profile)
    run_config = RunConfig(
        recorder_mode=args.record,
        video_mode=args.video,
        audio_mode=args.audio,
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
        reward_profile=args.reward_profile or "standard",
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
    audio = run_root / "audio"
    if audio.exists():
        shutil.copytree(audio, out / "audio", dirs_exist_ok=True)
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
                        "audio": _audio_payload(observation.audio),
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
                            "audio": _audio_payload(result.audio),
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
    elif args.game == "supertuxkart":
        from wargames.games.supertuxkart.transport.ws import app
    elif args.game == "zeroad":
        from wargames.games.zeroad.transport.ws import app
    elif args.game == "freeciv":
        from wargames.games.freeciv.transport.ws import app
    elif args.game == "doom":
        from wargames.games.doom.transport.ws import app
    elif args.game == "supertux":
        from wargames.games.supertux.transport.ws import app
    elif args.game == "opensurge":
        from wargames.games.opensurge.transport.ws import app
    elif args.game == "quaver":
        from wargames.games.quaver.transport.ws import app
    elif args.game == "naev":
        from wargames.games.naev.transport.ws import app
    elif args.game == "mindustry":
        from wargames.games.mindustry.transport.ws import app
    elif args.game == "craftium":
        from wargames.games.craftium.transport.ws import app
    elif args.game == "ikemen":
        from wargames.games.ikemen.transport.ws import app
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
    run.add_argument("--reward-profile")
    run.add_argument("--watch", choices=("none", "window", "hud"), default="none")
    run.add_argument("--record", choices=("none", "summary_only", "full"), default="summary_only")
    run.add_argument("--video", choices=("none", "frames"), default="none")
    run.add_argument("--audio", choices=("none", "chunks"), default="none")
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

    reward_profile = subcommands.add_parser(
        "reward-profile", help="list, show, or validate reward profiles"
    )
    reward_profile_subcommands = reward_profile.add_subparsers(
        dest="reward_profile_command", required=True
    )
    reward_profile_list = reward_profile_subcommands.add_parser("list")
    reward_profile_list.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    reward_profile_list.set_defaults(handler=_reward_profiles)
    reward_profile_show = reward_profile_subcommands.add_parser("show")
    reward_profile_show.add_argument("profile_id")
    reward_profile_show.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    reward_profile_show.set_defaults(handler=_reward_profiles)
    reward_profile_validate = reward_profile_subcommands.add_parser("validate")
    reward_profile_validate.add_argument("path")
    reward_profile_validate.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    reward_profile_validate.set_defaults(handler=_reward_profiles)
    reward_profile_new = reward_profile_subcommands.add_parser("new")
    reward_profile_new.add_argument("profile_id")
    reward_profile_new.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    reward_profile_new.add_argument("-o", "--output")
    reward_profile_new.set_defaults(handler=_reward_profiles)
    reward_profile_dry_run = reward_profile_subcommands.add_parser("dry-run")
    reward_profile_dry_run.add_argument("path")
    reward_profile_dry_run.add_argument("--trace", required=True)
    reward_profile_dry_run.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    reward_profile_dry_run.set_defaults(handler=_reward_profiles)

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
    boot.add_argument("--watch", dest="watch", action="store_true", default=False)
    boot.add_argument("--no-watch", dest="watch", action="store_false")
    boot.add_argument("--capture-frames", action="store_true")
    boot.add_argument("--hold", type=float, default=300.0)
    boot.set_defaults(handler=_boot)

    control = subcommands.add_parser(
        "control", help="dispatch keyboard and mouse events from JSON lines"
    )
    control.add_argument("--game", choices=_TASK_GAMES, default="redalert")
    control.add_argument("--mission")
    control.add_argument("--seed", type=int, default=0, help=argparse.SUPPRESS)
    control.add_argument("--actions", required=True)
    control.add_argument("--watch", dest="watch", action="store_true", default=False)
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
