from wargames.core.runtime.arena import GameDescriptor
from wargames.games.naev.backend import NaevBackend
from wargames.games.naev.config import NaevConfig
from wargames.games.naev.missions import NaevMissionSpec
from wargames.games.naev.profiles import register_profiles

GAME = GameDescriptor(id="naev", backend_cls=NaevBackend, config_cls=NaevConfig)
register_profiles()

__all__ = ["GAME", "NaevBackend", "NaevConfig", "NaevMissionSpec"]
