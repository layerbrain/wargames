import msgpack
from unittest import TestCase

from wargames.games.redalert.probe import decode_frame


class RedAlertProbeFormatTests(TestCase):
    def test_msgpack_frame_decodes_to_typed_world(self) -> None:
        payload = msgpack.packb(
            {
                "v": 1,
                "tick": 123,
                "us": {"id": "p1", "cash": 3400},
                "enemy": {"id": "p2"},
                "units": [],
                "buildings": [],
                "resources": [],
                "mission": {"elapsed_ticks": 123, "objectives": [{"id": "o1", "description": "Scout"}]},
            },
            use_bin_type=True,
        )
        snapshot = decode_frame(payload)
        self.assertEqual(snapshot.tick, 123)
        self.assertEqual(snapshot.world.us.cash, 3400)
        self.assertEqual(snapshot.world.mission.objectives[0].id, "o1")
