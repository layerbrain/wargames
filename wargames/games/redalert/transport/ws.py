from __future__ import annotations

from wargames.core.transport.ws import build_ws_app
from wargames.games.redalert import GAME
from wargames.games.redalert.lobby import RedAlertLobby

app = build_ws_app(GAME, lobby_factory=RedAlertLobby)
