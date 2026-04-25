from unittest import TestCase
from unittest.mock import patch

from wargames import WarGamesConfig
from wargames.cli import _linux_box_command, _should_run_in_linux_box, _without_host_watch, build_parser


class CLITests(TestCase):
    def test_parser_exposes_primitive_commands_only(self) -> None:
        parser = build_parser()
        self.assertEqual(parser.parse_args(["missions"]).command, "missions")
        self.assertEqual(parser.parse_args(["boot"]).command, "boot")
        self.assertEqual(parser.parse_args(["control", "--actions", "-"]).command, "control")
        self.assertEqual(parser.parse_args(["serve"]).command, "serve")

    def test_host_runs_primitive_redalert_commands_in_linux_box(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["boot", "--mission", "redalert.soviet-01.normal"])
        self.assertTrue(_should_run_in_linux_box(args, platform="darwin", env={}))

    def test_linux_box_command_does_not_forward_model_keys(self) -> None:
        with patch.dict(
            "os.environ",
            {"MODEL_API_KEY": "redacted-test-value", "LAYERBRAIN_WARGAMES_XVFB_RESOLUTION": "1280x720"},
            clear=True,
        ):
            command = _linux_box_command(["boot", "--mission", "redalert.soviet-01.normal"])
        joined = " ".join(command)
        self.assertNotIn("MODEL_API_KEY", joined)
        self.assertIn("LAYERBRAIN_WARGAMES_XVFB_RESOLUTION=1280x720", joined)
        self.assertIn("--entrypoint /workspace/host-wargames/scripts/linux_box.sh", joined)

    def test_config_is_importable(self) -> None:
        self.assertEqual(WarGamesConfig().xvfb_resolution, (1280, 720))

    def test_linux_box_serve_binds_inside_container(self) -> None:
        self.assertEqual(
            _without_host_watch(["serve", "--host", "127.0.0.1", "--port", "8765"]),
            ["serve", "--host", "0.0.0.0", "--port", "8765"],
        )
