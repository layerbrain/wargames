import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from wargames.games.zeroad.config import ZeroADConfig


class ZeroADConfigTests(TestCase):
    def test_from_env_uses_cached_install_manifest(self) -> None:
        with TemporaryDirectory() as temp_dir:
            cache = Path(temp_dir) / "cache"
            manifest = cache / "games" / "zeroad" / "install.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                json.dumps(
                    {
                        "binary": "/opt/wargames-cache/games/zeroad/0ad/binaries/system/pyrogenesis",
                        "root": "/opt/wargames-cache/games/zeroad/0ad",
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(
                "os.environ",
                {"LAYERBRAIN_WARGAMES_CACHE_DIR": str(cache)},
                clear=True,
            ):
                config = ZeroADConfig.from_env()

        self.assertEqual(
            config.binary,
            "/opt/wargames-cache/games/zeroad/0ad/binaries/system/pyrogenesis",
        )
        self.assertEqual(config.root, "/opt/wargames-cache/games/zeroad/0ad")

    def test_explicit_env_overrides_cached_install_manifest(self) -> None:
        with TemporaryDirectory() as temp_dir:
            cache = Path(temp_dir) / "cache"
            manifest = cache / "games" / "zeroad" / "install.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                json.dumps({"binary": "/cache/pyrogenesis", "root": "/cache/0ad"}),
                encoding="utf-8",
            )

            with patch.dict(
                "os.environ",
                {
                    "LAYERBRAIN_WARGAMES_CACHE_DIR": str(cache),
                    "LAYERBRAIN_WARGAMES_ZEROAD_BINARY": "/custom/pyrogenesis",
                    "LAYERBRAIN_WARGAMES_ZEROAD_ROOT": "/custom/0ad",
                },
                clear=True,
            ):
                config = ZeroADConfig.from_env()

        self.assertEqual(config.binary, "/custom/pyrogenesis")
        self.assertEqual(config.root, "/custom/0ad")
