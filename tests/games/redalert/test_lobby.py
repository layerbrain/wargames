from unittest import IsolatedAsyncioTestCase, TestCase

from tests.games.redalert.doubles import TEST_MISSIONS, make_test_backend
from wargames.core.errors import LobbyStateError
from wargames.games.redalert.config import RedAlertConfig
from wargames.games.redalert.lobby import RedAlertLobby
from wargames.games.redalert.missions import RedAlertMissionSpec


def _mission(slots: int = 2) -> RedAlertMissionSpec:
    return RedAlertMissionSpec(
        id=f"redalert.skirmish.test-{slots}",
        title="Test",
        game="redalert",
        source="skirmish",
        map="test",
        player_slots=slots,
        min_players=2,
    )


class RedAlertLobbyTests(TestCase):
    def test_lobby_owns_slots_and_mission(self) -> None:
        lobby = RedAlertLobby(config=RedAlertConfig(), mission=_mission(2), seed=1)
        self.assertEqual(lobby.slots, 2)
        self.assertEqual(lobby.state(), "open")

    def test_lobby_accepts_openra_eight_player_cap(self) -> None:
        lobby = RedAlertLobby(config=RedAlertConfig(), mission=_mission(8), seed=1)
        self.assertEqual(lobby.slots, 8)

    def test_lobby_rejects_less_than_two(self) -> None:
        with self.assertRaises(ValueError):
            RedAlertLobby(config=RedAlertConfig(), mission=_mission(1), seed=1)

    def test_lobby_rejects_more_than_openra_cap(self) -> None:
        with self.assertRaises(ValueError):
            RedAlertLobby(config=RedAlertConfig(), mission=_mission(9), seed=1)

    def test_join_assigns_lowest_open_slot(self) -> None:
        lobby = RedAlertLobby(config=RedAlertConfig(), mission=_mission(2), seed=1)
        self.assertEqual(lobby.join("alice"), "p1")
        self.assertEqual(lobby.join("bob"), "p2")

    def test_leave_frees_slot(self) -> None:
        lobby = RedAlertLobby(config=RedAlertConfig(), mission=_mission(2), seed=1)
        self.assertEqual(lobby.join("alice"), "p1")
        lobby.leave("p1")
        self.assertEqual(lobby.join("bob"), "p1")

    def test_select_faction_rejects_unknown(self) -> None:
        lobby = RedAlertLobby(config=RedAlertConfig(), mission=_mission(2), seed=1)
        slot = lobby.join("alice")
        with self.assertRaises(ValueError):
            lobby.select_faction(slot, "orc")

    def test_can_start_requires_all_slots_ready(self) -> None:
        lobby = RedAlertLobby(config=RedAlertConfig(), mission=_mission(2), seed=1)
        p1 = lobby.join("alice")
        p2 = lobby.join("bob")
        lobby.set_ready(p1, True)
        self.assertFalse(lobby.can_start())
        lobby.set_ready(p2, True)
        self.assertTrue(lobby.can_start())


class RedAlertLobbyStartTests(IsolatedAsyncioTestCase):
    async def test_lobby_starts_eight_sessions_with_injected_backend(self) -> None:
        lobby = RedAlertLobby(
            config=RedAlertConfig(),
            mission=TEST_MISSIONS[1],
            seed=1,
            backend_factory=make_test_backend,
        )
        for index in range(1, 9):
            slot = lobby.join(f"p{index}")
            lobby.set_ready(slot, True)
        try:
            await lobby.start()
            self.assertEqual(lobby.state(), "ready")
            self.assertEqual(set(lobby.sessions), {f"p{index}" for index in range(1, 9)})
            with self.assertRaises(LobbyStateError):
                lobby.join("late")
            await lobby.begin()
            self.assertEqual(lobby.state(), "running")
        finally:
            await lobby.close()
