from unittest import TestCase

from wargames.games.craftium.world import world_from_info


class CraftiumWorldTests(TestCase):
    def test_parses_info_state(self) -> None:
        world = world_from_info(
            {
                "player_pos": [1.0, 2.0, 3.0],
                "player_vel": [0.1, 0.2, 0.3],
                "player_pitch": 10.0,
                "player_yaw": 90.0,
                "voxel_obs": [[[[(1, 0, 0)]]]],
                "mt_dtime": 0.016,
            },
            tick=12,
            reward=1.5,
            total_reward=2.5,
            finished=True,
            failed=False,
            truncated=False,
        )

        self.assertEqual(world.tick, 12)
        self.assertEqual(world.player.position, (1.0, 2.0, 3.0))
        self.assertEqual(world.reward, 1.5)
        self.assertTrue(world.mission.finished)
