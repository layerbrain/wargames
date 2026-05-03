from __future__ import annotations

import asyncio
import json
from typing import Any

from wargames.core.world.probe import HiddenStateSnapshot, StateProbe
from wargames.games.naev.world import world_from_frame

STATE_PREFIX = "WARGAMES_STATE "


def decode_line(line: str) -> HiddenStateSnapshot:
    data: dict[str, Any] = json.loads(line)
    world = world_from_frame(data)
    return HiddenStateSnapshot(tick=world.tick, world=world)


class StdoutStateProbe(StateProbe):
    def __init__(self, reader: asyncio.StreamReader) -> None:
        self.reader = reader
        self._latest: HiddenStateSnapshot | None = None
        self._tail: list[str] = []
        self._updated = asyncio.Condition()
        self._reader_task: asyncio.Task[None] | None = None
        self._closed = False

    async def start(self) -> None:
        self._reader_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        while not self._closed:
            line = await self.reader.readline()
            if not line:
                return
            text = line.decode("utf-8", errors="replace").strip()
            async with self._updated:
                self._tail.append(text)
                if len(self._tail) > 80:
                    self._tail.pop(0)
                self._updated.notify_all()
            if not text.startswith(STATE_PREFIX):
                continue
            try:
                snapshot = decode_line(text[len(STATE_PREFIX) :])
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            async with self._updated:
                self._latest = snapshot
                self._updated.notify_all()

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

    def log_tail(self) -> tuple[str, ...]:
        return tuple(self._tail)

    async def wait_for_log(self, pattern: str) -> None:
        async with self._updated:
            await self._updated.wait_for(lambda: any(pattern in line for line in self._tail))

    async def close(self) -> None:
        self._closed = True
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
