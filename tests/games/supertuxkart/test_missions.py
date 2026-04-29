from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wargames.games.supertuxkart.missions import (
    discover,
    extract_mission_catalog,
    load_mission_catalog,
)


class SuperTuxKartMissionTests(TestCase):
    def test_loads_shipped_missions(self) -> None:
        missions = load_mission_catalog("scenarios/supertuxkart/missions")
        self.assertEqual(len(missions), 63)

        by_id = {mission.id: mission for mission in missions}
        mission = by_id["supertuxkart.race.lighthouse.normal"]

        self.assertEqual(mission.track, "lighthouse")
        self.assertEqual(mission.laps, 4)
        self.assertEqual(mission.num_karts, 6)
        self.assertEqual(mission.native_difficulty, "1")
        self.assertIn("race", mission.tags)

    def test_exports_race_tracks_from_supertuxkart_data(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "stk"
            tracks = root / "data" / "tracks"
            _track(tracks, "lighthouse", "Around the Lighthouse", laps=4)
            _track(tracks, "soccer_field", "Soccer Field", soccer=True)
            _track(tracks, "battleisland", "Battle Island", arena=True)
            _track(tracks, "introcutscene", "Intro", internal=True)

            missions = discover(root)

            self.assertEqual(
                [mission.id for mission in missions],
                [
                    "supertuxkart.race.lighthouse.easy",
                    "supertuxkart.race.lighthouse.normal",
                    "supertuxkart.race.lighthouse.hard",
                ],
            )

            written = extract_mission_catalog(root, Path(temp_dir) / "out")
            self.assertEqual(len(written), 3)
            exported = load_mission_catalog(Path(temp_dir) / "out")
            self.assertEqual(len(exported), 3)

    def test_extract_does_not_clear_catalog_when_no_tracks_are_found(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "out"
            stale = output / "normal" / "supertuxkart.race.lighthouse.normal.json"
            stale.parent.mkdir(parents=True)
            stale.write_text('{"id": "keep"}\n', encoding="utf-8")

            written = extract_mission_catalog(Path(temp_dir) / "missing", output)

            self.assertEqual(written, ())
            self.assertTrue(stale.exists())


def _track(
    tracks: Path,
    id: str,
    title: str,
    *,
    laps: int = 3,
    internal: bool = False,
    arena: bool = False,
    soccer: bool = False,
) -> None:
    path = tracks / id
    path.mkdir(parents=True)
    path.joinpath("track.xml").write_text(
        f"""
        <track
          name="{title}"
          groups="standard"
          default-number-of-laps="{laps}"
          internal="{"Y" if internal else "N"}"
          arena="{"Y" if arena else "N"}"
          soccer="{"Y" if soccer else "N"}"
        />
        """,
        encoding="utf-8",
    )
