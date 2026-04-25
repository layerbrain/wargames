from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass

from wargames.core.errors import DependencyMissing


@dataclass(frozen=True)
class X11StreamViewer:
    display: str
    resolution: tuple[int, int]
    fps: int = 30
    title: str = "WarGames"
    executable: str = "ffplay"
    viewer_display: str | None = None

    def command(self) -> list[str]:
        width, height = self.resolution
        return [
            self.executable,
            "-hide_banner",
            "-loglevel",
            "warning",
            "-fflags",
            "nobuffer",
            "-flags",
            "low_delay",
            "-framedrop",
            "-noborder",
            "-f",
            "x11grab",
            "-draw_mouse",
            "1",
            "-framerate",
            str(self.fps),
            "-video_size",
            f"{width}x{height}",
            "-i",
            self.display,
            "-window_title",
            self.title,
        ]

    def start(self) -> subprocess.Popen[bytes]:
        if shutil.which(self.executable) is None:
            raise DependencyMissing(f"{self.executable} is required to watch the Xvfb stream")
        env = os.environ.copy()
        if self.viewer_display:
            env["DISPLAY"] = self.viewer_display
        return subprocess.Popen(self.command(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)


def stop_stream_viewer(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)
