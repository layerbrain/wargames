import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase

from wargames.core.control.cua import WaitAction
from wargames.core.control.events import Target, WindowRect
from wargames.core.control.injector import RecordingInjector, XTestInjector, XdotoolInjector
from wargames.games.freeciv.backend import FreeCivBackend, FreeCivSession, _has_visible_pixels
from wargames.games.freeciv.config import FreeCivConfig
from wargames.games.freeciv.missions import FreeCivMissionSpec


class FakeServer:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.process = SimpleNamespace(returncode=None)
        self.turn = 1

    async def save(self, label: str, *, timeout: float) -> Path:
        self.turn += 1
        path = self.root / f"{label}.sav"
        path.write_text(_save(self.turn, gold=50 + self.turn), encoding="utf-8")
        return path

    async def terminate(self, timeout: float) -> None:
        self.process.returncode = 0


class FakeClient:
    def __init__(self) -> None:
        self.process = SimpleNamespace(returncode=None)

    async def terminate(self, timeout: float) -> None:
        self.process.returncode = 0


class FreeCivBackendTests(TestCase):
    def test_visible_frame_rejects_missing_file(self) -> None:
        self.assertFalse(_has_visible_pixels(Path("/missing"), "/usr/bin/identify"))

    def test_no_fallback_missions_without_catalog_or_runtime_data(self) -> None:
        backend = FreeCivBackend(FreeCivConfig(missions_dir="/missing", root="/missing"))
        self.assertEqual(backend.missions(), ())

    def test_default_injector_is_xdotool(self) -> None:
        backend = FreeCivBackend(FreeCivConfig())
        target = Target(pid=1, window_id=2, rect=WindowRect(0, 0, 100, 100), display=":99")
        self.assertIsInstance(backend._injector_for(target), XdotoolInjector)

    def test_xtest_injector_is_explicit_native_path(self) -> None:
        backend = FreeCivBackend(FreeCivConfig(injector_transport="xtest"))
        target = Target(pid=1, window_id=2, rect=WindowRect(0, 0, 100, 100), display=":99")
        self.assertIsInstance(backend._injector_for(target), XTestInjector)


class FreeCivSessionTests(TestCase):
    def test_step_saves_server_state_after_cua_input(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = root / "initial.sav"
            initial.write_text(_save(1, gold=50), encoding="utf-8")
            injector = RecordingInjector()
            session = FreeCivSession(
                id="s",
                mission=FreeCivMissionSpec(
                    id="freeciv.test",
                    title="T",
                    game="freeciv",
                    source="builtin",
                    time_limit_ticks=10,
                    scenario_file="test.sav.gz",
                ),
                seed=1,
                target=Target(pid=1, window_id=2, rect=WindowRect(0, 0, 1280, 720), display=":99"),
                injector=injector,
                server=FakeServer(root),
                client=FakeClient(),
                config=FreeCivConfig(action_settle_seconds=0.0),
                initial_save=initial,
            )

            result = asyncio.run(session.step(WaitAction(id="a")))

        self.assertEqual(result.tick, 2)
        self.assertFalse(result.finished)
        self.assertIsNotNone(result.hidden)
        self.assertEqual(result.hidden.world.us.gold, 52)
        self.assertEqual(len(injector.events), 1)


def _save(turn: int, *, gold: int) -> str:
    return f"""
[game]
server_state="S_S_RUNNING"
turn={turn}
year=-4000

[player0]
name="Player"
username="wargames"
nation="Romans"
government_name="Despotism"
is_alive=TRUE
gold={gold}
ncities=0
nunits=1

[player1]
name="AI"
username="Unassigned"
flags="ai"
is_alive=TRUE
gold=50
ncities=0
nunits=1
"""
