from unittest import TestCase

from wargames.core.control.cua import (
    KeyDownAction,
    KeyUpAction,
    MoveMouseAction,
    MouseDownAction,
    MouseUpAction,
    ScrollAction,
    WaitAction,
)


class CuaActionTests(TestCase):
    def test_all_actions_use_id(self) -> None:
        actions = (
            WaitAction(id="a", ms=10),
            MoveMouseAction(id="b", x=3, y=4),
            MouseDownAction(id="c"),
            MouseUpAction(id="d"),
            KeyDownAction(id="e", key="a"),
            KeyUpAction(id="f", key="a"),
            ScrollAction(id="g", dx=0, dy=1),
        )
        for action in actions:
            self.assertTrue(action.id)
            self.assertFalse(hasattr(action, "action" + "_id"))
