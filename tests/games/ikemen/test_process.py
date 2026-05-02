from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from wargames.games.ikemen.config import IkemenConfig
from wargames.games.ikemen.missions import IkemenMissionSpec
from wargames.games.ikemen.process import ikemen_command, write_config


class IkemenProcessTests(TestCase):
    def test_command_uses_quick_vs_flags(self) -> None:
        command = ikemen_command(
            "/opt/ikemen/Ikemen_GO_Linux",
            IkemenMissionSpec(
                id="ikemen.vs.kfm.normal",
                title="KFM",
                game="ikemen",
                source="builtin",
                p2="kfmZ",
                ai_level=5,
            ),
            IkemenConfig(),
            config_path=Path("/tmp/ikemen.json"),
        )

        self.assertIn("-p2.ai", command)
        self.assertIn("kfmZ", command)
        self.assertIn("-config", command)

    def test_config_injects_common_lua_exporter(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = write_config(Path(temp_dir) / "config.json", IkemenConfig(window_size=(800, 600)))

            text = path.read_text(encoding="utf-8")

        self.assertIn("wargames_state_export", text)
        self.assertIn('"GameWidth": 800', text)
