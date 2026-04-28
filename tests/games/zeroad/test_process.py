import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from wargames.games.zeroad.config import ZeroADConfig
from wargames.games.zeroad.process import (
    locate_zeroad,
    prepare_zeroad_runtime_environment,
    zeroad_command,
    zeroad_environment,
    zeroad_working_dir,
)


class ZeroADProcessTests(TestCase):
    def test_locates_binary_from_source_root(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "0ad"
            binary = root / "binaries" / "system" / "pyrogenesis"
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

            self.assertEqual(locate_zeroad(ZeroADConfig(root=str(root))), str(binary))

    def test_builds_rl_command(self) -> None:
        command = zeroad_command(
            "/opt/0ad/binaries/system/pyrogenesis",
            ZeroADConfig(window_size=(1024, 768)),
            rl_host="127.0.0.1",
            rl_port=6000,
        )

        self.assertIn("--rl-interface=127.0.0.1:6000", command)
        self.assertIn("-quickstart", command)
        self.assertIn("-nosound", command)
        self.assertIn("-xres=1024", command)
        self.assertIn("-yres=768", command)

    def test_wraps_zeroad_process_in_runtime_user_when_root(self) -> None:
        with (
            patch("wargames.games.zeroad.process.os.geteuid", return_value=0),
            patch("wargames.games.zeroad.process.shutil.which", return_value="/usr/sbin/runuser"),
            patch(
                "wargames.games.zeroad.process.pwd.getpwnam",
                return_value=SimpleNamespace(pw_uid=999, pw_gid=999),
            ),
        ):
            command = zeroad_command(
                "/opt/0ad/binaries/system/pyrogenesis",
                ZeroADConfig(),
                rl_host="127.0.0.1",
                rl_port=6000,
            )

        self.assertEqual(
            command[:5],
            ["runuser", "--user", "wargames", "--preserve-environment", "--"],
        )
        self.assertIn("/opt/0ad/binaries/system/pyrogenesis", command)

    def test_sets_cache_home_and_display(self) -> None:
        with TemporaryDirectory() as temp_dir:
            old = os.environ.get("LAYERBRAIN_WARGAMES_CACHE_DIR")
            os.environ["LAYERBRAIN_WARGAMES_CACHE_DIR"] = temp_dir
            try:
                env = zeroad_environment(ZeroADConfig(root="/opt/0ad"), display=":99")
            finally:
                if old is None:
                    os.environ.pop("LAYERBRAIN_WARGAMES_CACHE_DIR", None)
                else:
                    os.environ["LAYERBRAIN_WARGAMES_CACHE_DIR"] = old

        self.assertEqual(env["DISPLAY"], ":99")
        self.assertEqual(env["ZEROAD_ROOT"], "/opt/0ad")
        self.assertEqual(env["HOME"], str(Path(temp_dir) / "games" / "zeroad" / "home"))

    def test_prepares_runtime_home_dirs(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            env = {
                "HOME": str(root / "home"),
                "XDG_CACHE_HOME": str(root / "cache"),
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_DATA_HOME": str(root / "data"),
            }

            with patch("wargames.games.zeroad.process.os.geteuid", return_value=1000):
                prepare_zeroad_runtime_environment(env)

            self.assertTrue((root / "home").is_dir())
            self.assertTrue((root / "cache").is_dir())
            self.assertTrue((root / "config").is_dir())
            self.assertTrue((root / "data").is_dir())

    def test_working_dir_uses_source_root_for_pyrogenesis(self) -> None:
        self.assertEqual(
            zeroad_working_dir("/opt/0ad/binaries/system/pyrogenesis", ZeroADConfig()),
            "/opt/0ad",
        )
