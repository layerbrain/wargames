from __future__ import annotations

from unittest import TestCase

from wargames.games.naev.world import world_from_frame


class NaevWorldTests(TestCase):
    def test_world_from_exporter_frame(self) -> None:
        world = world_from_frame(
            {
                "tick": 12,
                "mission": {"finished": True, "completed_count": 1, "last_completed": "Cargo"},
                "player": {
                    "system": "Hakoi",
                    "landed": False,
                    "credits": 31_000,
                    "wealth": 32_000,
                    "fuel": 490,
                    "armour": 80,
                    "shield": 60,
                    "target": "Pirate",
                    "target_distance": 1200,
                },
                "navigation": {"system": "Hakoi", "jumps_available": 2},
            }
        )

        self.assertEqual(12, world.tick)
        self.assertTrue(world.mission.finished)
        self.assertEqual(1, world.mission.completed_count)
        self.assertEqual("Hakoi", world.player.system)
        self.assertEqual(31_000, world.player.credits)
        self.assertEqual(2, world.navigation.jumps_available)
