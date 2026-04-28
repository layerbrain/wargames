from unittest import TestCase

from wargames.games.zeroad.world import world_from_state


class ZeroADWorldTests(TestCase):
    def test_parses_rl_world_state(self) -> None:
        world = world_from_state(
            {
                "timeElapsed": 400,
                "mapSize": 256,
                "victoryConditions": ["conquest_units"],
                "players": [
                    {"name": "Gaia", "state": "active"},
                    {
                        "name": "Player 1",
                        "civ": "spart",
                        "state": "active",
                        "team": 1,
                        "popCount": 12,
                        "popLimit": 30,
                        "resourceCounts": {"food": 100, "wood": 250},
                        "statistics": {"enemyUnitsKilled": {"total": 2}},
                    },
                    {"name": "Player 2", "state": "active", "team": 2},
                ],
                "entities": {
                    "10": {
                        "id": 10,
                        "template": "units/spart/infantry_spearman_b",
                        "owner": 1,
                        "position": [12.5, 30.0],
                        "hitpoints": 100,
                    }
                },
            },
            player_id=1,
        )

        self.assertEqual(world.tick, 2)
        self.assertEqual(world.map_size, 256)
        self.assertEqual(world.us.population, 12)
        self.assertEqual(world.us.resources, {"food": 100, "wood": 250})
        self.assertEqual(world.us.enemy_units_killed, 2)
        self.assertEqual(len(world.enemies), 1)
        self.assertEqual(world.entities[0].x, 12.5)

    def test_marks_victory_and_defeat(self) -> None:
        won = world_from_state({"players": [{}, {"state": "won"}]}, player_id=1)
        lost = world_from_state({"players": [{}, {"state": "defeated"}]}, player_id=1)

        self.assertTrue(won.mission.finished)
        self.assertFalse(won.mission.failed)
        self.assertTrue(lost.mission.failed)
