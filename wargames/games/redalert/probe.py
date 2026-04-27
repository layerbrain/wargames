from __future__ import annotations

import asyncio
import os
import struct
from pathlib import Path
from typing import Any

import msgpack

from wargames.core.errors import ProbeError
from wargames.core.world.probe import HiddenStateSnapshot, StateProbe
from wargames.games.redalert.world import world_from_frame


def decode_frame(payload: bytes) -> HiddenStateSnapshot:
    data: dict[str, Any] = msgpack.unpackb(payload, raw=False)
    world = world_from_frame(data)
    return HiddenStateSnapshot(tick=world.tick, world=world)


class SocketStateProbe(StateProbe):
    def __init__(self, socket_path: str) -> None:
        self.socket_path = socket_path
        self._server: asyncio.AbstractServer | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._latest: HiddenStateSnapshot | None = None
        self._updated = asyncio.Condition()
        self._reader_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        path = Path(self.socket_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        self._server = await asyncio.start_unix_server(self._accept, path=self.socket_path)

    async def _accept(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer
        self._reader_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        assert self._reader is not None
        while True:
            try:
                prefix = await self._reader.readexactly(4)
                length = struct.unpack(">I", prefix)[0]
                payload = await self._reader.readexactly(length)
            except asyncio.IncompleteReadError:
                return
            snapshot = decode_frame(payload)
            async with self._updated:
                self._latest = snapshot
                self._updated.notify_all()

    async def wait_connected(self, timeout: float) -> None:
        deadline = asyncio.get_running_loop().time() + timeout
        while self._reader is None:
            if asyncio.get_running_loop().time() >= deadline:
                raise ProbeError("probe socket was not connected before timeout")
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
        if self._reader_task is not None:
            self._reader_task.cancel()
        if self._writer is not None:
            self._writer.close()
            await self._writer.wait_closed()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        try:
            os.unlink(self.socket_path)
        except FileNotFoundError:
            pass
