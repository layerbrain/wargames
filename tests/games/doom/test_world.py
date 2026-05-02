from unittest import TestCase

from wargames.games.doom.probe import decode_line
from wargames.games.doom.world import world_from_frame


class DoomWorldTests(TestCase):
    def test_decodes_exported_frame_shape(self) -> None:
        world = world_from_frame(
            {
                "tick": 42,
                "mission": {"finished": False, "failed": False},
                "level": {
                    "map": "MAP01",
                    "episode": None,
                    "map_number": 1,
                    "skill": 3,
                    "elapsed_ticks": 42,
                    "kills": 2,
                    "total_kills": 11,
                    "items": 1,
                    "total_items": 5,
                    "secrets": 0,
                    "total_secrets": 3,
                },
                "player": {
                    "x": 128.5,
                    "y": 64.0,
                    "angle": 90.0,
                    "health": 93,
                    "armor": 12,
                    "ammo": [44, 0, 0, 0],
                    "weapons": [True, True, False],
                    "keys": [False, True],
                    "damage_taken": 7,
                    "dead": False,
                },
            }
        )

        self.assertEqual(world.tick, 42)
        self.assertEqual(world.level.map, "MAP01")
        self.assertEqual(world.level.kills, 2)
        self.assertEqual(world.player.x, 128.5)
        self.assertEqual(world.player.ammo, (44, 0, 0, 0))
        self.assertEqual(world.player.weapons, (True, True, False))
        self.assertEqual(world.player.keys, (False, True))

    def test_probe_line_uses_world_tick(self) -> None:
        snapshot = decode_line(
            '{"tick": 9, "level": {"map": "MAP01"}, "player": {"health": 100}}'
        )

        self.assertEqual(snapshot.tick, 9)
        self.assertEqual(snapshot.world.level.map, "MAP01")
