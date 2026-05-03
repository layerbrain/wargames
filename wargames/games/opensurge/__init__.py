from wargames.core.runtime.arena import GameDescriptor
from wargames.games.opensurge.backend import OpenSurgeBackend
from wargames.games.opensurge.config import OpenSurgeConfig
from wargames.games.opensurge.missions import OpenSurgeMissionSpec
from wargames.games.opensurge.profiles import register_profiles

GAME = GameDescriptor(id="opensurge", backend_cls=OpenSurgeBackend, config_cls=OpenSurgeConfig)
register_profiles()

__all__ = ["GAME", "OpenSurgeBackend", "OpenSurgeConfig", "OpenSurgeMissionSpec"]
