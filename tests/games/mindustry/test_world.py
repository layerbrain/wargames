from unittest import TestCase

from wargames.games.mindustry.world import world_from_frame


class MindustryWorldTests(TestCase):
    def test_parses_plugin_frame(self) -> None:
        world = world_from_frame(
            {
                "tick": 60,
                "mission": {"finished": False, "failed": False},
                "game": {"map": "Veins", "wave": 3, "enemies": 7, "tick": 60},
                "teams": [
                    {
                        "id": 1,
                        "name": "sharded",
                        "cores": 1,
                        "units": 2,
                        "buildings": 15,
                        "items": 120,
                        "core_health": 1100.0,
                    },
                    {"id": 2, "name": "crux", "cores": 1},
                ],
            }
        )

        self.assertEqual(world.game.wave, 3)
        self.assertEqual(world.us.items, 120)
        self.assertEqual(len(world.enemies), 1)
