from __future__ import annotations

import json

from wargames.harness.agent import AgentDecision, AgentObservation
from wargames.harness.agent_spec import AgentSpec
from wargames.episode.serialization import agent_observation_to_dict, public_value
from wargames.harness.turns import events_from_payload


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
        await self._websocket.send(
            json.dumps({"event": "observe", "observation": agent_observation_to_dict(obs)})
        )
        payload = json.loads(await self._websocket.recv())
        if isinstance(payload, dict) and payload.get("stop"):
            return AgentDecision(stop=True, reason=payload.get("reason"))
        return AgentDecision(events=events_from_payload(payload))

    async def close(self) -> None:
        if self._websocket is not None:
            await self._websocket.close()
