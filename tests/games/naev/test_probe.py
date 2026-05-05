from __future__ import annotations

import asyncio
from unittest import TestCase

from wargames.games.naev.probe import StdoutStateProbe


class NaevProbeTests(TestCase):
    def test_probe_filters_stdout_for_state_lines(self) -> None:
        async def run() -> None:
            reader = asyncio.StreamReader()
            probe = StdoutStateProbe(reader)
            await probe.start()
            reader.feed_data(b"Reached main menu\n")
            reader.feed_data(
                b'WARGAMES_STATE {"tick":4,"player":{"system":"Hakoi","credits":30000}}\n'
            )
            snapshot = await asyncio.wait_for(probe.next(), timeout=1)
            await probe.close()
            self.assertEqual(4, snapshot.tick)
            self.assertEqual("Hakoi", snapshot.world.player.system)

        asyncio.run(run())
