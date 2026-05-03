from wargames.core.runtime.arena import GameDescriptor
from wargames.games.quaver.backend import QuaverBackend
from wargames.games.quaver.config import QuaverConfig
from wargames.games.quaver.missions import QuaverMissionSpec
from wargames.games.quaver.profiles import register_profiles

GAME = GameDescriptor(id="quaver", backend_cls=QuaverBackend, config_cls=QuaverConfig)
register_profiles()

__all__ = ["GAME", "QuaverBackend", "QuaverConfig", "QuaverMissionSpec"]
