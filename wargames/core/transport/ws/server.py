from __future__ import annotations

import asyncio
import base64
import inspect
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - import error is raised when constructing the app.
    FastAPI = WebSocket = WebSocketDisconnect = None  # type: ignore[assignment]

from wargames.core.backend.base import Backend
from wargames.core.capture.frame import Frame
from wargames.core.config import WarGamesConfig
from wargames.core.missions.spec import MissionSpec
from wargames.core.runtime.arena import GameDescriptor, WarGames
from wargames.core.runtime.lobby import Lobby
from wargames.core.runtime.mission import Mission
from wargames.core.runtime.observation import Observation
from wargames.core.transport.ws.protocol import SessionMode
from wargames.harness.turns import event_from_mapping, validate_turn


BackendFactory = Callable[[WarGamesConfig], Backend]
LobbyFactory = Callable[..., Lobby]


@dataclass
class _SessionRecord:
    id: str
    wg: WarGames
    mission: Mission
    mission_spec: MissionSpec
    mode: SessionMode
    owner: Any
    stream_task: asyncio.Task[None] | None = None


class WSApplication:
    def __init__(
        self,
        *,
        game: GameDescriptor,
        backend_factory: BackendFactory | None = None,
        lobby_factory: LobbyFactory | None = None,
    ) -> None:
        self.game = game
        self.backend_factory = backend_factory
        self.lobby_factory = lobby_factory
        self._sessions: dict[str, _SessionRecord] = {}
        self._lobbies: dict[str, Lobby] = {}
        self._lobby_subscribers: dict[str, set[Any]] = {}
        self.fastapi_app = self._build_fastapi()

    def _build_fastapi(self) -> Any:
        if FastAPI is None or WebSocket is None or WebSocketDisconnect is None:
            raise RuntimeError("fastapi is required for the WarGames WS transport")

        api = FastAPI(title=f"wargames-{self.game.id}-ws")

        @api.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket) -> None:
            await websocket.accept()
            try:
                while True:
                    payload = await websocket.receive_json()
                    await self._dispatch(websocket, dict(payload))
            except WebSocketDisconnect:
                await self._cleanup_socket(websocket)

        return api

    async def _dispatch(self, websocket: Any, payload: dict[str, Any]) -> None:
        op = str(payload.get("op", ""))
        try:
            if op == "create_session":
                await self._create_session(websocket, payload)
            elif op == "observe":
                await self._observe(websocket, payload)
            elif op == "act":
                await self._act(websocket, payload)
            elif op == "subscribe_frames":
                await self._subscribe_frames(websocket, payload)
            elif op == "unsubscribe_frames":
                await self._unsubscribe_frames(websocket, payload)
            elif op == "delete":
                await self._delete(websocket, payload)
            elif op == "create_lobby":
                await self._create_lobby(websocket, payload)
            elif op == "subscribe_lobby":
                await self._subscribe_lobby(websocket, payload)
            elif op == "join_lobby":
                await self._join_lobby(websocket, payload)
            elif op == "leave_lobby":
                await self._leave_lobby(websocket, payload)
            elif op == "select_faction":
                await self._select_faction(websocket, payload)
            elif op == "set_ready":
                await self._set_ready(websocket, payload)
            elif op == "start_lobby":
                await self._start_lobby(websocket, payload)
            elif op == "begin_lobby":
                await self._begin_lobby(websocket, payload)
            elif op == "close_lobby":
                await self._close_lobby(websocket, payload)
            else:
                await self._error(websocket, op or "unknown", "unknown_op", f"unknown op: {op}")
        except Exception as exc:
            await self._error(websocket, op, exc.__class__.__name__, str(exc))

    async def _create_session(self, websocket: Any, payload: dict[str, Any]) -> None:
        mission_id = str(payload["mission"])
        seed = int(payload.get("seed", 0))
        mode: SessionMode = str(payload.get("mode", "sampled"))  # type: ignore[assignment]
        if mode not in {"sampled", "streaming"}:
            raise ValueError("mode must be sampled or streaming")
        config = replace(self.game.config_cls.from_env(), capture_frames=True)
        backend = (
            self.backend_factory(config) if self.backend_factory else self.game.backend_cls(config)
        )
        wg = WarGames(backend)
        await wg.__aenter__()
        mission = await wg.start_mission(mission_id, seed=seed)
        mission_spec = mission.session.mission
        session_id = uuid.uuid4().hex
        self._sessions[session_id] = _SessionRecord(
            id=session_id,
            wg=wg,
            mission=mission,
            mission_spec=mission_spec,
            mode=mode,
            owner=websocket,
        )
        observation = await mission.observe()
        await websocket.send_json(
            {
                "event": "session_created",
                "session_id": session_id,
                "game": self.game.id,
                "mission": mission_spec.id,
                "mode": mode,
                "phase": "running",
                "capabilities": {"launch_modes": ["direct", "menu"], "transport": "ws-v1"},
                "frame_size": self._frame_size(observation.frame),
            }
        )

    async def _observe(self, websocket: Any, payload: dict[str, Any]) -> None:
        session = self._session(payload)
        observation = await session.mission.observe()
        await websocket.send_json(
            {
                "event": "observation",
                "session_id": session.id,
                "tick": self._observation_tick(observation),
                "frame": self._frame_payload(observation.frame),
            }
        )

    async def _act(self, websocket: Any, payload: dict[str, Any]) -> None:
        session = self._session(payload)
        raw_events = payload["events"]
        if not isinstance(raw_events, list):
            raise ValueError("events must be an array")
        events = validate_turn(event_from_mapping(item) for item in raw_events)
        result = None
        events_applied = 0
        for event in events:
            action = self.game.action_from_tool_call(event.name, event.arguments)
            result = await session.mission.step(action)
            events_applied += 1
            if result.finished or result.truncated:
                break
        if result is None:
            raise ValueError("turn must contain at least one event")
        await websocket.send_json(
            {
                "event": "action_result",
                "session_id": session.id,
                "tick": result.tick,
                "finished": result.finished,
                "truncated": result.truncated,
                "frame": self._frame_payload(result.frame),
                "events_applied": events_applied,
            }
        )

    async def _subscribe_frames(self, websocket: Any, payload: dict[str, Any]) -> None:
        session = self._session(payload)
        fps = int(payload.get("fps", 10))
        if fps < 1 or fps > 60:
            raise ValueError("fps must be between 1 and 60")
        await self._stop_stream(session)
        session.stream_task = asyncio.create_task(self._stream_frames(session, websocket, fps))
        await websocket.send_json(
            {"event": "frames_subscribed", "session_id": session.id, "fps": fps}
        )

    async def _unsubscribe_frames(self, websocket: Any, payload: dict[str, Any]) -> None:
        session = self._session(payload)
        await self._stop_stream(session)
        await websocket.send_json({"event": "frames_unsubscribed", "session_id": session.id})

    async def _delete(self, websocket: Any, payload: dict[str, Any]) -> None:
        session = self._sessions.pop(str(payload["session_id"]), None)
        if session is None:
            return
        await self._stop_stream(session)
        await session.mission.close()
        await session.wg.close()
        await websocket.send_json({"event": "session_deleted", "session_id": session.id})

    async def _stream_frames(self, session: _SessionRecord, websocket: Any, fps: int) -> None:
        interval = 1.0 / fps
        while True:
            observation = await session.mission.observe()
            await websocket.send_json(
                {
                    "event": "frame",
                    "session_id": session.id,
                    "tick": self._observation_tick(observation),
                    "frame": self._frame_payload(observation.frame),
                }
            )
            await asyncio.sleep(interval)

    async def _create_lobby(self, websocket: Any, payload: dict[str, Any]) -> None:
        if self.lobby_factory is None:
            raise ValueError("this game does not expose a lobby factory")
        mission = self._mission(str(payload["mission"]))
        slots = int(payload.get("slots", getattr(mission, "player_slots", 2)))
        if hasattr(mission, "player_slots"):
            mission = replace(mission, player_slots=slots)
        lobby = self.lobby_factory(
            config=self.game.config_cls.from_env(),
            mission=mission,
            seed=int(payload.get("seed", 0)),
        )
        lobby_id = uuid.uuid4().hex
        self._lobbies[lobby_id] = lobby
        self._lobby_subscribers[lobby_id] = {websocket}
        await websocket.send_json(
            {"event": "lobby_created", "lobby_id": lobby_id, "snapshot": lobby.snapshot()}
        )

    async def _subscribe_lobby(self, websocket: Any, payload: dict[str, Any]) -> None:
        lobby_id = str(payload["lobby_id"])
        lobby = self._lobbies[lobby_id]
        self._lobby_subscribers.setdefault(lobby_id, set()).add(websocket)
        await websocket.send_json(
            {"event": "lobby_state", "lobby_id": lobby_id, "snapshot": lobby.snapshot()}
        )

    async def _join_lobby(self, websocket: Any, payload: dict[str, Any]) -> None:
        lobby_id = str(payload["lobby_id"])
        lobby = self._lobbies[lobby_id]
        slot = lobby.join(str(payload["name"]), payload.get("faction"))
        await websocket.send_json({"event": "lobby_joined", "lobby_id": lobby_id, "slot": slot})
        await self._broadcast_lobby(lobby_id)

    async def _leave_lobby(self, websocket: Any, payload: dict[str, Any]) -> None:
        lobby_id = str(payload["lobby_id"])
        self._lobbies[lobby_id].leave(str(payload["slot"]))
        await self._broadcast_lobby(lobby_id)

    async def _select_faction(self, websocket: Any, payload: dict[str, Any]) -> None:
        lobby_id = str(payload["lobby_id"])
        self._lobbies[lobby_id].select_faction(str(payload["slot"]), str(payload["faction"]))
        await self._broadcast_lobby(lobby_id)

    async def _set_ready(self, websocket: Any, payload: dict[str, Any]) -> None:
        lobby_id = str(payload["lobby_id"])
        self._lobbies[lobby_id].set_ready(str(payload["slot"]), bool(payload["ready"]))
        await self._broadcast_lobby(lobby_id)

    async def _start_lobby(self, websocket: Any, payload: dict[str, Any]) -> None:
        lobby_id = str(payload["lobby_id"])
        lobby = self._lobbies[lobby_id]
        await lobby.start()
        sessions: dict[str, str] = {}
        for slot, backend_session in lobby.sessions.items():
            session_id = uuid.uuid4().hex
            mission = Mission(backend_session)
            self._sessions[session_id] = _SessionRecord(
                id=session_id,
                wg=WarGames(lobby.backend),  # type: ignore[attr-defined]
                mission=mission,
                mission_spec=backend_session.mission,
                mode=str(payload.get("mode", "sampled")),  # type: ignore[arg-type]
                owner=websocket,
            )
            sessions[slot] = session_id
        await self._broadcast_lobby(lobby_id)
        await self._broadcast(
            lobby_id,
            {
                "event": "lobby_ready",
                "lobby_id": lobby_id,
                "sessions": sessions,
                "snapshot": lobby.snapshot(),
            },
        )

    async def _begin_lobby(self, websocket: Any, payload: dict[str, Any]) -> None:
        lobby_id = str(payload["lobby_id"])
        lobby = self._lobbies[lobby_id]
        await lobby.begin()
        await self._broadcast(
            lobby_id,
            {"event": "lobby_started", "lobby_id": lobby_id, "snapshot": lobby.snapshot()},
        )

    async def _close_lobby(self, websocket: Any, payload: dict[str, Any]) -> None:
        lobby_id = str(payload["lobby_id"])
        lobby = self._lobbies.pop(lobby_id)
        await lobby.close()
        await self._broadcast(lobby_id, {"event": "lobby_closed", "lobby_id": lobby_id})
        self._lobby_subscribers.pop(lobby_id, None)

    async def _broadcast_lobby(self, lobby_id: str) -> None:
        lobby = self._lobbies[lobby_id]
        await self._broadcast(
            lobby_id, {"event": "lobby_state", "lobby_id": lobby_id, "snapshot": lobby.snapshot()}
        )

    async def _broadcast(self, lobby_id: str, event: dict[str, Any]) -> None:
        for websocket in tuple(self._lobby_subscribers.get(lobby_id, ())):
            await websocket.send_json(event)

    async def _cleanup_socket(self, websocket: Any) -> None:
        for session_id, session in tuple(self._sessions.items()):
            if session.owner is websocket:
                await self._stop_stream(session)
                await session.mission.close()
                await session.wg.close()
                self._sessions.pop(session_id, None)
        for subscribers in self._lobby_subscribers.values():
            subscribers.discard(websocket)

    async def _stop_stream(self, session: _SessionRecord) -> None:
        if session.stream_task is None:
            return
        session.stream_task.cancel()
        try:
            await session.stream_task
        except asyncio.CancelledError:
            pass
        session.stream_task = None

    async def _error(self, websocket: Any, op: str, code: str, message: str) -> None:
        await websocket.send_json({"event": "error", "op": op, "code": code, "message": message})

    def _mission(self, mission_id: str) -> MissionSpec:
        config = self.game.config_cls.from_env()
        backend = (
            self.backend_factory(config) if self.backend_factory else self.game.backend_cls(config)
        )
        for mission in backend.missions():
            if mission.id == mission_id:
                return mission
        raise KeyError(f"unknown mission: {mission_id}")

    def _session(self, payload: dict[str, Any]) -> _SessionRecord:
        return self._sessions[str(payload["session_id"])]

    def _observation_tick(self, observation: Observation) -> int:
        return observation.frame.captured_tick if observation.frame else 0

    def _frame_size(self, frame: Frame | None) -> dict[str, int] | None:
        if frame is None:
            return None
        return {"width": frame.width, "height": frame.height}

    def _frame_payload(self, frame: Frame | None) -> dict[str, Any] | None:
        if frame is None:
            return None
        payload: dict[str, Any] = {
            "id": frame.id,
            "mime": frame.mime,
            "width": frame.width,
            "height": frame.height,
        }
        if frame.image_b64:
            payload["image_b64"] = frame.image_b64
        elif frame.image_path:
            payload["image_b64"] = base64.b64encode(Path(frame.image_path).read_bytes()).decode()
        return payload

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> Any:
        result = self.fastapi_app(scope, receive, send)
        if inspect.isawaitable(result):
            return await result
        return result


def build_ws_app(
    game: GameDescriptor,
    *,
    backend_factory: BackendFactory | None = None,
    lobby_factory: LobbyFactory | None = None,
) -> WSApplication:
    return WSApplication(game=game, backend_factory=backend_factory, lobby_factory=lobby_factory)
