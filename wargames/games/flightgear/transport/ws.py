from __future__ import annotations

from wargames.core.transport.ws import build_ws_app
from wargames.games.flightgear import GAME
from wargames.games.flightgear.lobby import FlightGearLobby

app = build_ws_app(GAME, lobby_factory=FlightGearLobby)
