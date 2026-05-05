from wargames.core.transport.ws import build_ws_app
from wargames.games.naev import GAME

app = build_ws_app(GAME)

__all__ = ["app"]
