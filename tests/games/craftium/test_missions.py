from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wargames.games.craftium.missions import (
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)


class CraftiumMissionTests(TestCase):
    def test_exports_upstream_single_agent_tasks_with_difficulties(self) -> None:
        missions = discover()

        self.assertEqual(len(missions), 96)
        self.assertEqual(missions[0].id, "craftium.room.easy")
        self.assertEqual(missions[0].env_id, "Craftium/Room-v0")
        self.assertIn("forward", missions[0].action_names)
        self.assertIn(
            "craftium.crl.sequence0-25.task-24.hard",
            {mission.id for mission in missions},
        )

    def test_difficulty_variants_use_stricter_time_budgets(self) -> None:
        missions = {mission.id: mission for mission in discover()}

        self.assertGreater(
            missions["craftium.room.easy"].time_limit_ticks,
            missions["craftium.room.normal"].time_limit_ticks,
        )
        self.assertGreater(
            missions["craftium.room.normal"].time_limit_ticks,
            missions["craftium.room.hard"].time_limit_ticks,
        )
        self.assertGreater(
            missions["craftium.crl.sequence0-25.task-00.easy"].time_limit_ticks,
            missions["craftium.crl.sequence0-25.task-00.normal"].time_limit_ticks,
        )
        self.assertGreater(
            missions["craftium.crl.sequence0-25.task-00.normal"].time_limit_ticks,
            missions["craftium.crl.sequence0-25.task-00.hard"].time_limit_ticks,
        )

    def test_catalog_round_trip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            written = extract_mission_catalog(None, Path(temp_dir) / "out")

            self.assertEqual(len(written), 96)
            self.assertEqual(len(load_mission_catalog(Path(temp_dir) / "out")), 96)

    def test_sequence_task_count_can_be_extracted_from_craftium_root(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sequence = root / "craftium" / "extra" / "sequence0_25"
            sequence.parent.mkdir(parents=True)
            sequence.write_text("map-0=map-1", encoding="utf-8")

            missions = discover(root)

        self.assertEqual(len(missions), 27)
        self.assertIn("craftium.crl.sequence0-25.task-01.normal", {m.id for m in missions})
