import struct
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wargames.games.doom.missions import (
    discover,
    extract_mission_catalog,
    load_mission_catalog,
    wad_maps,
)


class DoomMissionTests(TestCase):
    def test_reads_map_markers_from_iwad_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            wad = Path(temp_dir) / "freedoom2.wad"
            _write_wad(wad, ("PLAYPAL", "MAP01", "THINGS", "MAP02", "E1M1"))

            self.assertEqual(wad_maps(wad), ("MAP01", "MAP02", "E1M1"))

    def test_exports_freedoom_maps_as_difficulty_variants(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "doom"
            _write_wad(root / "freedoom2.wad", ("MAP01", "THINGS"))

            missions = discover(root)

            self.assertEqual(
                [mission.id for mission in missions],
                [
                    "doom.map.map01.easy",
                    "doom.map.map01.normal",
                    "doom.map.map01.hard",
                ],
            )
            self.assertEqual(missions[0].iwad, str(root / "freedoom2.wad"))
            self.assertEqual(missions[0].skill, 2)
            self.assertEqual(missions[1].skill, 3)
            self.assertIn("freedoom", missions[0].tags)

            written = extract_mission_catalog(root, Path(temp_dir) / "out")
            self.assertEqual(len(written), 3)
            self.assertEqual(len(load_mission_catalog(Path(temp_dir) / "out")), 3)

    def test_extract_does_not_clear_catalog_when_no_iwads_are_found(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "out"
            stale = output / "normal" / "doom.map.map01.normal.json"
            stale.parent.mkdir(parents=True)
            stale.write_text('{"id": "keep"}\n', encoding="utf-8")

            written = extract_mission_catalog(Path(temp_dir) / "missing", output)

            self.assertEqual(written, ())
            self.assertTrue(stale.exists())


def _write_wad(path: Path, names: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = bytearray()
    data.extend(b"IWAD")
    data.extend(struct.pack("<II", len(names), 12))
    for name in names:
        data.extend(struct.pack("<II", 0, 0))
        data.extend(name.encode("ascii")[:8].ljust(8, b"\0"))
    path.write_bytes(bytes(data))
