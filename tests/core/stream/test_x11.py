from unittest import TestCase
from unittest.mock import Mock, patch

from wargames.core.stream.x11 import X11StreamViewer, stop_stream_viewer


class X11StreamViewerTests(TestCase):
    def test_command_captures_xvfb_with_visible_virtual_pointer(self) -> None:
        command = X11StreamViewer(display=":99", resolution=(1024, 768), fps=20, title="WarGames test").command()
        self.assertIn("-f", command)
        self.assertIn("x11grab", command)
        self.assertIn("-draw_mouse", command)
        self.assertIn("1", command)
        self.assertIn("1024x768", command)
        self.assertIn(":99", command)
        self.assertIn("-noborder", command)

    def test_start_launches_ffplay(self) -> None:
        with patch("wargames.core.stream.x11.shutil.which", return_value="/usr/bin/ffplay"):
            with patch("wargames.core.stream.x11.subprocess.Popen") as popen:
                X11StreamViewer(display=":99", resolution=(640, 480), viewer_display=":0").start()
        command = popen.call_args.args[0]
        self.assertEqual(command[0], "ffplay")
        self.assertIn("-draw_mouse", command)
        self.assertEqual(popen.call_args.kwargs["env"]["DISPLAY"], ":0")

    def test_stop_terminates_running_viewer(self) -> None:
        process = Mock()
        process.poll.return_value = None
        stop_stream_viewer(process)
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=2)
