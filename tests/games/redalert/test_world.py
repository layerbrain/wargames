from unittest import TestCase

from wargames.games.redalert.world import world_from_frame


class RedAlertWorldTests(TestCase):
    def test_decodes_nested_owner_objects(self) -> None:
        world = world_from_frame(
            {
                "tick": 1,
                "us": {"id": "p1", "cash": 100},
                "enemy": {"id": "p2"},
                "units": [{"id": "u1", "type": "e1", "owner": "us", "x": 1, "y": 2}],
                "buildings": [],
                "resources": [],
                "mission": {"elapsed_ticks": 1, "objectives": []},
            }
        )
        self.assertEqual(world.us.cash, 100)
        self.assertEqual(world.units[0].owner.id, "p1")
