from __future__ import annotations

from unittest import TestCase

from wargames.games.quaver.world import world_from_frame


class QuaverWorldTests(TestCase):
    def test_parses_exported_world_frame(self) -> None:
        world = world_from_frame(
            {
                "tick": 12,
                "mission": {"finished": True, "failed": False},
                "chart": {
                    "map_id": 42,
                    "mapset_id": 4,
                    "title": "Song",
                    "artist": "Artist",
                    "difficulty_name": "Easy",
                    "mode": "Keys4",
                    "key_count": 4,
                    "song_length_ms": 40000,
                    "hit_objects": 100,
                    "long_notes": 5,
                    "mines": 1,
                    "total_judgements": 105,
                },
                "gameplay": {
                    "song_time_ms": 1234.5,
                    "started": True,
                    "paused": False,
                    "completed": True,
                    "failed": False,
                    "health": 98.0,
                    "score": 5000,
                    "accuracy": 99.1,
                    "combo": 10,
                    "max_combo": 20,
                    "total_judgement_count": 15,
                    "stats_count": 15,
                },
                "judgements": {"marv": 8, "perf": 4, "great": 2, "good": 1, "okay": 0, "miss": 0},
            }
        )

        self.assertEqual(12, world.tick)
        self.assertTrue(world.mission.finished)
        self.assertEqual(42, world.chart.map_id)
        self.assertEqual(1.2345, world.gameplay.song_time_seconds)
        self.assertEqual(8, world.judgements.marv)
