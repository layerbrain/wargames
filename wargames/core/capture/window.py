from __future__ import annotations

import asyncio
import os
import subprocess
import shutil
from abc import ABC, abstractmethod
from pathlib import Path

from wargames.core.capture.frame import Frame
from wargames.core.control.events import Target
from wargames.core.errors import DependencyMissing


class WindowCapture(ABC):
    @abstractmethod
    async def capture(self, target: Target, *, tick: int) -> Frame: ...


class NullWindowCapture(WindowCapture):
    async def capture(self, target: Target, *, tick: int) -> Frame:
        return Frame(
            id=f"frame-{tick}",
            width=target.rect.width,
            height=target.rect.height,
            captured_tick=tick,
        )


class ScreenRegionCapture(WindowCapture):
    def __init__(self, frame_dir: str) -> None:
        self.frame_dir = Path(frame_dir)

    async def capture(self, target: Target, *, tick: int) -> Frame:
        self.frame_dir.mkdir(parents=True, exist_ok=True)
        path = self.frame_dir / f"frame-{tick}.png"
        await self._capture_linux(target, path)
        await self._normalize_dimensions(target, path)
        return Frame(
            id=f"frame-{tick}",
            width=target.rect.width,
            height=target.rect.height,
            captured_tick=tick,
            image_path=str(path),
        )

    async def _capture_linux(self, target: Target, path: Path) -> None:
        tool = shutil.which("import")
        if tool is None:
            raise DependencyMissing("ImageMagick import is required for Linux Xvfb frame capture")
        env = os.environ.copy()
        if target.display:
            env["DISPLAY"] = target.display
        command = [tool, "-window", "root", str(path)]
        process = await asyncio.create_subprocess_exec(*command, env=env)
        returncode = await process.wait()
        if returncode != 0:
            raise DependencyMissing(f"ImageMagick import failed with exit code {returncode}")

    async def _normalize_dimensions(self, target: Target, path: Path) -> None:
        convert = shutil.which("convert")
        if convert is None:
            return
        await asyncio.to_thread(
            subprocess.run,
            [
                convert,
                str(path),
                "-resize",
                f"{target.rect.width}x{target.rect.height}",
                "-gravity",
                "center",
                "-background",
                "black",
                "-extent",
                f"{target.rect.width}x{target.rect.height}",
                str(path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
