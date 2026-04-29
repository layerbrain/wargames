from __future__ import annotations

from unittest import TestCase

from fastapi.testclient import TestClient

from tests.games.redalert.doubles import TEST_MISSIONS, make_test_backend
from wargames.core.transport.ws import build_ws_app
from wargames.games.redalert import GAME
from wargames.games.redalert.lobby import RedAlertLobby


def _lobby_factory(*, config, mission, seed):
    return RedAlertLobby(
        config=config, mission=mission, seed=seed, backend_factory=make_test_backend
    )


class LobbyIntegrationTests(TestCase):
    def test_two_client_sampled_lobby_flow(self) -> None:
        app = build_ws_app(
            GAME, backend_factory=make_test_backend, lobby_factory=_lobby_factory
        ).fastapi_app
        client = TestClient(app)
        with client.websocket_connect("/ws") as a, client.websocket_connect("/ws") as b:
            a.send_json(
                {"op": "create_lobby", "mission": TEST_MISSIONS[1].id, "seed": 0, "slots": 2}
            )
            created = a.receive_json()
            self.assertEqual(created["event"], "lobby_created")
            lobby_id = created["lobby_id"]

            b.send_json({"op": "subscribe_lobby", "lobby_id": lobby_id})
            self.assertEqual(b.receive_json()["event"], "lobby_state")

            a.send_json(
                {"op": "join_lobby", "lobby_id": lobby_id, "name": "alice", "faction": "soviet"}
            )
            self.assertEqual(a.receive_json()["event"], "lobby_joined")
            self.assertEqual(a.receive_json()["event"], "lobby_state")
            self.assertEqual(b.receive_json()["event"], "lobby_state")

            b.send_json(
                {"op": "join_lobby", "lobby_id": lobby_id, "name": "bob", "faction": "allies"}
            )
            self.assertEqual(b.receive_json()["event"], "lobby_joined")
            self.assertEqual(a.receive_json()["event"], "lobby_state")
            self.assertEqual(b.receive_json()["event"], "lobby_state")

            for ws, slot in ((a, "p1"), (b, "p2")):
                ws.send_json({"op": "set_ready", "lobby_id": lobby_id, "slot": slot, "ready": True})
                a.receive_json()
                b.receive_json()

            a.send_json({"op": "start_lobby", "lobby_id": lobby_id, "mode": "sampled"})
            state = a.receive_json()
            ready = a.receive_json()
            self.assertEqual(state["event"], "lobby_state")
            self.assertEqual(ready["event"], "lobby_ready")
            sessions = ready["sessions"]
            self.assertEqual(set(sessions), {"p1", "p2"})

            a.send_json({"op": "begin_lobby", "lobby_id": lobby_id})
            self.assertEqual(a.receive_json()["event"], "lobby_started")

            a.send_json(
                {
                    "op": "act",
                    "session_id": sessions["p1"],
                    "events": [{"name": "wait", "arguments": {}}],
                }
            )
            result = a.receive_json()
            self.assertEqual(result["event"], "action_result")
            self.assertIsNotNone(result["frame"]["image_b64"])

            a.send_json({"op": "close_lobby", "lobby_id": lobby_id})
            self.assertEqual(a.receive_json()["event"], "lobby_closed")
