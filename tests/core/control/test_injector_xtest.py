from unittest import TestCase

from wargames.core.control.injector import _x11_keysym, _x11_window_id


class XTestInjectorTests(TestCase):
    def test_keysym_accepts_arrow_aliases(self) -> None:
        self.assertGreater(_x11_keysym("ArrowUp"), 0)

    def test_keysym_rejects_unknown_keys(self) -> None:
        with self.assertRaises(ValueError):
            _x11_keysym("not-a-real-key")
        with self.assertRaises(ValueError):
            _x11_keysym("Up")

    def test_keysym_accepts_modifier_aliases_as_keys(self) -> None:
        self.assertGreater(_x11_keysym("Control"), 0)
        self.assertGreater(_x11_keysym("PageUp"), 0)

    def test_window_id_accepts_hex_strings(self) -> None:
        self.assertEqual(_x11_window_id("0x600006"), 0x600006)
