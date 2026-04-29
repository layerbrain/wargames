from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from wargames.games.freeciv.config import FreeCivConfig
from wargames.games.freeciv.missions import FreeCivMissionSpec
from wargames.games.freeciv.process import (
    freeciv_client_command,
    freeciv_environment,
    freeciv_server_command,
    locate_freeciv_client,
    locate_freeciv_server,
    prepare_freeciv_runtime_environment,
)


class FreeCivProcessTests(TestCase):
    def test_locates_server_and_client_from_registered_root(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            server = root / "usr" / "games" / "freeciv-server"
            client = root / "usr" / "games" / "freeciv-gtk3.22"
            server.parent.mkdir(parents=True)
            server.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            client.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

            config = FreeCivConfig(root=str(root))

            self.assertEqual(locate_freeciv_server(config), str(server))
            self.assertEqual(locate_freeciv_client(config), str(client))

    def test_builds_server_and_client_commands(self) -> None:
        mission = FreeCivMissionSpec(
            id="freeciv.test",
            title="T",
            game="freeciv",
            source="builtin",
            ruleset="civ2civ3",
        )
        config = FreeCivConfig(server_port=6000, window_size=(1024, 768))
        server_command = freeciv_server_command(
            "/usr/games/freeciv-server",
            config,
            mission,
            script_path=Path("/tmp/start.serv"),
            save_dir=Path("/tmp/saves"),
        )
        client_command = freeciv_client_command("/usr/games/freeciv-gtk3.22", config, mission)

        self.assertIn("--Announce", server_command)
        self.assertIn("--bind", server_command)
        self.assertIn("127.0.0.1", server_command)
        self.assertIn("--ruleset", server_command)
        self.assertIn("civ2civ3", server_command)
        self.assertIn("--autoconnect", client_command)
        self.assertIn("--resolution", client_command)
        self.assertIn("1024x768", client_command)

    def test_wraps_freeciv_processes_in_runtime_user_when_root(self) -> None:
        mission = FreeCivMissionSpec(id="freeciv.test", title="T", game="freeciv", source="builtin")
        with (
            patch("wargames.games.freeciv.process.os.geteuid", return_value=0),
            patch("wargames.games.freeciv.process.shutil.which", return_value="/usr/sbin/runuser"),
            patch(
                "wargames.games.freeciv.process.pwd.getpwnam",
                return_value=SimpleNamespace(pw_uid=999, pw_gid=999),
            ),
        ):
            command = freeciv_client_command("/usr/games/freeciv-gtk3.22", FreeCivConfig(), mission)

        self.assertEqual(
            command[:5],
            ["/usr/sbin/runuser", "--user", "wargames", "--preserve-environment", "--"],
        )
        self.assertIn("/usr/games/freeciv-gtk3.22", command)

    def test_environment_keeps_state_inside_runtime_cache(self) -> None:
        with patch.dict(
            "os.environ", {"LAYERBRAIN_WARGAMES_CACHE_DIR": "/opt/wargames-cache"}, clear=True
        ):
            env = freeciv_environment(FreeCivConfig(), display=":99")

        self.assertEqual(env["DISPLAY"], ":99")
        self.assertEqual(env["HOME"], "/opt/wargames-cache/games/freeciv/home")
        self.assertEqual(env["XDG_CACHE_HOME"], "/opt/wargames-cache/games/freeciv/xdg-cache")

    def test_prepares_runtime_dirs_and_save_dir(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = FreeCivConfig(save_dir=str(root / "saves"), startup_dir=str(root / "startup"))
            env = {
                "HOME": str(root / "home"),
                "XDG_CACHE_HOME": str(root / "cache"),
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_DATA_HOME": str(root / "data"),
            }

            with patch("wargames.games.freeciv.process.os.geteuid", return_value=1000):
                save_dir = prepare_freeciv_runtime_environment(config, env)

            self.assertEqual(save_dir, root / "saves")
            for name in ("home", "cache", "config", "data", "saves", "startup"):
                self.assertTrue((root / name).is_dir(), name)
