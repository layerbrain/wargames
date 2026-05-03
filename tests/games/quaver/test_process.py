from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase

from wargames.games.quaver.config import QuaverConfig
from wargames.games.quaver.backend import verify_state_probe_installed
from wargames.games.quaver.missions import QuaverMissionSpec
from wargames.games.quaver.process import quaver_command, quaver_environment


class QuaverProcessTests(TestCase):
    def test_command_runs_runtime_binary_directly(self) -> None:
        mission = _mission()

        command = quaver_command("/opt/quaver/Quaver", mission, QuaverConfig())

        self.assertEqual(["/opt/quaver/Quaver"], command)

    def test_environment_selects_chart_and_captures_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "runtime"
            runtime.mkdir()
            binary = runtime / "Quaver"
            binary.write_text("", encoding="utf-8")
            (runtime / "Quaver.Shared.dll").write_text("WARGAMES_QUAVER_STATE_PATH", encoding="utf-8")
            audio = root / "quaver.pcm"

            env = quaver_environment(
                QuaverConfig(binary=str(binary)),
                _mission(),
                state_path=str(root / "state.jsonl"),
                audio_path=str(audio),
                display=":99",
            )

        self.assertEqual("1", env["WARGAMES_QUAVER_AUTOPLAY"])
        self.assertEqual("1", env["WARGAMES_QUAVER_DISABLE_STEAM"])
        self.assertEqual("42", env["WARGAMES_QUAVER_MAP_ID"])
        self.assertEqual(":99", env["DISPLAY"])
        self.assertIn(str(runtime), env["LD_LIBRARY_PATH"])
        config = Path(env["ALSA_CONFIG_PATH"]).read_text(encoding="utf-8")
        self.assertIn(str(audio), config)
        self.assertNotIn("ffplay", config)

    def test_probe_verification_accepts_dotnet_utf16_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = "WARGAMES_QUAVER_STATE_PATH".encode("utf-16-le")
            (root / "Quaver.Shared.dll").write_bytes(b"\x00" + marker + b"\x00")

            verify_state_probe_installed(root)


def _mission() -> QuaverMissionSpec:
    return QuaverMissionSpec(
        id="quaver.chart.test.42.easy",
        title="Artist - Song [Easy]",
        game="quaver",
        source="builtin",
        difficulty="easy",
        native_difficulty="Easy",
        tags=("rhythm", "timing", "keys4", "4k"),
        time_limit_ticks=3600,
        estimated_duration_ticks=2400,
        map_id=42,
        mapset_id=4,
        map_path="DefaultMaps/sample.qp:chart.qua",
        archive_path="DefaultMaps/sample.qp",
        song_title="Song",
        artist="Artist",
        difficulty_name="Easy",
        mode="Keys4",
        key_count=4,
        audio_file="audio.mp3",
        hit_objects=120,
        long_notes=4,
        mines=0,
        total_judgements=124,
        song_length_ms=40_000,
        notes_per_second=3.0,
    )
