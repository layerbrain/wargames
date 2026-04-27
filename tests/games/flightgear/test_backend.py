import asyncio
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from wargames.core.control.cua import WaitAction
from wargames.core.control.events import Target, WindowRect
from wargames.core.control.injector import RecordingInjector, XTestInjector, XdotoolInjector
from wargames.games.flightgear.backend import (
    FlightGearBackend,
    FlightGearSession,
    _has_visible_pixels,
)
from wargames.games.flightgear.config import FlightGearConfig
from wargames.games.flightgear.missions import FlightGearMissionSpec


class FlightGearBackendTests(TestCase):
    def test_visible_frame_rejects_missing_file(self) -> None:
        self.assertFalse(_has_visible_pixels(Path("/missing"), "/usr/bin/identify"))

    def test_env_config_keeps_flightgear_startup_timeout(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(FlightGearConfig.from_env().step_timeout, 150.0)

        with patch.dict("os.environ", {"LAYERBRAIN_WARGAMES_STEP_TIMEOUT": "45"}, clear=True):
            self.assertEqual(FlightGearConfig.from_env().step_timeout, 45.0)

    def test_no_fallback_missions_without_catalog_or_runtime_data(self) -> None:
        with patch("wargames.games.flightgear.backend.discover", return_value=()):
            backend = FlightGearBackend(FlightGearConfig(missions_dir="/missing"))
            self.assertEqual(backend.missions(), ())

    def test_default_injector_is_xdotool(self) -> None:
        backend = FlightGearBackend(FlightGearConfig())
        target = Target(pid=1, window_id=2, rect=WindowRect(0, 0, 100, 100), display=":99")
        self.assertIsInstance(backend._injector_for(target), XdotoolInjector)

    def test_xtest_injector_is_explicit_native_path(self) -> None:
        backend = FlightGearBackend(FlightGearConfig(injector_transport="xtest"))
        target = Target(pid=1, window_id=2, rect=WindowRect(0, 0, 100, 100), display=":99")
        self.assertIsInstance(backend._injector_for(target), XTestInjector)


class FlightGearSessionTests(TestCase):
    def test_step_uses_same_cua_and_capture_contract_as_other_games(self) -> None:
        injector = RecordingInjector()
        session = FlightGearSession(
            id="s",
            mission=FlightGearMissionSpec(
                id="flightgear.test",
                title="T",
                game="flightgear",
                source="builtin",
            ),
            seed=1,
            target=Target(pid=1, window_id=2, rect=WindowRect(0, 0, 1280, 720), display=":99"),
            injector=injector,
            process=None,
            config=FlightGearConfig(),
        )

        result = asyncio.run(session.step(WaitAction(id="a")))

        self.assertEqual(result.tick, 1)
        self.assertFalse(result.finished)
        self.assertIsNotNone(result.hidden)
        self.assertEqual(len(injector.events), 1)

    def test_hidden_state_includes_flightgear_telemetry(self) -> None:
        values = {
            "/position/altitude-ft": "1700.5",
            "/velocities/airspeed-kt": "92.0",
            "/orientation/pitch-deg": "3.5",
            "/orientation/roll-deg": "-1.25",
            "/orientation/heading-deg": "282.0",
            "/velocities/vertical-speed-fps": "4.0",
            "/controls/engines/engine/throttle": "0.82",
            "/sim/crashed": "false",
        }
        with patch(
            "wargames.games.flightgear.backend.read_flightgear_property",
            side_effect=lambda path, **_: values[path],
        ):
            session = FlightGearSession(
                id="s",
                mission=FlightGearMissionSpec(
                    id="flightgear.test",
                    title="T",
                    game="flightgear",
                    source="builtin",
                ),
                seed=1,
                target=Target(pid=1, window_id=2, rect=WindowRect(0, 0, 1280, 720), display=":99"),
                injector=RecordingInjector(),
                process=None,
                config=FlightGearConfig(),
            )

        aircraft = session._last_hidden.world.aircraft
        self.assertEqual(aircraft.altitude_ft, 1700.5)
        self.assertEqual(aircraft.airspeed_kt, 92.0)
        self.assertFalse(aircraft.crashed)
