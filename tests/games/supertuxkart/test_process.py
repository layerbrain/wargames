from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from wargames.games.supertuxkart.config import SuperTuxKartConfig
from wargames.games.supertuxkart.missions import SuperTuxKartMissionSpec
from wargames.games.supertuxkart.process import (
    locate_supertuxkart,
    supertuxkart_command,
    supertuxkart_environment,
)


class SuperTuxKartProcessTests(TestCase):
    def test_locate_binary_from_registered_root(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "bin" / "supertuxkart"
            binary.parent.mkdir()
            binary.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

            self.assertEqual(locate_supertuxkart(SuperTuxKartConfig(root=str(root))), str(binary))

    def test_command_starts_direct_race(self) -> None:
        mission = SuperTuxKartMissionSpec(
            id="supertuxkart.race.lighthouse.normal",
            title="Around the Lighthouse",
            game="supertuxkart",
            source="builtin",
            track="lighthouse",
            laps=4,
            num_karts=6,
            native_difficulty="1",
        )

        command = supertuxkart_command(
            "/usr/games/supertuxkart",
            mission,
            SuperTuxKartConfig(window_size=(1024, 768)),
            seed=7,
        )

        self.assertIn("--race-now", command)
        self.assertIn("--track=lighthouse", command)
        self.assertIn("--laps=4", command)
        self.assertIn("--numkarts=6", command)
        self.assertIn("--difficulty=1", command)
        self.assertIn("--screensize=1024x768", command)
        self.assertIn("--seed=7", command)

    def test_environment_keeps_state_inside_runtime_cache(self) -> None:
        with patch.dict(
            "os.environ", {"LAYERBRAIN_WARGAMES_CACHE_DIR": "/opt/wargames-cache"}, clear=True
        ):
            env = supertuxkart_environment(SuperTuxKartConfig(), display=":99")

        self.assertEqual(env["DISPLAY"], ":99")
        self.assertEqual(env["HOME"], "/opt/wargames-cache/games/supertuxkart/home")
        self.assertEqual(env["XDG_DATA_HOME"], "/opt/wargames-cache/games/supertuxkart/xdg-data")
        self.assertEqual(env["IRR_DEVICE_TYPE"], "x11")
