from wargames.core.runtime.arena import GameDescriptor
from wargames.games.freeciv.backend import FreeCivBackend
from wargames.games.freeciv.config import FreeCivConfig
from wargames.games.freeciv.missions import FreeCivMissionSpec
from wargames.games.freeciv.profiles import register_profiles

GAME = GameDescriptor(id="freeciv", backend_cls=FreeCivBackend, config_cls=FreeCivConfig)
register_profiles()

__all__ = ["GAME", "FreeCivBackend", "FreeCivConfig", "FreeCivMissionSpec"]
