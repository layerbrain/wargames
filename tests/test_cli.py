from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from wargames import WarGamesConfig
from wargames.cli import (
    _build_zeroad_source,
    _default_doom_source_root,
    _default_mindustry_root,
    _default_openra_root,
    _default_supertux_source_root,
    _default_zeroad_source_root,
    _find_doom_binary,
    _find_freeciv_client_binary,
    _find_freeciv_server_binary,
    _find_mindustry_client,
    _find_mindustry_server,
    _find_openra_root,
    _find_supertux_binary,
    _find_supertuxkart_binary,
    _find_zeroad_binary,
    _ensure_linux_box_image,
    _host_openra_support_dir,
    _install_flightgear,
    _install_freeciv,
    _install_doom,
    _install_mindustry,
    _install_redalert,
    _install_supertux,
    _install_supertuxkart,
    _install_zeroad,
    _linux_box_command,
    _linux_box_runtime,
    _normalize_zeroad_premake_version,
    _should_run_in_linux_box,
    _sync_zeroad_lfs,
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


def _write_supertuxkart_app(root: Path) -> None:
    binary = root / "bin" / "supertuxkart"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (root / "data" / "tracks").mkdir(parents=True)


def _write_zeroad_app(root: Path) -> Path:
    binary = root / "binaries" / "system" / "pyrogenesis"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (root / "binaries" / "data" / "mods" / "public" / "maps").mkdir(parents=True)
    return binary


def _write_freeciv_app(root: Path) -> tuple[Path, Path]:
    server = root / "usr" / "games" / "freeciv-server"
    client = root / "usr" / "games" / "freeciv-gtk3.22"
    server.parent.mkdir(parents=True)
    server.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    client.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    return server, client


def _write_doom_checkout(root: Path) -> Path:
    binary = root / "build" / "src" / "chocolate-doom"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (root / "src" / "doom").mkdir(parents=True)
    (root / "src" / "doom" / "g_game.c").write_text("void G_Ticker(void) {}\n", encoding="utf-8")
    (root / "CMakeLists.txt").write_text("project(chocolate-doom)\n", encoding="utf-8")
    return binary


def _write_supertux_checkout(root: Path) -> Path:
    binary = root / "build" / "supertux2"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/usr/bin/env bash\nWARGAMES_SUPERTUX_STATE_PATH=1\n", encoding="utf-8")
    (root / "src" / "supertux").mkdir(parents=True)
    (root / "src" / "supertux" / "game_session.cpp").write_text(
        "void GameSession::update() {}\n", encoding="utf-8"
    )
    (root / "data" / "levels" / "world1").mkdir(parents=True)
    (root / "data" / "levels" / "world1" / "intro.stl").write_text(
        '(supertux-level (name "Intro"))\n', encoding="utf-8"
    )
    (root / "CMakeLists.txt").write_text("project(supertux)\n", encoding="utf-8")
    return binary


def _write_mindustry_app(root: Path) -> tuple[Path, Path]:
    client = root / "Mindustry.jar"
    server = root / "server-release.jar"
    server.parent.mkdir(parents=True)
    client.write_text("jar", encoding="utf-8")
    server.write_text("jar", encoding="utf-8")
    return client, server


class CLITests(TestCase):
    def test_parser_exposes_commands(self) -> None:
        parser = build_parser()
        self.assertEqual(parser.parse_args(["install", "--game", "redalert"]).command, "install")
        self.assertEqual(parser.parse_args(["missions"]).command, "missions")
        self.assertEqual(parser.parse_args(["missions", "--game", "flightgear"]).game, "flightgear")
        self.assertEqual(parser.parse_args(["missions", "--game", "freeciv"]).game, "freeciv")
        self.assertEqual(parser.parse_args(["missions", "--game", "doom"]).game, "doom")
        self.assertEqual(parser.parse_args(["missions", "--game", "supertux"]).game, "supertux")
        self.assertEqual(parser.parse_args(["missions", "--game", "mindustry"]).game, "mindustry")
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
        self.assertEqual(
            parser.parse_args(["install", "--game", "supertuxkart"]).game, "supertuxkart"
        )
        self.assertEqual(parser.parse_args(["install", "--game", "zeroad"]).game, "zeroad")
        self.assertEqual(parser.parse_args(["install", "--game", "freeciv"]).game, "freeciv")
        self.assertEqual(parser.parse_args(["install", "--game", "doom"]).game, "doom")
        self.assertEqual(parser.parse_args(["install", "--game", "supertux"]).game, "supertux")
        self.assertEqual(parser.parse_args(["install", "--game", "mindustry"]).game, "mindustry")

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
        self.assertEqual(
            _default_zeroad_source_root(env), Path("/tmp/wargames-cache/games/zeroad/0ad")
        )
        self.assertEqual(
            _default_doom_source_root(env),
            Path("/tmp/wargames-cache/games/doom/chocolate-doom"),
        )
        self.assertEqual(
            _default_supertux_source_root(env), Path("/tmp/wargames-cache/games/supertux/supertux")
        )
        self.assertEqual(
            _default_mindustry_root(env), Path("/tmp/wargames-cache/games/mindustry")
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

    def test_install_supertuxkart_remembers_registered_app(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env = {"LAYERBRAIN_WARGAMES_CACHE_DIR": str(Path(temp_dir) / "cache")}
            root = Path(temp_dir) / "stk-code"
            binary = root / "cmake_build" / "bin" / "supertuxkart"
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            (root / "CMakeLists.txt").write_text("project(stk)\n", encoding="utf-8")
            args = SimpleNamespace(root=str(root))

            with patch("wargames.cli._install_supertuxkart_probe"), redirect_stdout(StringIO()):
                self.assertEqual(_install_supertuxkart(args, env), 0)

            manifest = Path(temp_dir) / "cache" / "games" / "supertuxkart" / "install.json"
            self.assertIn(
                "WarGames in-process kart state exporter",
                manifest.read_text(encoding="utf-8"),
            )
            self.assertEqual(_find_supertuxkart_binary(root), binary)

    def test_install_zeroad_remembers_registered_app(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env = {"LAYERBRAIN_WARGAMES_CACHE_DIR": str(Path(temp_dir) / "cache")}
            root = Path(temp_dir) / "0ad"
            binary = _write_zeroad_app(root)
            args = SimpleNamespace(root=str(root))

            with redirect_stdout(StringIO()):
                self.assertEqual(_install_zeroad(args, env), 0)

            manifest = Path(temp_dir) / "cache" / "games" / "zeroad" / "install.json"
            self.assertIn("upstream 0 A.D. RL HTTP interface", manifest.read_text(encoding="utf-8"))
            self.assertEqual(_find_zeroad_binary(root), binary)

    def test_install_freeciv_remembers_registered_app(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env = {"LAYERBRAIN_WARGAMES_CACHE_DIR": str(Path(temp_dir) / "cache")}
            root = Path(temp_dir) / "freeciv"
            server, client = _write_freeciv_app(root)
            args = SimpleNamespace(root=str(root))

            with redirect_stdout(StringIO()):
                self.assertEqual(_install_freeciv(args, env), 0)

            manifest = Path(temp_dir) / "cache" / "games" / "freeciv" / "install.json"
            self.assertIn("Freeciv server save snapshots", manifest.read_text(encoding="utf-8"))
            self.assertEqual(_find_freeciv_server_binary(root), server)
            self.assertEqual(_find_freeciv_client_binary(root), client)

    def test_install_doom_remembers_registered_app(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env = {"LAYERBRAIN_WARGAMES_CACHE_DIR": str(Path(temp_dir) / "cache")}
            root = Path(temp_dir) / "chocolate-doom"
            binary = _write_doom_checkout(root)
            args = SimpleNamespace(root=str(root))

            with (
                patch("wargames.cli._install_doom_probe"),
                patch("wargames.games.doom.missions.discover_iwads", return_value=(Path("/iwad.wad"),)),
                redirect_stdout(StringIO()),
            ):
                self.assertEqual(_install_doom(args, env), 0)

            manifest = Path(temp_dir) / "cache" / "games" / "doom" / "install.json"
            self.assertIn("WarGames in-process Doom state exporter", manifest.read_text(encoding="utf-8"))
            self.assertEqual(_find_doom_binary(root), binary)

    def test_install_supertux_remembers_registered_app(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env = {"LAYERBRAIN_WARGAMES_CACHE_DIR": str(Path(temp_dir) / "cache")}
            root = Path(temp_dir) / "supertux"
            binary = _write_supertux_checkout(root)
            args = SimpleNamespace(root=str(root))

            with (
                patch("wargames.cli._install_supertux_probe"),
                redirect_stdout(StringIO()),
            ):
                self.assertEqual(_install_supertux(args, env), 0)

            manifest = Path(temp_dir) / "cache" / "games" / "supertux" / "install.json"
            self.assertIn(
                "WarGames in-process SuperTux state exporter",
                manifest.read_text(encoding="utf-8"),
            )
            self.assertEqual(_find_supertux_binary(root), binary)

    def test_install_mindustry_remembers_registered_app(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env = {"LAYERBRAIN_WARGAMES_CACHE_DIR": str(Path(temp_dir) / "cache")}
            root = Path(temp_dir) / "mindustry"
            client, server = _write_mindustry_app(root)
            args = SimpleNamespace(root=str(root))

            with (
                patch(
                    "wargames.cli._build_mindustry_probe",
                    return_value=root
                    / "home"
                    / ".local"
                    / "share"
                    / "Mindustry"
                    / "mods"
                    / "wargames-mindustry-state.jar",
                ),
                redirect_stdout(StringIO()),
            ):
                self.assertEqual(_install_mindustry(args, env), 0)

            manifest = Path(temp_dir) / "cache" / "games" / "mindustry" / "install.json"
            self.assertIn(
                "Mindustry headless server plugin JSONL state exporter",
                manifest.read_text(encoding="utf-8"),
            )
            self.assertEqual(_find_mindustry_client(root), client)
            self.assertEqual(_find_mindustry_server(root), server)

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
        self.assertIn("wargames-redalert:/opt/wargames-cache", joined)
        self.assertIn("wargames-linux-redalert", joined)
        self.assertIn("LAYERBRAIN_WARGAMES_CACHE_DIR=/opt/wargames-cache", joined)
        self.assertIn("LAYERBRAIN_WARGAMES_GAME=redalert", joined)
        self.assertIn("LAYERBRAIN_WARGAMES_XVFB_RESOLUTION=1280x720", joined)
        self.assertIn("LAYERBRAIN_WARGAMES_FLIGHTGEAR_WINDOW_SIZE=1280x720", joined)
        self.assertIn("LAYERBRAIN_WARGAMES_SUPERTUXKART_WINDOW_SIZE=1280x720", joined)
        self.assertIn("LAYERBRAIN_WARGAMES_ZEROAD_WINDOW_SIZE=1280x720", joined)
        self.assertIn("LAYERBRAIN_WARGAMES_FREECIV_WINDOW_SIZE=1280x720", joined)
        self.assertIn("LAYERBRAIN_WARGAMES_DOOM_WINDOW_SIZE=1280x720", joined)
        self.assertIn("LAYERBRAIN_WARGAMES_SUPERTUX_WINDOW_SIZE=1280x720", joined)
        self.assertIn("--entrypoint /workspace/host-wargames/scripts/linux_box.sh", joined)

    def test_linux_box_install_uses_docker_volume_cache(self) -> None:
        command = _linux_box_command(["install", "--game", "redalert"])
        joined = " ".join(command)
        self.assertIn("wargames-redalert:/opt/wargames-cache", joined)
        self.assertIn("wargames-linux-redalert", joined)
        self.assertIn("LAYERBRAIN_WARGAMES_CACHE_DIR=/opt/wargames-cache", joined)
        self.assertNotIn(":/openra", joined)

    def test_linux_box_uses_separate_image_and_volume_per_game(self) -> None:
        cases = {
            "redalert": ("wargames-linux-redalert", "wargames-redalert"),
            "flightgear": ("wargames-linux-flightgear", "wargames-flightgear"),
            "supertuxkart": ("wargames-linux-supertuxkart", "wargames-supertuxkart"),
            "zeroad": ("wargames-linux-zeroad", "wargames-zeroad"),
            "freeciv": ("wargames-linux-freeciv", "wargames-freeciv"),
            "doom": ("wargames-linux-doom", "wargames-doom"),
            "supertux": ("wargames-linux-supertux", "wargames-supertux"),
            "mindustry": ("wargames-linux-mindustry", "wargames-mindustry"),
        }
        for game, (image, volume) in cases.items():
            with self.subTest(game=game):
                runtime = _linux_box_runtime(game)
                command = _linux_box_command(["install", "--game", game])
                joined = " ".join(command)

                self.assertEqual(runtime.image, image)
                self.assertEqual(runtime.cache_volume, volume)
                self.assertIn(image, joined)
                self.assertIn(f"{volume}:/opt/wargames-cache", joined)
                self.assertIn(f"LAYERBRAIN_WARGAMES_GAME={game}", joined)
                if game == "mindustry":
                    self.assertEqual(runtime.platform, "linux/amd64")
                    self.assertIn("--platform linux/amd64", joined)

    def test_linux_box_builds_shared_base_before_game_image(self) -> None:
        built: list[tuple[str, str]] = []

        def image_exists(image: str) -> bool:
            return image == "docker"

        def build(*, image: str, dockerfile: str, platform: str | None = None) -> None:
            built.append((image, dockerfile))

        with (
            patch("wargames.cli.shutil.which", return_value="/usr/bin/docker"),
            patch("wargames.cli._image_exists", side_effect=image_exists),
            patch("wargames.cli._docker_build", side_effect=build),
        ):
            _ensure_linux_box_image(_linux_box_runtime("zeroad"))

        self.assertEqual(
            built,
            [
                ("wargames-linux-base", "docker/base/Dockerfile"),
                ("wargames-linux-zeroad", "docker/zeroad/Dockerfile"),
            ],
        )

    def test_mindustry_linux_box_builds_amd64_base_and_game_image(self) -> None:
        built: list[tuple[str, str, str | None]] = []

        def image_exists(image: str) -> bool:
            return image == "docker"

        def build(*, image: str, dockerfile: str, platform: str | None = None) -> None:
            built.append((image, dockerfile, platform))

        with (
            patch("wargames.cli.shutil.which", return_value="/usr/bin/docker"),
            patch("wargames.cli._image_exists", side_effect=image_exists),
            patch("wargames.cli._docker_build", side_effect=build),
        ):
            _ensure_linux_box_image(_linux_box_runtime("mindustry"))

        self.assertEqual(
            built,
            [
                ("wargames-linux-base-amd64", "docker/base/Dockerfile", "linux/amd64"),
                ("wargames-linux-mindustry", "docker/mindustry/Dockerfile", "linux/amd64"),
            ],
        )

    def test_zeroad_build_normalizes_vendored_premake_version(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir) / "0ad"
            premake_vendor_root = source_root / "libraries" / "source" / "premake-core"
            premake_root = premake_vendor_root / "premake-core-5.0.0-beta7"
            makefile = premake_root / "build" / "bootstrap" / "Premake5.make"
            built_binary = premake_root / "bin" / "release" / "premake5"
            makefile.parent.mkdir(parents=True)
            built_binary.parent.mkdir(parents=True)
            makefile.write_text(
                'DEFINES += -DNDEBUG -DPREMAKE_VERSION=\\"0.28.0\\" -DLUA_USE_POSIX\n',
                encoding="utf-8",
            )
            built_binary.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

            with (
                patch(
                    "wargames.cli.subprocess.run",
                    return_value=SimpleNamespace(stdout="premake5 5.0.0-beta7\n"),
                ) as run,
                patch("wargames.cli.shutil.copy2") as copy,
            ):
                _normalize_zeroad_premake_version(source_root, jobs="2")

            self.assertIn(
                '-DPREMAKE_VERSION=\\"5.0.0-beta7\\"',
                makefile.read_text(encoding="utf-8"),
            )
            copy.assert_called_once_with(built_binary, premake_vendor_root / "bin" / "premake5")
            self.assertEqual(
                run.call_args_list[0].args[0],
                ["make", "-C", "build/bootstrap", "-j2", "config=release"],
            )
            self.assertEqual(
                run.call_args_list[1].args[0],
                [str(premake_vendor_root / "bin" / "premake5"), "--version"],
            )

    def test_zeroad_lfs_sync_materializes_runtime_assets(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir) / "0ad"
            source_root.mkdir()

            with (
                patch("wargames.cli._zeroad_lfs_assets_ready", side_effect=[False, True]),
                patch("wargames.cli.shutil.which", return_value="/usr/bin/tool"),
                patch("wargames.cli.subprocess.run") as run,
            ):
                _sync_zeroad_lfs(source_root)

        self.assertEqual(
            [call.args[0] for call in run.call_args_list],
            [
                ["git", "-c", f"safe.directory={source_root}", "lfs", "install", "--local"],
                ["git", "-c", f"safe.directory={source_root}", "lfs", "pull"],
            ],
        )
        self.assertEqual(run.call_args_list[0].kwargs["cwd"], source_root)
        self.assertTrue(run.call_args_list[0].kwargs["check"])

    def test_zeroad_build_uses_current_atlas_flag(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir) / "0ad"
            source_root.mkdir()

            with (
                patch("wargames.cli.os.cpu_count", return_value=8),
                patch("wargames.cli.shutil.which", return_value="/usr/local/bin/cbindgen"),
                patch("wargames.cli._normalize_zeroad_premake_version"),
                patch("wargames.cli.subprocess.run") as run,
            ):
                _build_zeroad_source(source_root)

            commands = [call.args[0] for call in run.call_args_list]
            self.assertIn(
                ["build/workspaces/update-workspaces.sh", "--without-atlas", "-j4"],
                commands,
            )
            self.assertIn(
                ["make", "-C", "build/workspaces/gcc", "-j4", "pyrogenesis"],
                commands,
            )
            self.assertNotIn(
                ["build/workspaces/update-workspaces.sh", "--disable-atlas", "-j4"],
                commands,
            )

    def test_zeroad_premake_normalization_skips_valid_binary(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir) / "0ad"
            premake_vendor_root = source_root / "libraries" / "source" / "premake-core"
            premake_root = premake_vendor_root / "premake-core-5.0.0-beta7"
            makefile = premake_root / "build" / "bootstrap" / "Premake5.make"
            target_binary = premake_vendor_root / "bin" / "premake5"
            makefile.parent.mkdir(parents=True)
            target_binary.parent.mkdir(parents=True)
            makefile.write_text(
                'DEFINES += -DNDEBUG -DPREMAKE_VERSION=\\"5.0.0-beta7\\" -DLUA_USE_POSIX\n',
                encoding="utf-8",
            )
            target_binary.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

            with (
                patch(
                    "wargames.cli.subprocess.run",
                    return_value=SimpleNamespace(stdout="premake5 5.0.0-beta7\n"),
                ) as run,
                patch("wargames.cli.shutil.copy2") as copy,
            ):
                _normalize_zeroad_premake_version(source_root, jobs="2")

            run.assert_called_once_with(
                [str(target_binary), "--version"],
                cwd=source_root,
                check=True,
                capture_output=True,
                text=True,
            )
            copy.assert_not_called()

    def test_config_is_importable(self) -> None:
        self.assertEqual(WarGamesConfig().xvfb_resolution, (1280, 720))

    def test_linux_box_serve_binds_inside_container(self) -> None:
        self.assertEqual(
            _without_host_watch(["serve", "--host", "127.0.0.1", "--port", "8765"]),
            ["serve", "--host", "0.0.0.0", "--port", "8765"],
        )
