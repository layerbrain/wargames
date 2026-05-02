from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from wargames.games.doom.config import DoomConfig
from wargames.games.doom.missions import DoomMissionSpec
from wargames.games.doom.process import doom_command, doom_environment, locate_doom


class DoomProcessTests(TestCase):
    def test_locate_binary_from_registered_source_root(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "build" / "src" / "chocolate-doom"
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

            self.assertEqual(locate_doom(DoomConfig(root=str(root))), str(binary))

    def test_command_starts_windowed_freedoom_map(self) -> None:
        with TemporaryDirectory() as temp_dir:
            iwad = Path(temp_dir) / "freedoom2.wad"
            iwad.write_bytes(b"IWAD\0\0\0\0\0\0\0\0")
            mission = DoomMissionSpec(
                id="doom.map.map01.normal",
                title="MAP01",
                game="doom",
                source="builtin",
                iwad=str(iwad),
                map="MAP01",
                skill=3,
                map_number=1,
            )

            command = doom_command(
                "/usr/games/chocolate-doom",
                mission,
                DoomConfig(window_size=(1024, 768)),
                seed=7,
            )

        self.assertIn("-iwad", command)
        self.assertIn(str(iwad), command)
        self.assertIn("-skill", command)
        self.assertIn("3", command)
        self.assertIn("-geometry", command)
        self.assertIn("1024x768", command)
        self.assertIn("-nosound", command)
        self.assertIn("-nomusic", command)
        self.assertEqual(command[-2:], ["-warp", "1"])

    def test_episode_command_uses_two_argument_warp(self) -> None:
        with TemporaryDirectory() as temp_dir:
            iwad = Path(temp_dir) / "freedoom1.wad"
            iwad.write_bytes(b"IWAD\0\0\0\0\0\0\0\0")
            mission = DoomMissionSpec(
                id="doom.episode.e1m2.normal",
                title="E1M2",
                game="doom",
                source="builtin",
                iwad=str(iwad),
                map="E1M2",
                episode=1,
                map_number=2,
            )

            command = doom_command("/usr/games/chocolate-doom", mission, DoomConfig(), seed=1)

        self.assertEqual(command[-3:], ["-warp", "1", "2"])

    def test_environment_keeps_state_inside_runtime_cache(self) -> None:
        with patch.dict(
            "os.environ", {"LAYERBRAIN_WARGAMES_CACHE_DIR": "/opt/wargames-cache"}, clear=True
        ):
            env = doom_environment(DoomConfig(), state_path="/tmp/doom.jsonl", display=":99")

        self.assertEqual(env["DISPLAY"], ":99")
        self.assertEqual(env["HOME"], "/opt/wargames-cache/games/doom/home")
        self.assertEqual(env["XDG_DATA_HOME"], "/opt/wargames-cache/games/doom/xdg-data")
        self.assertEqual(env["WARGAMES_DOOM_STATE_PATH"], "/tmp/doom.jsonl")
        self.assertEqual(env["WARGAMES_DOOM_STATE_INTERVAL_TICKS"], "1")
