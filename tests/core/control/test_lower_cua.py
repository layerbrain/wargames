from unittest import TestCase

from wargames.core.control.cua import ClickAction, DragAction, MoveMouseAction, WaitAction
from wargames.core.control.events import MouseEvent, WaitEvent, WindowRect
from wargames.core.control.lower import lower_cua


class LowerCuaTests(TestCase):
    def test_click_is_anchored_to_window_rect(self) -> None:
        events = tuple(lower_cua(ClickAction(id="a", x=5, y=6), WindowRect(10, 20, 100, 100)))
        self.assertEqual(events[0], MouseEvent(kind="move", x=15, y=26))
        self.assertEqual(events[1], MouseEvent(kind="down", x=15, y=26))
        self.assertEqual(events[2], MouseEvent(kind="up", x=15, y=26))

    def test_drag_has_down_move_up(self) -> None:
        events = tuple(lower_cua(DragAction(id="a", start_x=1, start_y=2, end_x=3, end_y=4), WindowRect(0, 0, 10, 10)))
        self.assertEqual(events[0].kind, "move")
        self.assertEqual(events[1].kind, "down")
        self.assertEqual(events[-1].kind, "up")
        self.assertGreaterEqual([event.kind for event in events].count("move"), 8)

    def test_move_mouse_is_a_pure_move(self) -> None:
        events = tuple(lower_cua(MoveMouseAction(id="a", x=5, y=6), WindowRect(10, 20, 100, 100)))
        self.assertEqual(events, (MouseEvent(kind="move", x=15, y=26),))

    def test_wait_lowers_to_wait_event(self) -> None:
        self.assertEqual(tuple(lower_cua(WaitAction(id="a", ticks=3), WindowRect(0, 0, 1, 1))), (WaitEvent(ticks=3),))
