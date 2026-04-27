from unittest import TestCase

from wargames.core.control.cua import MouseDownAction, MoveMouseAction, WaitAction
from wargames.core.control.tools import CUA_TOOL_SPECS, action_from_tool_call


class CUAToolTests(TestCase):
    def test_specs_expose_integer_coordinates(self) -> None:
        move = next(tool for tool in CUA_TOOL_SPECS if tool.name == "move_mouse")
        self.assertEqual(move.parameters["properties"]["x"]["type"], "integer")
        self.assertEqual(move.parameters["properties"]["y"]["type"], "integer")

    def test_rejects_normalized_float_coordinates(self) -> None:
        with self.assertRaises(ValueError):
            action_from_tool_call("move_mouse", {"x": 0.5, "y": 100})

    def test_rejects_unknown_arguments(self) -> None:
        with self.assertRaises(ValueError):
            action_from_tool_call("wait", {"seconds": 2})

    def test_builds_primitive_actions_and_default_wait(self) -> None:
        move = action_from_tool_call("move_mouse", {"x": 10, "y": 12})
        mouse_down = action_from_tool_call("mouse_down", {})
        wait = action_from_tool_call("wait", {})
        self.assertIsInstance(move, MoveMouseAction)
        self.assertIsInstance(mouse_down, MouseDownAction)
        self.assertIsInstance(wait, WaitAction)
        self.assertEqual(wait.ms, 0)

    def test_rejects_removed_convenience_actions(self) -> None:
        with self.assertRaises(ValueError):
            action_from_tool_call("click", {"x": 10, "y": 12})

    def test_wait_accepts_ms(self) -> None:
        wait = action_from_tool_call("wait", {"ms": 1000})
        self.assertEqual(wait.ms, 1000)

    def test_wait_rejects_legacy_ticks(self) -> None:
        with self.assertRaises(ValueError):
            action_from_tool_call("wait", {"ticks": 1})

    def test_rejects_unknown_public_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown key"):
            action_from_tool_call("key_down", {"key": "Control_L"})
