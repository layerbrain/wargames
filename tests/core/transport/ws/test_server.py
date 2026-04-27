from __future__ import annotations

from unittest import TestCase

from fastapi.testclient import TestClient

from tests.games.redalert.doubles import make_test_backend
from wargames.core.transport.ws import build_ws_app
from wargames.games.redalert import GAME
from wargames.games.redalert.lobby import RedAlertLobby


def _lobby_factory(*, config, mission, seed):
    return RedAlertLobby(
        config=config, mission=mission, seed=seed, backend_factory=make_test_backend
    )


def _app():
    return build_ws_app(
        GAME, backend_factory=make_test_backend, lobby_factory=_lobby_factory
    ).fastapi_app


def _contains_key(value: object, keys: set[str]) -> bool:
    if isinstance(value, dict):
        return any(key in value for key in keys) or any(
            _contains_key(item, keys) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_key(item, keys) for item in value)
    return False


class WSServerTests(TestCase):
    def test_sampled_lifecycle(self) -> None:
        with TestClient(_app()).websocket_connect("/ws") as ws:
            ws.send_json(
                {
                    "op": "create_session",
                    "mission": "redalert.soviet-01.normal",
                    "seed": 1,
                    "mode": "sampled",
                }
            )
            created = ws.receive_json()
            self.assertEqual(created["event"], "session_created")
            self.assertNotIn("tools", created)
            session_id = created["session_id"]

            ws.send_json({"op": "observe", "session_id": session_id})
            observation = ws.receive_json()
            self.assertEqual(observation["event"], "observation")
            self.assertIsNotNone(observation["frame"]["image_b64"])

            ws.send_json(
                {
                    "op": "act",
                    "session_id": session_id,
                    "events": [{"name": "wait", "arguments": {}}],
                }
            )
            result = ws.receive_json()
            self.assertEqual(result["event"], "action_result")
            self.assertEqual(result["tick"], 1)
            self.assertEqual(result["events_applied"], 1)

            ws.send_json({"op": "delete", "session_id": session_id})
            self.assertEqual(ws.receive_json()["event"], "session_deleted")

    def test_invalid_event_returns_error_event(self) -> None:
        with TestClient(_app()).websocket_connect("/ws") as ws:
            ws.send_json({"op": "create_session", "mission": "redalert.soviet-01.normal"})
            session_id = ws.receive_json()["session_id"]
            ws.send_json(
                {
                    "op": "act",
                    "session_id": session_id,
                    "events": [{"name": "move_mouse", "arguments": {"x": 0.5, "y": 4}}],
                }
            )
            error = ws.receive_json()
            self.assertEqual(error["event"], "error")
            self.assertIn("integer", error["message"])

    def test_act_accepts_event_array(self) -> None:
        with TestClient(_app()).websocket_connect("/ws") as ws:
            ws.send_json({"op": "create_session", "mission": "redalert.soviet-01.normal"})
            session_id = ws.receive_json()["session_id"]
            ws.send_json(
                {
                    "op": "act",
                    "session_id": session_id,
                    "events": [
                        {"name": "wait", "arguments": {}},
                        {"name": "wait", "arguments": {}},
                    ],
                }
            )

            result = ws.receive_json()

        self.assertEqual(result["event"], "action_result")
        self.assertEqual(result["tick"], 2)
        self.assertEqual(result["events_applied"], 2)

    def test_hidden_state_never_on_wire(self) -> None:
        with TestClient(_app()).websocket_connect("/ws") as ws:
            ws.send_json({"op": "create_session", "mission": "redalert.soviet-01.normal"})
            created = ws.receive_json()
            ws.send_json(
                {
                    "op": "act",
                    "session_id": created["session_id"],
                    "events": [{"name": "wait", "arguments": {}}],
                }
            )
            result = ws.receive_json()
            self.assertFalse(_contains_key(result, {"hidden", "prev_hidden", "world", "units"}))

    def test_streaming_pushes_frames(self) -> None:
        with TestClient(_app()).websocket_connect("/ws") as ws:
            ws.send_json(
                {
                    "op": "create_session",
                    "mission": "redalert.soviet-01.normal",
                    "mode": "streaming",
                }
            )
            session_id = ws.receive_json()["session_id"]
            ws.send_json({"op": "subscribe_frames", "session_id": session_id, "fps": 30})
            self.assertEqual(ws.receive_json()["event"], "frames_subscribed")
            frames = [ws.receive_json(), ws.receive_json()]
            self.assertTrue(all(frame["event"] == "frame" for frame in frames))
            ws.send_json({"op": "unsubscribe_frames", "session_id": session_id})
            self.assertEqual(ws.receive_json()["event"], "frames_unsubscribed")

    def test_concurrent_sessions_are_isolated(self) -> None:
        client = TestClient(_app())
        with client.websocket_connect("/ws") as a, client.websocket_connect("/ws") as b:
            a.send_json({"op": "create_session", "mission": "redalert.soviet-01.normal"})
            b.send_json({"op": "create_session", "mission": "redalert.soviet-01.normal"})
            a_id = a.receive_json()["session_id"]
            b_id = b.receive_json()["session_id"]
            a.send_json(
                {"op": "act", "session_id": a_id, "events": [{"name": "wait", "arguments": {}}]}
            )
            b.send_json(
                {"op": "act", "session_id": b_id, "events": [{"name": "wait", "arguments": {}}]}
            )
            self.assertEqual(a.receive_json()["session_id"], a_id)
            self.assertEqual(b.receive_json()["session_id"], b_id)
