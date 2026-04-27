from unittest import TestCase

from wargames.core.control.cua import (
    KeyDownAction,
    KeyUpAction,
    MouseDownAction,
    MouseUpAction,
    MoveMouseAction,
    WaitAction,
)
from wargames.core.control.events import KeyEvent, MouseEvent, WaitEvent, WindowRect
from wargames.core.control.lower import lower_cua


class LowerCuaTests(TestCase):
    def test_move_mouse_is_a_pure_move(self) -> None:
        events = tuple(lower_cua(MoveMouseAction(id="a", x=5, y=6), WindowRect(10, 20, 100, 100)))
        self.assertEqual(events, (MouseEvent(kind="move", x=15, y=26),))

    def test_mouse_buttons_are_primitive_current_pointer_events(self) -> None:
        self.assertEqual(
            tuple(lower_cua(MouseDownAction(id="a"), WindowRect(10, 20, 100, 100))),
            (MouseEvent(kind="down"),),
        )
        self.assertEqual(
            tuple(lower_cua(MouseUpAction(id="a", button="right"), WindowRect(10, 20, 100, 100))),
            (MouseEvent(kind="up", button="right"),),
        )

    def test_key_actions_are_primitive_down_and_up_events(self) -> None:
        self.assertEqual(
            tuple(lower_cua(KeyDownAction(id="a", key="PageUp"), WindowRect(0, 0, 1, 1))),
            (KeyEvent(kind="down", key="PageUp"),),
        )
        self.assertEqual(
            tuple(lower_cua(KeyUpAction(id="a", key="PageUp"), WindowRect(0, 0, 1, 1))),
            (KeyEvent(kind="up", key="PageUp"),),
        )

    def test_wait_lowers_to_wait_event(self) -> None:
        self.assertEqual(
            tuple(lower_cua(WaitAction(id="a", ms=1000), WindowRect(0, 0, 1, 1))),
            (WaitEvent(ms=1000),),
        )
        self.assertEqual(
            tuple(lower_cua(WaitAction(id="a"), WindowRect(0, 0, 1, 1))),
            (WaitEvent(),),
        )
