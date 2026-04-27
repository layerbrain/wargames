from __future__ import annotations

import os
import shutil
from pathlib import Path
from collections.abc import Mapping

from wargames.core.errors import GameNotInstalled, ProbeNotInstalled
from wargames.games.redalert.config import RedAlertConfig
from wargames.games.redalert.missions import RedAlertMissionSpec


def locate_openra(config: RedAlertConfig) -> str:
    candidates = [
        config.openra_binary,
        os.getenv("OPENRA_BINARY"),
        shutil.which("openra"),
        "/usr/local/bin/openra",
        "/usr/bin/openra",
        "/usr/games/openra",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise GameNotInstalled("OpenRA binary was not found")


def openra_engine_dir(binary: str, config: RedAlertConfig) -> str | None:
    if config.openra_root:
        return str(Path(config.openra_root))
    path = Path(binary).resolve()
    if path.parent.name == "bin" and (path.parent.parent / "mods").exists():
        return str(path.parent.parent)
    return None


def openra_dotnet_root(config: RedAlertConfig) -> str | None:
    candidates = [
        config.dotnet_root,
        os.getenv("DOTNET_ROOT"),
        str(Path(config.openra_root).parent / ".dotnet") if config.openra_root else None,
    ]
    for candidate in candidates:
        if candidate and (Path(candidate) / "dotnet").exists():
            return candidate
    return None


def openra_environment(
    config: RedAlertConfig, *, probe_socket: str | None = None, display: str | None = None
) -> Mapping[str, str]:
    env: dict[str, str] = {
        "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS": "0",
    }
    if probe_socket:
        env["PROBE_SOCK"] = probe_socket
    if display:
        env["DISPLAY"] = display
    dotnet_root = openra_dotnet_root(config)
    if dotnet_root:
        env["DOTNET_ROOT"] = dotnet_root
        env["PATH"] = f"{dotnet_root}{os.pathsep}{os.environ.get('PATH', '')}"
    return env


def bootstrap_openra(config: RedAlertConfig) -> None:
    binary = Path(locate_openra(config))
    if not binary.exists():
        raise GameNotInstalled(f"OpenRA binary was not found: {binary}")
    if (
        config.openra_root
        and not (Path(config.openra_root) / "mods" / config.openra_mod / "mod.yaml").exists()
    ):
        raise GameNotInstalled(
            f"OpenRA mod '{config.openra_mod}' was not found under {config.openra_root}"
        )
    if config.openra_support_dir:
        Path(config.openra_support_dir).mkdir(parents=True, exist_ok=True)


def verify_probe_installed(config: RedAlertConfig) -> None:
    if not config.openra_root:
        raise ProbeNotInstalled(
            "LAYERBRAIN_WARGAMES_REDALERT_OPENRA_ROOT is required for the probe build"
        )
    root = Path(config.openra_root)
    source = (
        root / "OpenRA.Mods.Common" / "Traits" / "World" / "WarGames" / "WarGamesStateExport.cs"
    )
    rules = root / "mods" / "ra" / "rules" / "wargames-state-export.yaml"
    assembly = root / "bin" / "OpenRA.Mods.Common.dll"
    missing = [str(path) for path in (source, rules, assembly) if not path.exists()]
    if missing:
        raise ProbeNotInstalled("missing WarGames probe install files: " + ", ".join(missing))


def openra_command(binary: str, mission: RedAlertMissionSpec, config: RedAlertConfig) -> list[str]:
    width, height = config.openra_window_size
    command = [binary]
    engine_dir = openra_engine_dir(binary, config)
    if engine_dir:
        command.append(f"Engine.EngineDir={engine_dir}")
    command.extend(
        [
            f"Game.Mod={config.openra_mod}",
            f"Launch.Map={mission.map}",
            "Graphics.Mode=Windowed",
            f"Graphics.FullscreenSize={width},{height}",
            f"Graphics.WindowedSize={width},{height}",
            "Game.LockMouseWindow=False",
            "Game.ViewportEdgeScroll=False",
            "Game.MouseScroll=Disabled",
        ]
    )
    if config.openra_support_dir:
        command.append(f"Engine.SupportDir={config.openra_support_dir}")
    return command
