from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from wargames.core.control.events import Target, WindowRect
from wargames.games.redalert.window import (
    _candidate_pids,
    _largest_window,
    _locate_x11_window_by_title,
    _normalize_target,
    _window_title_matches,
)


class RedAlertWindowTests(TestCase):
    def test_candidate_pids_include_launcher_children(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for pid, children in {10: "11 12", 11: "13", 12: "", 13: ""}.items():
                path = root / str(pid) / "task" / str(pid)
                path.mkdir(parents=True)
                (path / "children").write_text(children)

            self.assertEqual(_candidate_pids(10, root), (10, 11, 12, 13))

    def test_largest_window_selects_render_surface(self) -> None:
        tiny = object()
        render = object()
        selected, rect = _largest_window(
            [
                (tiny, WindowRect(0, 0, 1, 1)),
                (render, WindowRect(0, 0, 1280, 720)),
            ]
        )

        self.assertIs(selected, render)
        self.assertEqual((rect.width, rect.height), (1280, 720))

    def test_normalize_target_uses_root_when_pid_window_is_tiny(self) -> None:
        target = Target(pid=1, window_id=123, rect=WindowRect(0, 0, 1, 1), display=":99")
        normalized = _normalize_target(target, width=1280, height=720)

        self.assertIsNone(normalized.window_id)
        self.assertEqual((normalized.rect.width, normalized.rect.height), (1280, 720))

    def test_title_match_is_case_insensitive(self) -> None:
        self.assertTrue(_window_title_matches("FlightGear", "flightgear"))
        self.assertFalse(_window_title_matches(None, "flightgear"))

    def test_closed_x11_display_is_treated_as_missing_window(self) -> None:
        with patch("Xlib.display.Display", side_effect=RuntimeError("closed")):
            self.assertIsNone(_locate_x11_window_by_title(title="FlightGear", display=":99"))
