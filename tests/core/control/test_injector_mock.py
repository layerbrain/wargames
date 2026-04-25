from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from wargames.core.control.cua import ClickAction
from wargames.core.control.events import MouseEvent, Target, WindowRect
from wargames.core.control.injector import RecordingInjector, XdotoolInjector
from wargames.core.control.lower import lower_cua


class RecordingInjectorTests(IsolatedAsyncioTestCase):
    async def test_records_targeted_events(self) -> None:
        target = Target(pid=1, window_id=2, rect=WindowRect(0, 0, 100, 100))
        injector = RecordingInjector()
        await injector.send_many(target, lower_cua(ClickAction(id="a", x=1, y=1), target.rect))
        self.assertEqual(len(injector.events), 3)
        self.assertTrue(all(item[0] == target for item in injector.events))


class XdotoolInjectorTests(IsolatedAsyncioTestCase):
    async def test_button_command_places_window_after_action(self) -> None:
        target = Target(pid=1, window_id=2, rect=WindowRect(0, 0, 100, 100), display=":99")
        with patch("wargames.core.control.injector.subprocess.run") as run:
            await XdotoolInjector().send(target, MouseEvent(kind="down", x=10, y=10))

        self.assertEqual(run.call_args.args[0], ["xdotool", "mousedown", "--window", "2", "1"])

    async def test_button_command_can_target_root_pointer(self) -> None:
        target = Target(pid=1, window_id=None, rect=WindowRect(0, 0, 100, 100), display=":99")
        with patch("wargames.core.control.injector.subprocess.run") as run:
            await XdotoolInjector().send(target, MouseEvent(kind="down", x=10, y=10))

        self.assertEqual(run.call_args.args[0], ["xdotool", "mousedown", "1"])
