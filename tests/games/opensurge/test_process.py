from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase

from wargames.games.opensurge.config import OpenSurgeConfig
from wargames.games.opensurge.missions import OpenSurgeMissionSpec
from wargames.games.opensurge.process import opensurge_command, opensurge_environment


class OpenSurgeProcessTests(TestCase):
    def test_command_uses_relative_level_inside_game_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "levels").mkdir()
            (root / "levels" / "sunshine-1.lev").write_text("", encoding="utf-8")
            mission = _mission(level_file=str(root / "levels" / "sunshine-1.lev"), data_dir=str(root))

            command = opensurge_command(
                "/usr/games/opensurge", mission, OpenSurgeConfig(root=str(root)), seed=0
            )

        self.assertEqual("levels/sunshine-1.lev", command[command.index("--level") + 1])

    def test_environment_captures_audio_to_runtime_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "opensurge.pcm"

            env = opensurge_environment(
                OpenSurgeConfig(),
                state_path=str(Path(tmp) / "state.jsonl"),
                audio_path=str(audio),
            )

        config = Path(env["ALSA_CONFIG_PATH"]).read_text(encoding="utf-8")
        self.assertIn("pcm.wargames_sink { type null }", config)
        self.assertIn(str(audio), config)
        self.assertNotIn("ffplay", config)


def _mission(*, level_file: str, data_dir: str) -> OpenSurgeMissionSpec:
    return OpenSurgeMissionSpec(
        id="opensurge.level.sunshine-1.normal",
        title="Sunshine Paradise Act 1 (Normal)",
        game="opensurge",
        source="builtin",
        difficulty="normal",
        native_difficulty="normal",
        tags=("platformer", "running"),
        time_limit_ticks=6000,
        level_file=level_file,
        level_set="builtin",
        act=1,
        target_time_seconds=100,
        data_dir=data_dir,
    )
