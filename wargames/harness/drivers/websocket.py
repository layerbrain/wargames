from __future__ import annotations

import json
from dataclasses import asdict

from wargames.harness.agent import AgentDecision, AgentObservation, ToolCall
from wargames.harness.agent_spec import AgentSpec
from wargames.episode.serialization import public_value


class WebSocketAgent:
    def __init__(self, spec: AgentSpec) -> None:
        self.spec = spec
        self.id = spec.id
        self._websocket = None

    async def start(self, task: object) -> None:
        try:
            import websockets
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("websockets is required for websocket agents") from exc
        self._websocket = await websockets.connect(self.spec.url)
        await self._websocket.send(json.dumps({"event": "start", "task": public_value(task)}))

    async def decide(self, obs: AgentObservation) -> AgentDecision:
        if self._websocket is None:
            raise RuntimeError("websocket agent has not started")
        await self._websocket.send(json.dumps({"event": "observe", "observation": public_value(asdict(obs))}))
        payload = json.loads(await self._websocket.recv())
        if payload.get("stop"):
            return AgentDecision(tool_call=None, stop=True, reason=payload.get("reason"))
        tool = payload.get("tool_call") or payload
        return AgentDecision(tool_call=ToolCall(name=str(tool["name"]), arguments=dict(tool.get("arguments", {}))))

    async def close(self) -> None:
        if self._websocket is not None:
            await self._websocket.close()
