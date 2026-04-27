from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from wargames import WarGamesConfig
from wargames.cli import (
    _default_openra_root,
    _find_openra_root,
    _host_openra_support_dir,
    _install_flightgear,
    _install_redalert,
    _linux_box_command,
    _should_run_in_linux_box,
    _without_host_watch,
    build_parser,
)


def _write_openra_checkout(root: Path) -> None:
    (root / "mods" / "ra").mkdir(parents=True)
    (root / "mods" / "ra" / "mod.yaml").write_text("Metadata:\n", encoding="utf-8")
    (root / "launch-game.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")


def _write_flightgear_app(root: Path) -> None:
    binary = root / "bin" / "fgfs"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/usr/bin/env bash\n", encoding="utf-8")


class CLITests(TestCase):
    def test_parser_exposes_commands(self) -> None:
        parser = build_parser()
        self.assertEqual(parser.parse_args(["install", "--game", "redalert"]).command, "install")
        self.assertEqual(parser.parse_args(["missions"]).command, "missions")
        self.assertEqual(parser.parse_args(["missions", "--game", "flightgear"]).game, "flightgear")
        self.assertEqual(
            parser.parse_args(
                ["run", "--game", "flightgear", "--mission", "m", "--agent", "a"]
            ).game,
            "flightgear",
        )
        self.assertEqual(parser.parse_args(["boot"]).command, "boot")
        self.assertEqual(parser.parse_args(["control", "--actions", "-"]).command, "control")
        self.assertFalse(parser.parse_args(["control", "--actions", "-"]).capture_frames)
        self.assertTrue(
            parser.parse_args(["control", "--actions", "-", "--capture-frames"]).capture_frames
        )
        self.assertEqual(parser.parse_args(["serve"]).command, "serve")

    def test_install_command_uses_top_level_game_option(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["install", "--game", "redalert"])
        self.assertEqual(args.command, "install")
        self.assertEqual(args.game, "redalert")
        self.assertEqual(parser.parse_args(["install", "--game", "flightgear"]).game, "flightgear")

    def test_host_runs_primitive_redalert_commands_in_linux_box(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["boot", "--mission", "redalert.soviet-01.normal"])
        self.assertTrue(_should_run_in_linux_box(args, platform="darwin", env={}))

    def test_install_runs_in_linux_box_on_host(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["install", "--game", "redalert"])
        self.assertTrue(_should_run_in_linux_box(args, platform="darwin", env={}))
        self.assertTrue(_should_run_in_linux_box(args, platform="linux", env={}))
        self.assertFalse(
            _should_run_in_linux_box(
                args,
                platform="linux",
                env={"LAYERBRAIN_WARGAMES_IN_LINUX_BOX": "1"},
            )
        )

    def test_mission_extract_runs_in_linux_box_on_host(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["missions", "--game", "flightgear", "--extract"])
        self.assertTrue(_should_run_in_linux_box(args, platform="darwin", env={}))
        self.assertFalse(
            _should_run_in_linux_box(
                args,
                platform="linux",
                env={"LAYERBRAIN_WARGAMES_IN_LINUX_BOX": "1"},
            )
        )

    def test_default_openra_root_uses_wargames_cache(self) -> None:
        env = {"LAYERBRAIN_WARGAMES_CACHE_DIR": "/tmp/wargames-cache"}
        self.assertEqual(
            _default_openra_root(env), Path("/tmp/wargames-cache/games/redalert/openra")
        )
        self.assertEqual(_host_openra_support_dir(env), Path("/tmp/wargames-cache/openra-support"))

    def test_find_openra_root_discovers_cached_checkout(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env = {"LAYERBRAIN_WARGAMES_CACHE_DIR": temp_dir}
            root = _default_openra_root(env)
            _write_openra_checkout(root)

            self.assertEqual(_find_openra_root(env), root)

    def test_install_redalert_remembers_custom_checkout(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env = {"LAYERBRAIN_WARGAMES_CACHE_DIR": str(Path(temp_dir) / "cache")}
            root = Path(temp_dir) / "OpenRA"
            _write_openra_checkout(root)
            args = SimpleNamespace(root=str(root), repo="", ref="", build_probe=False)

            with redirect_stdout(StringIO()):
                self.assertEqual(_install_redalert(args, env), 0)

            self.assertEqual(_find_openra_root(env), root)
            self.assertTrue(_host_openra_support_dir(env).exists())

    def test_install_flightgear_remembers_registered_app(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env = {"LAYERBRAIN_WARGAMES_CACHE_DIR": str(Path(temp_dir) / "cache")}
            root = Path(temp_dir) / "flightgear"
            _write_flightgear_app(root)
            args = SimpleNamespace(root=str(root))

            with redirect_stdout(StringIO()):
                self.assertEqual(_install_flightgear(args, env), 0)

            manifest = Path(temp_dir) / "cache" / "games" / "flightgear" / "install.json"
            self.assertIn("fgfs_binary", manifest.read_text(encoding="utf-8"))

    def test_linux_box_command_does_not_forward_model_keys(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "MODEL_API_KEY": "redacted-test-value",
                "LAYERBRAIN_WARGAMES_XVFB_RESOLUTION": "1280x720",
            },
            clear=True,
        ):
            command = _linux_box_command(["boot", "--mission", "redalert.soviet-01.normal"])
        joined = " ".join(command)
        self.assertNotIn("MODEL_API_KEY", joined)
        self.assertNotIn("/Users/aaronkazah/.cache/wargames", joined)
        self.assertIn("wargames-games:/opt/wargames-cache", joined)
        self.assertIn("LAYERBRAIN_WARGAMES_CACHE_DIR=/opt/wargames-cache", joined)
        self.assertIn("LAYERBRAIN_WARGAMES_XVFB_RESOLUTION=1280x720", joined)
        self.assertIn("--entrypoint /workspace/host-wargames/scripts/linux_box.sh", joined)

    def test_linux_box_install_uses_docker_volume_cache(self) -> None:
        command = _linux_box_command(["install", "--game", "redalert"])
        joined = " ".join(command)
        self.assertIn("wargames-games:/opt/wargames-cache", joined)
        self.assertIn("LAYERBRAIN_WARGAMES_CACHE_DIR=/opt/wargames-cache", joined)
        self.assertNotIn(":/openra", joined)

    def test_config_is_importable(self) -> None:
        self.assertEqual(WarGamesConfig().xvfb_resolution, (1280, 720))

    def test_linux_box_serve_binds_inside_container(self) -> None:
        self.assertEqual(
            _without_host_watch(["serve", "--host", "127.0.0.1", "--port", "8765"]),
            ["serve", "--host", "0.0.0.0", "--port", "8765"],
        )
