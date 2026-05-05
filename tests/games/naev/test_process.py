from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase

from wargames.games.naev.config import NaevConfig
from wargames.games.naev.missions import NaevMissionSpec
from wargames.games.naev.process import (
    install_state_exporter,
    naev_command,
    naev_environment,
)


class NaevProcessTests(TestCase):
    def test_installs_lua_state_exporter_and_generated_start_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = _data_dir(Path(tmp))

            install_state_exporter(data, _mission(data_dir=str(data)))

            exporter = data / "events" / "wargames_state.lua"
            start = data / "events" / "start.lua"
            backup = data / "events" / "start.lua.wargames-original"

            self.assertIn("WARGAMES_STATE", exporter.read_text(encoding="utf-8"))
            self.assertIn('naev.missionStart("Cargo Run")', start.read_text(encoding="utf-8"))
            self.assertTrue(backup.exists())

    def test_command_selects_window_size_user_data_and_data_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = _data_dir(Path(tmp) / "dat")
            config = NaevConfig(root=str(Path(tmp) / "runtime"), window_size=(800, 600))

            command = naev_command("/usr/games/naev", str(data), config)

        self.assertEqual("/usr/games/naev", command[0])
        self.assertEqual("800", command[command.index("-W") + 1])
        self.assertEqual("600", command[command.index("-H") + 1])
        self.assertEqual(str(data), command[-1])

    def test_environment_captures_audio_without_viewer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "naev.pcm"

            env = naev_environment(NaevConfig(root=str(Path(tmp) / "runtime")), audio_path=str(audio))

        config = Path(env["ALSA_CONFIG_PATH"]).read_text(encoding="utf-8")
        self.assertIn(str(audio), config)
        self.assertIn("ALSOFT_DRIVERS", env)
        self.assertNotIn("ffplay", config)


def _data_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "events").mkdir()
    (root / "missions").mkdir()
    (root / "start.xml").write_text("<Start />\n", encoding="utf-8")
    (root / "events" / "start.lua").write_text("function create () end\n", encoding="utf-8")
    return root


def _mission(*, data_dir: str) -> NaevMissionSpec:
    return NaevMissionSpec(
        id="naev.mission.cargo.easy",
        title="Cargo Run",
        game="naev",
        source="builtin",
        difficulty="easy",
        native_difficulty="tier-1",
        tags=("space", "delivery"),
        time_limit_ticks=7200,
        mission_name="Cargo Run",
        mission_file="missions/trader/cargo.lua",
        native_location="Computer",
        tier=1,
        data_dir=data_dir,
    )
