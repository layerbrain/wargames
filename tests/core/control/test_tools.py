from unittest import TestCase

from wargames.core.control.cua import ClickAction, WaitAction
from wargames.core.control.tools import CUA_TOOL_SPECS, action_from_tool_call


class CUAToolTests(TestCase):
    def test_specs_expose_integer_coordinates(self) -> None:
        click = next(tool for tool in CUA_TOOL_SPECS if tool.name == "click")
        self.assertEqual(click.parameters["properties"]["x"]["type"], "integer")
        self.assertEqual(click.parameters["properties"]["y"]["type"], "integer")

    def test_rejects_normalized_float_coordinates(self) -> None:
        with self.assertRaises(ValueError):
            action_from_tool_call("click", {"x": 0.5, "y": 100})

    def test_rejects_unknown_arguments(self) -> None:
        with self.assertRaises(ValueError):
            action_from_tool_call("wait", {"seconds": 2})

    def test_builds_click_and_one_tick_wait(self) -> None:
        click = action_from_tool_call("click", {"x": 10, "y": 12})
        wait = action_from_tool_call("wait", {})
        self.assertIsInstance(click, ClickAction)
        self.assertIsInstance(wait, WaitAction)
        self.assertEqual(wait.ticks, 1)
