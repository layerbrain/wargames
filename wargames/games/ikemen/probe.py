from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from wargames.core.world.probe import HiddenStateSnapshot, StateProbe
from wargames.games.ikemen.world import world_from_frame


def decode_line(line: str) -> HiddenStateSnapshot:
    data: dict[str, Any] = json.loads(line)
    world = world_from_frame(data)
    return HiddenStateSnapshot(tick=world.tick, world=world)


class JsonlStateProbe(StateProbe):
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._latest: HiddenStateSnapshot | None = None
        self._updated = asyncio.Condition()
        self._reader_task: asyncio.Task[None] | None = None
        self._closed = False

    async def start(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.unlink(missing_ok=True)
        self._reader_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        offset = 0
        while not self._closed:
            if self.path.exists():
                with self.path.open("r", encoding="utf-8") as handle:
                    handle.seek(offset)
                    while line := handle.readline():
                        offset = handle.tell()
                        line = line.strip()
                        if not line:
                            continue
                        snapshot = decode_line(line)
                        async with self._updated:
                            self._latest = snapshot
                            self._updated.notify_all()
                    offset = handle.tell()
            await asyncio.sleep(0.02)

    async def next(self) -> HiddenStateSnapshot:
        async with self._updated:
            await self._updated.wait_for(lambda: self._latest is not None)
            assert self._latest is not None
            return self._latest

    async def next_after(self, tick: int) -> HiddenStateSnapshot:
        async with self._updated:
            await self._updated.wait_for(
                lambda: self._latest is not None and self._latest.tick > tick
            )
            assert self._latest is not None
            return self._latest

    async def latest(self) -> HiddenStateSnapshot | None:
        return self._latest

    async def close(self) -> None:
        self._closed = True
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
