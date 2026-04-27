from __future__ import annotations

import asyncio
import json

from wargames.harness.agent import AgentDecision, AgentObservation
from wargames.harness.agent_spec import AgentSpec
from wargames.episode.serialization import agent_observation_to_dict
from wargames.harness.turns import events_from_payload


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
        self._process.stdin.write((json.dumps(agent_observation_to_dict(obs)) + "\n").encode())
        await self._process.stdin.drain()
        line = await self._process.stdout.readline()
        if not line:
            return AgentDecision(stop=True, reason="subprocess_closed")
        payload = json.loads(line.decode())
        if isinstance(payload, dict) and payload.get("stop"):
            return AgentDecision(stop=True, reason=payload.get("reason"))
        return AgentDecision(events=events_from_payload(payload))

    async def close(self) -> None:
        if self._process is None or self._process.returncode is not None:
            return
        self._process.terminate()
        try:
            await asyncio.wait_for(self._process.wait(), timeout=2)
        except TimeoutError:
            self._process.kill()
            await self._process.wait()
