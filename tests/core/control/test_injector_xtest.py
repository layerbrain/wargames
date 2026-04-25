from unittest import TestCase

from wargames.core.control.events import MouseEvent, Target, WindowRect
from wargames.core.control.injector import _window_local_pointer, _x11_keysym, _x11_window_id


class XTestInjectorTests(TestCase):
    def test_keysym_accepts_arrow_aliases(self) -> None:
        self.assertGreater(_x11_keysym("ArrowUp"), 0)
        self.assertEqual(_x11_keysym("ArrowUp"), _x11_keysym("Up"))

    def test_keysym_rejects_unknown_keys(self) -> None:
        with self.assertRaises(ValueError):
            _x11_keysym("not-a-real-key")

    def test_window_id_accepts_hex_strings(self) -> None:
        self.assertEqual(_x11_window_id("0x600006"), 0x600006)

    def test_window_local_pointer_clamps_to_target_rect(self) -> None:
        target = Target(pid=1, window_id=2, rect=WindowRect(10, 20, 100, 80), display=":99")
        self.assertEqual(_window_local_pointer(target, MouseEvent(kind="move", x=60, y=70)), (50, 50))
        self.assertEqual(_window_local_pointer(target, MouseEvent(kind="move", x=0, y=200)), (0, 79))
