from wargames.core.runtime.arena import GameDescriptor
from wargames.games.ikemen.backend import IkemenBackend
from wargames.games.ikemen.config import IkemenConfig
from wargames.games.ikemen.missions import IkemenMissionSpec
from wargames.games.ikemen.profiles import register_profiles

GAME = GameDescriptor(id="ikemen", backend_cls=IkemenBackend, config_cls=IkemenConfig)
register_profiles()

__all__ = ["GAME", "IkemenBackend", "IkemenConfig", "IkemenMissionSpec"]
