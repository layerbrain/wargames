from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from unittest import TestCase

from wargames.games.quaver.missions import discover, extract_mission_catalog, load_mission_catalog


class QuaverMissionTests(TestCase):
    def test_discovers_each_shipped_chart_as_one_mission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            default_maps = root / "Quaver.Resources" / "Quaver.Resources" / "DefaultMaps"
            default_maps.mkdir(parents=True)
            with zipfile.ZipFile(default_maps / "sample.qp", "w") as archive:
                archive.writestr("easy.qua", _qua(map_id=10, notes=8, spacing=800))
                archive.writestr("hard.qua", _qua(map_id=11, notes=80, spacing=100))

            missions = discover(root)

        self.assertEqual(2, len(missions))
        self.assertEqual({"easy", "hard"}, {mission.difficulty for mission in missions})
        self.assertEqual({10, 11}, {mission.map_id for mission in missions})
        self.assertTrue(all(mission.map_path.endswith(".qua") for mission in missions))
        self.assertTrue(all("sample.qp" in mission.map_path for mission in missions))

    def test_catalog_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            default_maps = root / "Quaver.Resources" / "Quaver.Resources" / "DefaultMaps"
            output = root / "catalog"
            default_maps.mkdir(parents=True)
            with zipfile.ZipFile(default_maps / "sample.qp", "w") as archive:
                archive.writestr("chart.qua", _qua(map_id=22, notes=24, spacing=250))

            written = extract_mission_catalog(root, output)
            loaded = load_mission_catalog(output)

        self.assertEqual(1, len(written))
        self.assertEqual(1, len(loaded))
        self.assertEqual("quaver", loaded[0].game)
        self.assertEqual("Keys4", loaded[0].mode)
        self.assertEqual(4, loaded[0].key_count)


def _qua(*, map_id: int, notes: int, spacing: int) -> str:
    objects = "\n".join(
        f"- StartTime: {index * spacing}\n  Lane: {(index % 4) + 1}\n  KeySounds: []"
        for index in range(notes)
    )
    return "\n".join(
        [
            "AudioFile: audio.mp3",
            f"MapId: {map_id}",
            "MapSetId: 1",
            "Mode: Keys4",
            "Title: Test Song",
            "Artist: Test Artist",
            "DifficultyName: Test",
            "HitObjects:",
            objects,
            "",
        ]
    )
