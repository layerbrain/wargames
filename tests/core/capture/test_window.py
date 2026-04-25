import subprocess
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from wargames.core.capture.window import ScreenRegionCapture
from wargames.core.control.events import Target, WindowRect


class ScreenRegionCaptureTests(IsolatedAsyncioTestCase):
    async def test_normalize_dimensions_preserves_aspect_ratio(self) -> None:
        capture = ScreenRegionCapture("/tmp/wargames-test")
        target = Target(pid=1, window_id=None, rect=WindowRect(0, 0, 1280, 720), display=":99")

        with patch("wargames.core.capture.window.shutil.which", return_value="/usr/bin/convert"):
            with patch("wargames.core.capture.window.subprocess.run") as run:
                await capture._normalize_dimensions(target, Path("/tmp/frame.png"))

        command = run.call_args.args[0]
        self.assertEqual(command[:4], ["/usr/bin/convert", "/tmp/frame.png", "-resize", "1280x720"])
        self.assertIn("-extent", command)
        self.assertIn("1280x720", command)
        self.assertNotIn("1280x720!", command)
        self.assertEqual(run.call_args.kwargs["check"], True)
        self.assertEqual(run.call_args.kwargs["stdout"], subprocess.DEVNULL)
