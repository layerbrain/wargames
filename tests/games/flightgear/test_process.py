from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from wargames.games.flightgear.config import FlightGearConfig
from wargames.games.flightgear.missions import FlightGearMissionSpec
from wargames.games.flightgear.process import (
    _parse_flightgear_property,
    flightgear_command,
    flightgear_environment,
    is_flightgear_ready,
    locate_fgfs,
)


class FlightGearProcessTests(TestCase):
    def test_locate_fgfs_from_registered_root(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary = root / "bin" / "fgfs"
            binary.parent.mkdir()
            binary.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

            self.assertEqual(locate_fgfs(FlightGearConfig(fgfs_root=str(root))), str(binary))

    def test_command_enables_property_interfaces_and_window_size(self) -> None:
        mission = FlightGearMissionSpec(
            id="flightgear.c172p-ksfo-pattern.debug",
            title="C172P KSFO Pattern",
            game="flightgear",
            source="builtin",
            aircraft="c172p",
            airport="KSFO",
            runway="28L",
            timeofday="noon",
            startup_args=("--in-air", "--altitude=1500"),
        )

        command = flightgear_command(
            "/usr/games/fgfs", mission, FlightGearConfig(window_size=(1024, 768))
        )

        self.assertIn("--aircraft=c172p", command)
        self.assertIn("--airport=KSFO", command)
        self.assertIn("--runway=28L", command)
        self.assertIn("--telnet=5501", command)
        self.assertIn("--httpd=5500", command)
        self.assertIn("--geometry=1024x768", command)
        self.assertIn("--disable-sound", command)
        self.assertIn("--disable-terrasync", command)
        self.assertIn("--in-air", command)
        self.assertIn("--altitude=1500", command)

    def test_command_uses_dbus_session_when_available(self) -> None:
        mission = FlightGearMissionSpec(
            id="flightgear.c172p-ksfo-pattern.debug",
            title="C172P KSFO Pattern",
            game="flightgear",
            source="builtin",
            aircraft="c172p",
            airport="KSFO",
        )

        with patch(
            "wargames.games.flightgear.process.shutil.which",
            return_value="/usr/bin/dbus-run-session",
        ):
            command = flightgear_command("/usr/games/fgfs", mission, FlightGearConfig())

        self.assertEqual(["/usr/bin/dbus-run-session", "--", "/usr/games/fgfs"], command[:3])

    def test_environment_keeps_flightgear_state_inside_runtime_cache(self) -> None:
        with patch.dict(
            "os.environ", {"LAYERBRAIN_WARGAMES_CACHE_DIR": "/opt/wargames-cache"}, clear=True
        ):
            env = flightgear_environment(FlightGearConfig(), display=":99")

        self.assertEqual(env["DISPLAY"], ":99")
        self.assertEqual(env["FG_HOME"], "/opt/wargames-cache/games/flightgear/home")
        self.assertIn("/opt/wargames-cache/games/flightgear/scenery", env["FG_SCENERY"])
        self.assertEqual(env["XDG_CACHE_HOME"], "/opt/wargames-cache/games/flightgear/xdg-cache")

    def test_parse_telnet_property_response(self) -> None:
        response = "Welcome to FlightGear\r\n/> /sim/startup/splash-alpha = '0' (double)\r\n/> "

        self.assertEqual("0", _parse_flightgear_property("/sim/startup/splash-alpha", response))

    def test_readiness_uses_fdm_and_finished_splash(self) -> None:
        values = {
            "/sim/signals/fdm-initialized": "true",
            "/sim/startup/splash-alpha": "0",
        }

        with patch(
            "wargames.games.flightgear.process.read_flightgear_property",
            side_effect=lambda path, **_: values[path],
        ):
            self.assertTrue(is_flightgear_ready(FlightGearConfig()))

        values["/sim/startup/splash-alpha"] = "1"
        with patch(
            "wargames.games.flightgear.process.read_flightgear_property",
            side_effect=lambda path, **_: values[path],
        ):
            self.assertFalse(is_flightgear_ready(FlightGearConfig()))
