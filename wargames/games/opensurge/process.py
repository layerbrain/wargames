from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from pathlib import Path

from wargames.core.errors import GameNotInstalled
from wargames.games.opensurge.config import OpenSurgeConfig
from wargames.games.opensurge.missions import OpenSurgeMissionSpec


def locate_opensurge(config: OpenSurgeConfig) -> str:
    candidates = [
        config.binary,
        os.getenv("OPENSURGE_BINARY"),
        _cache_binary(),
        str(Path(config.root) / "opensurge") if config.root else None,
        str(Path(config.root) / "build" / "opensurge") if config.root else None,
        str(Path(config.root) / "cmake_build" / "opensurge") if config.root else None,
        str(Path(config.root) / "bin" / "opensurge") if config.root else None,
        shutil.which("opensurge"),
        "/usr/games/opensurge",
        "/usr/bin/opensurge",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise GameNotInstalled("Open Surge binary was not found in its Docker runtime")


def locate_data_dir(config: OpenSurgeConfig, mission: OpenSurgeMissionSpec | None = None) -> str:
    candidates = [
        mission.data_dir if mission is not None else None,
        config.data_dir,
        config.root,
        _cache_root(),
        str(Path(config.root) / "data") if config.root else None,
        str(Path(config.root) / "share" / "games" / "opensurge") if config.root else None,
        "/usr/share/games/opensurge",
    ]
    for candidate in candidates:
        if candidate and (Path(candidate) / "levels").exists():
            return candidate
    raise GameNotInstalled("Open Surge data directory was not found in its Docker runtime")


def locate_level_file(config: OpenSurgeConfig, mission: OpenSurgeMissionSpec) -> str:
    raw = Path(mission.level_file)
    if raw.is_absolute() and raw.exists():
        return str(raw)
    candidate = Path(locate_data_dir(config, mission)) / raw
    if candidate.exists():
        return str(candidate)
    raise GameNotInstalled(f"Open Surge level file was not found: {mission.level_file}")


def opensurge_environment(
    config: OpenSurgeConfig,
    *,
    state_path: str,
    audio_path: str | None = None,
    display: str | None = None,
) -> Mapping[str, str]:
    env: dict[str, str] = {
        "LIBGL_ALWAYS_SOFTWARE": "1",
        "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS": "0",
        "ALSA_CONFIG_PATH": _alsa_config(audio_path),
        "WARGAMES_OPENSURGE_STATE_PATH": state_path,
        "WARGAMES_OPENSURGE_STATE_INTERVAL_TICKS": str(config.state_interval_ticks),
    }
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if cache_dir:
        root = Path(cache_dir).expanduser() / "games" / "opensurge"
        env["HOME"] = str(root / "home")
        env["XDG_CACHE_HOME"] = str(root / "xdg-cache")
        env["XDG_CONFIG_HOME"] = str(root / "xdg-config")
        env["XDG_DATA_HOME"] = str(root / "xdg-data")
    if display:
        env["DISPLAY"] = display
    return env


def bootstrap_opensurge(config: OpenSurgeConfig) -> None:
    binary = Path(locate_opensurge(config))
    if not binary.exists():
        raise GameNotInstalled(f"Open Surge binary was not found: {binary}")
    locate_data_dir(config)


def opensurge_command(
    binary: str, mission: OpenSurgeMissionSpec, config: OpenSurgeConfig, *, seed: int
) -> list[str]:
    del seed
    return [
        binary,
        "--windowed",
        "--resolution",
        _resolution_scale(config.window_size),
        "--hide-fps",
        "--game-folder",
        locate_data_dir(config, mission),
        "--level",
        _level_argument(config, mission),
    ]


def _resolution_scale(window_size: tuple[int, int]) -> str:
    width, height = window_size
    return str(max(1, min(4, min(width // 320, height // 240))))


def _level_argument(config: OpenSurgeConfig, mission: OpenSurgeMissionSpec) -> str:
    raw = Path(mission.level_file)
    if not raw.is_absolute():
        locate_level_file(config, mission)
        return mission.level_file
    data_dir = Path(locate_data_dir(config, mission))
    try:
        return str(raw.relative_to(data_dir))
    except ValueError as exc:
        raise GameNotInstalled(
            f"Open Surge level file must be inside the game data directory: {mission.level_file}"
        ) from exc


def _alsa_config(audio_path: str | None) -> str:
    suffix = Path(audio_path).stem if audio_path else "null"
    path = Path("/tmp/wargames") / "asound" / f"opensurge-{suffix}.conf"
    path.parent.mkdir(parents=True, exist_ok=True)
    if audio_path is None:
        path.write_text(
            "\n".join(
                [
                    "pcm.!default { type null }",
                    "ctl.!default { type hw card 0 }",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return str(path)
    Path(audio_path).parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "pcm.wargames_sink { type null }",
                "pcm.wargames_capture {",
                "  type file",
                "  slave.pcm wargames_sink",
                f"  file \"{audio_path}\"",
                "  format raw",
                "}",
                "pcm.!default {",
                "  type plug",
                "  slave {",
                "    pcm wargames_capture",
                "    rate 48000",
                "    channels 2",
                "    format S16_LE",
                "  }",
                "}",
                "ctl.!default { type hw card 0 }",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return str(path)


def _cache_binary() -> str | None:
    root = _cache_root()
    return str(root / "opensurge") if root else None


def _cache_root() -> Path | None:
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if not cache_dir:
        return None
    return Path(cache_dir) / "games" / "opensurge" / "opensurge"
