from __future__ import annotations

from unittest import TestCase

from wargames.games.opensurge.world import world_from_frame


class OpenSurgeWorldTests(TestCase):
    def test_parses_jsonl_state_frame(self) -> None:
        world = world_from_frame(
            {
                "tick": 42,
                "mission": {"finished": True, "failed": False},
                "level": {
                    "file": "levels/sunshine-1.lev",
                    "name": "Sunshine Paradise",
                    "act": 1,
                    "elapsed_ticks": 42,
                    "elapsed_seconds": 0.7,
                    "width": 17920,
                    "height": 10752,
                    "target_time_seconds": 81,
                },
                "player": {
                    "x": 207.5,
                    "y": 9920.0,
                    "xsp": 1.0,
                    "ysp": 2.0,
                    "gsp": 3.0,
                    "speed": 4.0,
                    "rings": 5,
                    "score": 100,
                    "lives": 4,
                    "alive": True,
                    "dying": False,
                    "winning": True,
                    "rolling": False,
                    "jumping": True,
                },
            }
        )

        self.assertTrue(world.mission.finished)
        self.assertEqual("Sunshine Paradise", world.level.name)
        self.assertEqual(207.5, world.player.x)
        self.assertEqual(5, world.player.rings)
        self.assertTrue(world.player.jumping)
