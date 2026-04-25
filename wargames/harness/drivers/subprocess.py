from __future__ import annotations

import asyncio
import json
from dataclasses import asdict

from wargames.harness.agent import AgentDecision, AgentObservation, ToolCall
from wargames.harness.agent_spec import AgentSpec
from wargames.episode.serialization import public_value


class SubprocessAgent:
    def __init__(self, spec: AgentSpec) -> None:
        self.spec = spec
        self.id = spec.id
        self._process: asyncio.subprocess.Process | None = None

    async def start(self, task: object) -> None:
        self._process = await asyncio.create_subprocess_exec(
            *self.spec.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )

    async def decide(self, obs: AgentObservation) -> AgentDecision:
        if self._process is None or self._process.stdin is None or self._process.stdout is None:
            raise RuntimeError("subprocess agent has not started")
        self._process.stdin.write((json.dumps(public_value(asdict(obs))) + "\n").encode())
        await self._process.stdin.drain()
        line = await self._process.stdout.readline()
        if not line:
            return AgentDecision(tool_call=None, stop=True, reason="subprocess_closed")
        payload = json.loads(line.decode())
        if payload.get("stop"):
            return AgentDecision(tool_call=None, stop=True, reason=payload.get("reason"))
        tool = payload.get("tool_call") or payload
        return AgentDecision(tool_call=ToolCall(name=str(tool["name"]), arguments=dict(tool.get("arguments", {}))))

    async def close(self) -> None:
        if self._process is None or self._process.returncode is not None:
            return
        self._process.terminate()
        try:
            await asyncio.wait_for(self._process.wait(), timeout=2)
        except TimeoutError:
            self._process.kill()
            await self._process.wait()
