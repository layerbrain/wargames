from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from wargames.core.capture.window import NullWindowCapture, ScreenRegionCapture
from wargames.core.control.events import Target, WindowRect


class CaptureTests(IsolatedAsyncioTestCase):
    async def test_null_capture_preserves_dimensions(self) -> None:
        frame = await NullWindowCapture().capture(
            Target(pid=None, window_id=None, rect=WindowRect(0, 0, 20, 30)), tick=4
        )
        self.assertEqual((frame.width, frame.height, frame.captured_tick), (20, 30, 4))

    async def test_screen_capture_reads_dedicated_xvfb_root(self) -> None:
        process = AsyncMock()
        process.wait.return_value = 0
        target = Target(pid=1, window_id=123, rect=WindowRect(0, 0, 1280, 720), display=":99")
        with patch("wargames.core.capture.window.shutil.which", return_value="/usr/bin/import"):
            with patch(
                "wargames.core.capture.window.asyncio.create_subprocess_exec", return_value=process
            ) as create:
                await ScreenRegionCapture("/tmp/wargames-test")._capture_linux(
                    target, "/tmp/frame.png"
                )  # type: ignore[arg-type]
        self.assertEqual(
            create.call_args.args, ("/usr/bin/import", "-window", "root", "/tmp/frame.png")
        )
        self.assertEqual(create.call_args.kwargs["env"]["DISPLAY"], ":99")
