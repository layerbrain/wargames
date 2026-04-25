from unittest import TestCase

from wargames.core.control.cua import (
    ClickAction,
    DragAction,
    KeyAction,
    MoveMouseAction,
    ScrollAction,
    TypeTextAction,
    WaitAction,
)


class CuaActionTests(TestCase):
    def test_all_actions_use_id(self) -> None:
        actions = (
            WaitAction(id="a", ticks=1),
            ClickAction(id="b", x=1, y=2),
            MoveMouseAction(id="c", x=3, y=4),
            DragAction(id="d", start_x=1, start_y=2, end_x=3, end_y=4),
            KeyAction(id="e", key="a"),
            TypeTextAction(id="f", text="hi"),
            ScrollAction(id="g", dx=0, dy=1),
        )
        for action in actions:
            self.assertTrue(action.id)
            self.assertFalse(hasattr(action, "action" + "_id"))
