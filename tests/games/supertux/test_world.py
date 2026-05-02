from unittest import TestCase

from wargames.games.supertux.world import world_from_frame


class SuperTuxWorldTests(TestCase):
    def test_parses_jsonl_probe_frame(self) -> None:
        world = world_from_frame(
            {
                "tick": 12,
                "mission": {"finished": True, "failed": False},
                "level": {
                    "file": "levels/world1/a.stl",
                    "name": "A",
                    "set": "world1",
                    "coins": 3,
                    "total_coins": 10,
                },
                "player": {
                    "x": 20.5,
                    "y": 100.0,
                    "vx": 4.0,
                    "vy": -1.0,
                    "coins": 3,
                    "bonus": "grow",
                    "alive": True,
                },
            }
        )

        self.assertEqual(world.tick, 12)
        self.assertTrue(world.mission.finished)
        self.assertEqual(world.level.coins, 3)
        self.assertEqual(world.player.bonus, "grow")
