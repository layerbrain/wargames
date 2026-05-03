from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from pathlib import Path

from wargames.core.errors import GameNotInstalled
from wargames.games.quaver.config import QuaverConfig
from wargames.games.quaver.missions import QuaverMissionSpec


def locate_quaver(config: QuaverConfig) -> str:
    candidates = [
        config.binary,
        os.getenv("QUAVER_BINARY"),
        _cache_binary(),
        str(Path(config.runtime_root) / "Quaver") if config.runtime_root else None,
        str(Path(config.root) / "Quaver" / "bin" / "Release" / "net6.0" / "Quaver")
        if config.root
        else None,
        str(Path(config.root) / "Quaver" / "bin" / "Debug" / "net6.0" / "Quaver")
        if config.root
        else None,
        str(Path(config.root) / "Quaver") if config.root and Path(config.root).is_file() else None,
        shutil.which("Quaver"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise GameNotInstalled("Quaver binary was not found in its Docker runtime")


def locate_runtime_root(config: QuaverConfig) -> Path:
    if config.runtime_root and (Path(config.runtime_root) / "Quaver.Shared.dll").exists():
        return Path(config.runtime_root)
    binary = Path(locate_quaver(config))
    if (binary.parent / "Quaver.Shared.dll").exists():
        return binary.parent
    raise GameNotInstalled("Quaver runtime directory was not found in its Docker runtime")


def locate_default_maps_dir(config: QuaverConfig) -> str:
    candidates = [
        config.default_maps_dir,
        str(Path(config.root) / "Quaver.Resources" / "Quaver.Resources" / "DefaultMaps")
        if config.root
        else None,
        str(_cache_source_root() / "Quaver.Resources" / "Quaver.Resources" / "DefaultMaps")
        if _cache_source_root()
        else None,
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists() and any(Path(candidate).glob("*.qp")):
            return candidate
    raise GameNotInstalled("Quaver default map archives were not found in its Docker runtime")


def quaver_environment(
    config: QuaverConfig,
    mission: QuaverMissionSpec,
    *,
    state_path: str,
    audio_path: str | None = None,
    display: str | None = None,
) -> Mapping[str, str]:
    runtime_root = locate_runtime_root(config)
    env: dict[str, str] = {
        "ALSA_CONFIG_PATH": _alsa_config(audio_path),
        "ALSOFT_DRIVERS": "alsa",
        "DOTNET_BUNDLE_EXTRACT_BASE_DIR": "/tmp/wargames/quaver-dotnet",
        "FNA3D_FORCE_DRIVER": "OpenGL",
        "LD_LIBRARY_PATH": _library_path(runtime_root),
        "LIBGL_ALWAYS_SOFTWARE": "1",
        "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS": "0",
        "WARGAMES_QUAVER_AUTOPLAY": "1",
        "WARGAMES_QUAVER_DISABLE_STEAM": "1",
        "WARGAMES_QUAVER_MAP_ID": str(mission.map_id),
        "WARGAMES_QUAVER_MAP_PATH": mission.map_path,
        "WARGAMES_QUAVER_STATE_INTERVAL_TICKS": str(config.state_interval_ticks),
        "WARGAMES_QUAVER_STATE_PATH": state_path,
    }
    root = _cache_runtime_home()
    if root is not None:
        for key, child in {
            "HOME": "home",
            "XDG_CACHE_HOME": "xdg-cache",
            "XDG_CONFIG_HOME": "xdg-config",
            "XDG_DATA_HOME": "xdg-data",
        }.items():
            path = root / child
            path.mkdir(parents=True, exist_ok=True)
            env[key] = str(path)
        (root / "xdg-data" / "applications").mkdir(parents=True, exist_ok=True)
    if display:
        env["DISPLAY"] = display
    return env


def bootstrap_quaver(config: QuaverConfig) -> None:
    binary = Path(locate_quaver(config))
    if not binary.exists():
        raise GameNotInstalled(f"Quaver binary was not found: {binary}")
    locate_runtime_root(config)


def quaver_command(binary: str, mission: QuaverMissionSpec, config: QuaverConfig) -> list[str]:
    del mission, config
    return [binary]


def _library_path(runtime_root: Path) -> str:
    paths = [runtime_root, runtime_root / "x64"]
    existing = [str(path) for path in paths if path.exists()]
    current = os.getenv("LD_LIBRARY_PATH")
    if current:
        existing.append(current)
    return ":".join(existing)


def _alsa_config(audio_path: str | None) -> str:
    suffix = Path(audio_path).stem if audio_path else "null"
    path = Path("/tmp/wargames") / "asound" / f"quaver-{suffix}.conf"
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
    root = _cache_source_root()
    if root is None:
        return None
    return str(root / "Quaver" / "bin" / "Release" / "net6.0" / "Quaver")


def _cache_source_root() -> Path | None:
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if not cache_dir:
        return None
    return Path(cache_dir) / "games" / "quaver" / "quaver"


def _cache_runtime_home() -> Path | None:
    cache_dir = os.getenv("LAYERBRAIN_WARGAMES_CACHE_DIR")
    if not cache_dir:
        return None
    return Path(cache_dir) / "games" / "quaver" / "runtime"
