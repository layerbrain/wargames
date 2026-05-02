from unittest import TestCase

from wargames.games.ikemen.world import world_from_frame


class IkemenWorldTests(TestCase):
    def test_parses_lua_state_frame(self) -> None:
        world = world_from_frame(
            {
                "tick": 60,
                "mission": {"finished": False, "failed": False},
                "match": {"round_state": 2, "round_no": 1, "fight_time": 10},
                "players": [
                    {"slot": 1, "exists": True, "name": "kfm", "life": 900, "power": 300},
                    {"slot": 2, "exists": True, "name": "kfmZ", "life": 700, "power": 100},
                ],
            }
        )

        self.assertEqual(world.tick, 60)
        self.assertEqual(world.match.round_state, 2)
        self.assertEqual(world.p1.life, 900)
        self.assertEqual(world.p2.name, "kfmZ")
