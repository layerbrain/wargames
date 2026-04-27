from __future__ import annotations

import asyncio
import os
import signal
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass

ReadinessPredicate = Callable[[], bool | Awaitable[bool]]


@dataclass
class ProcessHandle:
    id: str
    process: asyncio.subprocess.Process
    command: tuple[str, ...]
    env: Mapping[str, str]

    @property
    def pid(self) -> int:
        if self.process.pid is None:
            raise RuntimeError("process has no pid")
        return self.process.pid

    async def terminate(self, timeout: float = 5.0) -> None:
        if self.process.returncode is not None:
            return
        try:
            os.killpg(self.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        except Exception:
            self.process.terminate()
        try:
            await asyncio.wait_for(self.process.wait(), timeout=timeout)
        except TimeoutError:
            try:
                os.killpg(self.pid, signal.SIGKILL)
            except ProcessLookupError:
                return
            except Exception:
                self.process.kill()
            await self.process.wait()


class ProcessLauncher:
    async def start(
        self,
        command: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
        ready: ReadinessPredicate | None = None,
        timeout: float = 30.0,
        id: str = "process",
    ) -> ProcessHandle:
        merged_env = {**os.environ, **(env or {})}
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            env=merged_env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
        handle = ProcessHandle(id=id, process=process, command=tuple(command), env=merged_env)
        if ready is not None:
            await self._wait_ready(ready, timeout)
        return handle

    async def _wait_ready(self, ready: ReadinessPredicate, timeout: float) -> None:
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            result = ready()
            if asyncio.iscoroutine(result):
                result = await result
            if result:
                return
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("process did not become ready before timeout")
            await asyncio.sleep(0.05)
