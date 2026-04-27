import asyncio
import socket
import struct
import tempfile
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase

import msgpack

from wargames.games.redalert.probe import SocketStateProbe


def _payload(tick: int) -> bytes:
    return msgpack.packb(
        {
            "v": 1,
            "tick": tick,
            "us": {"id": "p1", "cash": 1},
            "enemy": {"id": "p2"},
            "units": [],
            "buildings": [],
            "resources": [],
            "mission": {"elapsed_ticks": tick, "objectives": []},
        },
        use_bin_type=True,
    )


class RedAlertProbeTests(TestCase):
    def test_probe_tracks_socket_path(self) -> None:
        self.assertEqual(
            SocketStateProbe("/tmp/wargames-test.sock").socket_path, "/tmp/wargames-test.sock"
        )


class RedAlertSocketProbeTests(IsolatedAsyncioTestCase):
    async def test_reads_length_prefixed_msgpack_frame(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "probe.sock")
            probe = SocketStateProbe(path)
            await probe.start()

            payload = _payload(9)

            def send() -> None:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.connect(path)
                    client.sendall(struct.pack(">I", len(payload)) + payload)

            await asyncio.to_thread(send)
            snapshot = await asyncio.wait_for(probe.next(), timeout=1)
            self.assertEqual(snapshot.tick, 9)
            await probe.close()

    async def test_next_after_skips_stale_queued_frames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "probe.sock")
            probe = SocketStateProbe(path)
            await probe.start()

            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.connect(path)

                def send(tick: int) -> None:
                    payload = _payload(tick)
                    client.sendall(struct.pack(">I", len(payload)) + payload)

                await asyncio.to_thread(send, 1)
                await asyncio.to_thread(send, 2)
                while (latest := await probe.latest()) is None or latest.tick < 2:
                    await asyncio.sleep(0.01)

                waiter = asyncio.create_task(probe.next_after(2))
                await asyncio.sleep(0.01)
                self.assertFalse(waiter.done())

                await asyncio.to_thread(send, 3)
                snapshot = await asyncio.wait_for(waiter, timeout=1)
                self.assertEqual(snapshot.tick, 3)
            await probe.close()
