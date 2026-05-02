from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase

from wargames.core.process.launcher import ProcessLauncher


class LauncherTests(IsolatedAsyncioTestCase):
    async def test_starts_and_terminates_process(self) -> None:
        handle = await ProcessLauncher().start(
            ["python3", "-c", "import time; time.sleep(5)"], id="sleep"
        )
        self.assertGreater(handle.pid, 0)
        await handle.terminate(timeout=1)
        self.assertIsNotNone(handle.process.returncode)

    async def test_started_process_does_not_consume_parent_stdin(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "stdin.txt"
            handle = await ProcessLauncher().start(
                [
                    "python3",
                    "-c",
                    (
                        "import sys; "
                        f"open({str(output)!r}, 'w', encoding='utf-8').write(sys.stdin.readline())"
                    ),
                ],
                id="stdin-reader",
            )
            await handle.process.wait()

            self.assertEqual(output.read_text(encoding="utf-8"), "")
