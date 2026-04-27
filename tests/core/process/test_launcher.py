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
